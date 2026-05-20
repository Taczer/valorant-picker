from __future__ import annotations

from collections import Counter

from .analyzer import analyze_team, calculate_team_score
from .data.agents import AGENTS
from .models import CandidateScore, MapInfo, Recommendation, Role, SelectionState, TeamSlot, UserProfile
from .strategy import DEFAULT_ROLE_WEIGHTS, MAP_AGENT_NOTES, MAP_AGENT_TIPS, MAP_TUNING, PAIR_SYNERGIES, SELFISH_DUELISTS


ROLE_PRIORITY = (Role.CONTROLLER, Role.INITIATOR, Role.SENTINEL, Role.DUELIST)


def recommend(
    team: tuple[TeamSlot, ...],
    map_info: MapInfo,
    profile: UserProfile | None = None,
) -> Recommendation:
    profile = profile or UserProfile()
    analysis = analyze_team(team, map_info)
    candidates = tuple(
        sorted(
            (_score_agent(agent_name, team, map_info, profile, analysis) for agent_name in AGENTS),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
    )
    best = candidates[0]
    alternatives = candidates[1:5]
    best_role = _best_role_to_fill(analysis.missing_roles)
    warning = None
    if analysis.score <= 4.0:
        warning = "Team jest mocno niezbalansowany. Najpierw uzupełnij brakującą kluczową rolę."
    elif best.agent.role == Role.DUELIST and analysis.role_counts[Role.DUELIST] >= 2:
        warning = "Rekomendacja duelista ma sens tylko przy Twoim profilu; kompozycyjnie lepsza jest rola utility."

    return Recommendation(
        map_info=map_info,
        team=team,
        analysis=analysis,
        best=best,
        alternatives=alternatives,
        best_role_to_fill=best_role,
        advice=advice_for_agent(best.agent.name, map_info),
        warning=warning,
    )


def _score_agent(
    agent_name: str,
    team: tuple[TeamSlot, ...],
    map_info: MapInfo,
    profile: UserProfile,
    analysis,
) -> CandidateScore:
    agent = AGENTS[agent_name]
    reasons: list[str] = []
    warnings: list[str] = []
    score = 50.0
    picked_names = {
        slot.agent_name
        for slot in team
        if slot.agent_name and slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
    }
    selected_names = {
        slot.agent_name for slot in team if slot.agent_name and slot.state == SelectionState.SELECTED
    }
    locked_names = {
        slot.agent_name for slot in team if slot.agent_name and slot.state == SelectionState.LOCKED
    }

    if agent.name in locked_names:
        score -= 500
        warnings.append("Agent jest już zalockowany przez innego gracza.")
    elif agent.name in selected_names:
        score -= 350
        warnings.append("Agent jest już zaznaczony przez innego gracza.")
    elif agent.name in picked_names:
        score -= 250
        warnings.append("Agent jest już zajęty.")

    if agent.role in analysis.missing_roles:
        role_weight = _role_weight(map_info, agent.role)
        bonus = 38 * role_weight
        if agent.role == Role.CONTROLLER and analysis.role_counts[Role.CONTROLLER] == 0:
            bonus = 78 * role_weight
            reasons.append("Team nie ma żadnego controllera, więc smoke'i są najwyższym priorytetem.")
        elif agent.role == Role.INITIATOR and analysis.role_counts[Role.INITIATOR] == 0:
            bonus = 52 * role_weight
            reasons.append("Team nie ma inicjatora, więc brakuje info, flasha albo cleara pod execute.")
        elif agent.role == Role.DUELIST and analysis.role_counts[Role.DUELIST] == 0:
            has_core_utility = (
                analysis.role_counts[Role.CONTROLLER] >= 1
                and analysis.role_counts[Role.INITIATOR] >= 1
                and analysis.role_counts[Role.SENTINEL] >= 1
            )
            bonus = (52 if has_core_utility else 30) * role_weight
            reasons.append("Team nie ma entry duelista, więc brakuje agenta do otwierania site'u.")
        else:
            reasons.append(f"Uzupełnia brakującą rolę: {agent.role.value}.")
        score += bonus

    role_count = analysis.role_counts[agent.role]
    if role_count >= 2 and agent.role != Role.CONTROLLER:
        penalty = 15 * (role_count - 1)
        score -= penalty
        warnings.append(f"Team ma już {role_count} agentów w roli {agent.role.value}.")
    if agent.role == Role.DUELIST and analysis.role_counts[Role.DUELIST] >= 2:
        score -= 95
        warnings.append("To byłby trzeci duelist albo kolejny pick bez utility.")
    if agent.role == Role.CONTROLLER and role_count >= 1:
        if _map_has_feature(map_info, "wall_map") and "wall" in agent.utility:
            score += 24
            reasons.append("Mapa lubi drugiego controllera ze ścianą, bo łatwiej odciąć długie linie.")
        else:
            score -= 12
            warnings.append("Team ma już controllera; drugi smoke musi dawać konkretną wartość mapową.")
    if agent.role == Role.SENTINEL and role_count >= 1 and (
        Role.CONTROLLER in analysis.missing_roles or Role.INITIATOR in analysis.missing_roles
    ):
        score -= 25
        warnings.append("Drugi sentinel jest ryzykowny, gdy nadal brakuje smoke'ów albo inicjatora.")

    critical_gap_score = _score_critical_gaps(agent, analysis, warnings)
    score += critical_gap_score

    recommended_names = set(map_info.recommended_for_role(agent.role))
    if agent.name in recommended_names:
        rank_bonus = _map_recommendation_rank_bonus(agent.name, map_info)
        score += rank_bonus
        reasons.append(f"{agent.name} jest rekomendowany na mapę {map_info.name} dla roli {agent.role.value}.")
    map_note = MAP_AGENT_NOTES.get(map_info.name, {}).get(agent.name)
    if map_note:
        score += 7
        reasons.append(map_note)
    if map_info.name in agent.strong_maps:
        score += 20
        reasons.append(f"{agent.name} jest mocny na mapie {map_info.name}.")
    if map_info.name in agent.weak_maps:
        score -= 22
        warnings.append(f"{agent.name} jest słabszym wyborem na mapie {map_info.name}.")

    matched_needs = [need for need in map_info.needs if need in agent.utility and need in analysis.missing_utility]
    if matched_needs:
        score += 8 * len(matched_needs)
        reasons.append("Uzupełnia brakujące utility: " + ", ".join(matched_needs) + ".")
    score += _score_utility_targets(agent, map_info, analysis.utility_counts, reasons)
    score += _score_map_features(agent, map_info, reasons, warnings)
    score += _score_team_synergy(agent, team, map_info, analysis, reasons, warnings)

    if agent.solo_queue:
        score += 5
        reasons.append("Dobrze działa w solo queue.")

    style_matches = sorted(profile.preferred_styles & agent.playstyles)
    if style_matches:
        score += 7 + 3 * len(style_matches)
        reasons.append("Pasuje do Twojego stylu gry: " + ", ".join(style_matches) + ".")
    if profile.beginner_mode:
        if agent.difficulty <= 2 or "beginner" in agent.playstyles:
            score += 16
            reasons.append("Jest dobry dla trybu początkującego.")
        elif agent.difficulty >= 4:
            score -= 18
            warnings.append("Agent jest trudniejszy, a masz włączony tryb początkujący.")
    team_after = _team_score_after(agent, team, map_info)
    score += (team_after - analysis.score) * 5
    if team_after > analysis.score:
        reasons.append(f"Podnosi ocenę teamu z {analysis.score}/10 do {team_after}/10.")
    elif team_after <= analysis.score and agent.name not in picked_names:
        score -= 8
        warnings.append("Nie poprawia ogólnego balansu teamu według modelu ról i utility.")

    if not reasons:
        reasons.append(agent.description)

    return CandidateScore(agent, round(score, 1), _prioritize_reasons(reasons), tuple(dict.fromkeys(warnings)), team_after)


def _score_critical_gaps(agent, analysis, warnings: list[str]) -> float:
    score = 0.0

    if analysis.role_counts[Role.CONTROLLER] == 0 and agent.role != Role.CONTROLLER:
        score -= 42
        warnings.append("Brak smoke'ów jest ważniejszy niż komfortowy pick albo profil gracza.")

    has_controller = analysis.role_counts[Role.CONTROLLER] >= 1
    if has_controller and analysis.role_counts[Role.INITIATOR] == 0 and agent.role != Role.INITIATOR:
        score -= 24
        warnings.append("Bez inicjatora execute będzie słabszy nawet przy dobrych smoke'ach.")

    has_initiator = analysis.role_counts[Role.INITIATOR] >= 1
    if has_controller and has_initiator and analysis.utility_counts.get("flank_watch", 0) == 0:
        if agent.role != Role.SENTINEL and "flank_watch" not in agent.utility:
            score -= 12
            warnings.append("Team nadal nie ma stabilnego flank watcha.")

    has_sentinel = analysis.role_counts[Role.SENTINEL] >= 1
    if has_controller and has_initiator and has_sentinel and analysis.role_counts[Role.DUELIST] == 0:
        if agent.role != Role.DUELIST:
            score -= 14
            warnings.append("Po zabezpieczeniu utility team nadal potrzebuje entry.")

    return score


def _prioritize_reasons(reasons: list[str]) -> tuple[str, ...]:
    unique_reasons = tuple(dict.fromkeys(reasons))
    profile_prefixes = (
        "Dobrze działa w solo queue.",
        "Pasuje do Twojego stylu gry:",
        "Jest dobry dla trybu początkującego.",
    )

    def priority(reason: str) -> int:
        if reason.startswith(profile_prefixes):
            return 2
        if (
            "map" in reason.lower()
            or reason.startswith("Mapa ")
            or reason.startswith("Pasuje do cech mapy:")
        ):
            return 1
        return 0

    return tuple(sorted(unique_reasons, key=priority))


def _team_score_after(agent, team: tuple[TeamSlot, ...], map_info: MapInfo) -> float:
    picked_agents = [
        AGENTS[slot.agent_name]
        for slot in team
        if slot.agent_name in AGENTS and slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
    ]
    picked_agents.append(agent)
    role_counts = Counter(picked.role for picked in picked_agents)
    utility_counts = Counter()
    for picked in picked_agents:
        utility_counts.update(picked.utility)
    return calculate_team_score(role_counts, utility_counts, map_info)


def _score_utility_targets(agent, map_info: MapInfo, utility_counts: dict[str, int], reasons: list[str]) -> float:
    tuning = MAP_TUNING.get(map_info.name)
    if not tuning:
        return 0.0
    score = 0.0
    filled: list[str] = []
    for utility, target in tuning.utility_targets.items():
        current = utility_counts.get(utility, 0)
        if current < target and utility in agent.utility:
            if utility == "smokes":
                weight = 16.0
            elif utility == "wall":
                weight = 15.0
            elif utility in {"flank_watch", "info"}:
                weight = 12.0
            else:
                weight = 9.0
            if current == 0:
                score += weight
            else:
                score += weight * 0.65
            filled.append(utility)
    if filled:
        reasons.append("Domyka progi utility dla tej mapy: " + ", ".join(filled) + ".")
    return score


def _score_map_features(agent, map_info: MapInfo, reasons: list[str], warnings: list[str]) -> float:
    tuning = MAP_TUNING.get(map_info.name)
    if not tuning:
        return 0.0
    features = tuning.features
    score = 0.0

    feature_hits: list[str] = []
    if "wall_map" in features and "wall" in agent.utility:
        score += 18
        feature_hits.append("ściana na długie linie")
    if "plant_wall" in features and {"wall", "plant"} & agent.utility:
        score += 10
        feature_hits.append("bezpieczny plant")
    if {"long_range", "wide_sites", "recon_lanes"} & features and {"info", "recon"} & agent.utility:
        score += 10
        feature_hits.append("informacja na otwarte przestrzenie")
    if {"tight_chokes", "standard_chokes"} & features and {"flash", "stun", "clear", "suppress"} & agent.utility:
        score += 10
        feature_hits.append("czyszczenie ciasnych wejść")
        if agent.role == Role.DUELIST and "clear" in agent.utility:
            score += 6
    if {"three_sites", "flank_pressure", "pinch_attacks"} & features and {"flank_watch", "stall", "info"} & agent.utility:
        score += 9
        feature_hits.append("kontrola flank i rotacji")
    if {"fast_exec", "pinch_attacks"} & features and {"mobility", "entry", "flash", "stun"} & agent.utility:
        score += 7
        feature_hits.append("tempo execute'u")
    if "mid_control" in features and {"smokes", "info", "flash", "stall"} & agent.utility:
        score += 5
        feature_hits.append("walka o mida")
    if "postplant" in features and "postplant" in agent.utility:
        score += 5
        feature_hits.append("post-plant")
    if "operator" in features and {"operator", "mobility"} & agent.utility:
        score += 5
        feature_hits.append("presja Operatora")

    if "wall_map" in features and agent.role == Role.CONTROLLER and "wall" not in agent.utility:
        score -= 14
        warnings.append("To mapa ze szczególnie dużą wartością wall controllera.")
    if "tight_chokes" in features and agent.role == Role.DUELIST and "clear" not in agent.utility and "mobility" not in agent.utility:
        score -= 10
        warnings.append("Na tej mapie duelist bez mocnego cleara lub mobilności ma trudniejsze wejścia.")

    if feature_hits:
        reasons.append("Pasuje do cech mapy: " + ", ".join(dict.fromkeys(feature_hits)) + ".")
    return score


def _score_team_synergy(
    agent,
    team: tuple[TeamSlot, ...],
    map_info: MapInfo,
    analysis,
    reasons: list[str],
    warnings: list[str],
) -> float:
    allies = [
        AGENTS[slot.agent_name]
        for slot in team
        if slot.agent_name in AGENTS and slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
    ]
    score = 0.0
    synergy_reasons: list[str] = []

    for ally in allies:
        pair = frozenset({agent.name, ally.name})
        pair_bonus = PAIR_SYNERGIES.get(pair)
        if pair_bonus and (not pair_bonus[2] or map_info.name in pair_bonus[2]):
            score += pair_bonus[0]
            synergy_reasons.append(pair_bonus[1])

    if agent.role == Role.DUELIST:
        support_count = sum(
            bool({"flash", "info", "clear", "stun", "suppress"} & ally.utility)
            for ally in allies
            if ally.role == Role.INITIATOR
        )
        if support_count:
            score += min(14, 6 * support_count)
            synergy_reasons.append("Ma inicjatora, który może przygotować entry zamiast wymuszać suche wejście.")
        if analysis.role_counts[Role.INITIATOR] == 0:
            score -= 22
            warnings.append("Duelist bez inicjatora będzie często musiał wchodzić bez przygotowania.")
        if agent.name in SELFISH_DUELISTS and analysis.role_counts[Role.DUELIST] >= 1:
            score -= 24
            warnings.append("Kolejny samowystarczalny duelist wnosi mało utility dla drużyny.")

    if agent.role == Role.INITIATOR and analysis.role_counts[Role.DUELIST] >= 1:
        if {"flash", "clear", "info", "stun"} & agent.utility:
            score += 10
            synergy_reasons.append("Wzmacnia obecnego duelista przez info, flash albo clear pod pierwszy kontakt.")

    if agent.role == Role.CONTROLLER:
        if analysis.role_counts[Role.SENTINEL] >= 1:
            score += 5
            synergy_reasons.append("Smoke'i z sentinelem pozwalają kontrolować wejścia i flankę.")
        if analysis.role_counts[Role.INITIATOR] >= 1 and "flash" in agent.utility:
            score += 4
            synergy_reasons.append("Dodatkowy flash controllera ułatwia wejście po utility inicjatora.")

    if agent.role == Role.SENTINEL:
        if analysis.role_counts[Role.CONTROLLER] >= 1:
            score += 6
            synergy_reasons.append("Sentinel za smoke'ami stabilizuje flankę, retake i kontrolę mapy.")
        if analysis.role_counts[Role.CONTROLLER] == 0:
            score -= 10
            warnings.append("Sentinel nie zastąpi smoke'ów, jeśli team nadal nie ma controllera.")

    if "postplant" in agent.utility and analysis.utility_counts.get("postplant", 0) >= 1:
        score += 4
        synergy_reasons.append("Dokłada drugi warunek wygrania rundy po plancie.")

    if synergy_reasons:
        reasons.extend(dict.fromkeys(synergy_reasons))
    return score


def _role_weight(map_info: MapInfo, role: Role) -> float:
    tuning = MAP_TUNING.get(map_info.name)
    if tuning:
        return tuning.role_weights.get(role, DEFAULT_ROLE_WEIGHTS[role])
    return DEFAULT_ROLE_WEIGHTS[role]


def _map_has_feature(map_info: MapInfo, feature: str) -> bool:
    tuning = MAP_TUNING.get(map_info.name)
    return bool(tuning and feature in tuning.features)


def _map_recommendation_rank_bonus(agent_name: str, map_info: MapInfo) -> float:
    recommended = map_info.recommended_for_role(AGENTS[agent_name].role)
    if agent_name not in recommended:
        return 0.0
    rank = recommended.index(agent_name)
    if rank == 0:
        return 24.0
    if rank == 1:
        return 18.0
    if rank == 2:
        return 13.0
    return 8.0


def _best_role_to_fill(missing_roles: tuple[Role, ...]) -> Role | None:
    for role in ROLE_PRIORITY:
        if role in missing_roles:
            return role
    return None


def advice_for_agent(agent_name: str, map_info: MapInfo) -> str:
    agent = AGENTS[agent_name]
    map_note = MAP_AGENT_NOTES.get(map_info.name, {}).get(agent.name)
    tips = MAP_AGENT_TIPS.get(map_info.name, {}).get(agent.name, ())
    prefix_parts = []
    if map_note:
        prefix_parts.append(map_note)
    if tips:
        prefix_parts.append("Pro tipy: " + " | ".join(tips))
    prefix = " ".join(prefix_parts)
    if prefix:
        prefix += " "
    if agent.role == Role.CONTROLLER:
        if map_info.name == "Ascent":
            return prefix + "Graj blisko teamu, dawaj smoke'i na Heaven, Tree, Market i pod wejścia. Używaj flasha/utility razem z entry, zamiast lurkować za daleko."
        return prefix + "Priorytetem są smoke'i pod wejście i retake. Nie oddawaj życia przed użyciem kluczowego utility."
    if agent.role == Role.INITIATOR:
        return prefix + "Ustawiaj utility pod wejście duelista. Najpierw info albo flash, potem trade; nie zużywaj wszystkiego bez kontaktu teamu."
    if agent.role == Role.SENTINEL:
        return prefix + "Zabezpiecz flankę i graj pod informację. W ataku trzymaj lurka przeciwnika, w obronie opóźniaj wejścia zamiast brać samotne pojedynki."
    return prefix + "Wejdź pierwszy dopiero po smoke'u i utility inicjatora. Twoim zadaniem jest przestrzeń, a nie samotny lurk bez trade'u."
