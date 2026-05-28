from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from .analyzer import analyze_team, calculate_team_score
from .data.agents import AGENTS
from .data.map_tuning import DEFAULT_ROLE_WEIGHTS, MAP_TUNING
from .data.synergies import MAP_AGENT_NOTES, MAP_AGENT_TIPS, MAP_ROLE_ADVICE, PAIR_SYNERGIES
from .i18n import localized_text, localized_texts, t
from .models import Agent, CandidateScore, MapInfo, Recommendation, Role, SelectionState, TeamAnalysis, TeamSlot, UserProfile


ROLE_PRIORITY = (Role.CONTROLLER, Role.INITIATOR, Role.SENTINEL, Role.DUELIST)


class ReasonKind(StrEnum):
    COMPOSITION = "composition"
    UTILITY = "utility"
    SYNERGY = "synergy"
    MAP = "map"
    SCORE = "score"
    PROFILE = "profile"


@dataclass(frozen=True)
class Reason:
    kind: ReasonKind
    text: str


@dataclass(frozen=True)
class ScoringContext:
    team: tuple[TeamSlot, ...]
    map_info: MapInfo
    profile: UserProfile
    analysis: TeamAnalysis
    language: str
    picked_names: frozenset[str]
    selected_names: frozenset[str]
    locked_names: frozenset[str]
    base_role_counts: Counter[Role]
    base_utility_counts: Counter[str]

    @classmethod
    def build(
        cls,
        team: tuple[TeamSlot, ...],
        map_info: MapInfo,
        profile: UserProfile,
        analysis: TeamAnalysis,
        language: str,
    ) -> ScoringContext:
        picked_agents = _picked_agents(team)
        base_role_counts = Counter(picked.role for picked in picked_agents)
        base_utility_counts: Counter[str] = Counter()
        for picked in picked_agents:
            base_utility_counts.update(picked.utility)
        picked_names, selected_names, locked_names = _picked_name_sets(team)
        return cls(
            team=team,
            map_info=map_info,
            profile=profile,
            analysis=analysis,
            language=language,
            picked_names=picked_names,
            selected_names=selected_names,
            locked_names=locked_names,
            base_role_counts=base_role_counts,
            base_utility_counts=base_utility_counts,
        )

    def t(self, key: str, **params) -> str:
        return t(self.language, key, **params)

# Heuristic scoring weights tuned through regression tests and sample Valorant
# composition scenarios. They are relative ranking weights, not probabilities.
BASE_AGENT_SCORE = 50.0
LOCKED_AGENT_PENALTY = 500
SELECTED_AGENT_PENALTY = 350
TAKEN_AGENT_PENALTY = 250
MISSING_ROLE_BONUS = 38
NO_CONTROLLER_BONUS = 78
NO_INITIATOR_BONUS = 52
NO_DUELIST_CORE_BONUS = 52
NO_DUELIST_INCOMPLETE_CORE_BONUS = 30
ROLE_STACK_PENALTY = 15
THIRD_DUELIST_PENALTY = 95
SECOND_WALL_CONTROLLER_BONUS = 24
SECOND_CONTROLLER_PENALTY = 12
SECOND_SENTINEL_WITH_CORE_GAP_PENALTY = 25
NO_CONTROLLER_CRITICAL_GAP_PENALTY = 42
NO_INITIATOR_CRITICAL_GAP_PENALTY = 24
NO_FLANK_WATCH_CRITICAL_GAP_PENALTY = 12
NO_ENTRY_CRITICAL_GAP_PENALTY = 14
MAP_RECOMMENDATION_TOP_BONUS = 24
MAP_RECOMMENDATION_SECOND_BONUS = 18
MAP_RECOMMENDATION_THIRD_BONUS = 13
MAP_RECOMMENDATION_OTHER_BONUS = 8
MAP_NOTE_BONUS = 7
STRONG_MAP_BONUS = 20
WEAK_MAP_PENALTY = 22
MISSING_UTILITY_BONUS = 8
UTILITY_WEIGHT_SMOKES = 16.0
UTILITY_WEIGHT_WALL = 15.0
UTILITY_WEIGHT_INFO_OR_FLANK = 12.0
UTILITY_WEIGHT_DEFAULT = 9.0
UTILITY_PARTIAL_TARGET_MULTIPLIER = 0.65
FEATURE_WALL_BONUS = 18
FEATURE_PLANT_BONUS = 10
FEATURE_INFO_BONUS = 10
FEATURE_CLEAR_BONUS = 10
FEATURE_DUELIST_CLEAR_BONUS = 6
FEATURE_FLANK_BONUS = 9
FEATURE_EXECUTE_BONUS = 7
FEATURE_MID_BONUS = 5
FEATURE_POSTPLANT_BONUS = 5
FEATURE_OPERATOR_BONUS = 5
NON_WALL_CONTROLLER_ON_WALL_MAP_PENALTY = 14
DUELIST_TIGHT_CHOKE_PENALTY = 10
TEAM_SCORE_DELTA_MULTIPLIER = 5
NO_BALANCE_IMPROVEMENT_PENALTY = 8
SOLO_QUEUE_BONUS = 5
STYLE_MATCH_BASE_BONUS = 7
STYLE_MATCH_PER_STYLE_BONUS = 3
BEGINNER_FRIENDLY_BONUS = 16
BEGINNER_DIFFICULT_AGENT_PENALTY = 18
DUELIST_SUPPORT_BONUS_PER_INITIATOR = 6
DUELIST_SUPPORT_BONUS_CAP = 14
DUELIST_WITHOUT_INITIATOR_PENALTY = 22
SELFISH_DUELIST_STACK_PENALTY = 24
INITIATOR_WITH_DUELIST_BONUS = 10
CONTROLLER_WITH_SENTINEL_BONUS = 5
CONTROLLER_FLASH_WITH_INITIATOR_BONUS = 4
SENTINEL_WITH_CONTROLLER_BONUS = 6
SENTINEL_WITHOUT_CONTROLLER_PENALTY = 10
POSTPLANT_STACK_BONUS = 4


def recommend(
    team: tuple[TeamSlot, ...],
    map_info: MapInfo,
    profile: UserProfile | None = None,
    language: str = "en",
) -> Recommendation:
    profile = profile or UserProfile()
    analysis = analyze_team(team, map_info)
    ctx = ScoringContext.build(team, map_info, profile, analysis, language)
    candidates = tuple(
        sorted(
            (
                _score_agent(agent_name, ctx)
                for agent_name in AGENTS
            ),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
    )
    best = candidates[0]
    alternatives = candidates[1:5]
    best_role = _best_role_to_fill(analysis.missing_roles)
    warning = None
    if analysis.score <= 4.0:
        warning = ctx.t("rec_unbalanced_warning")
    elif best.agent.role == Role.DUELIST and analysis.role_counts[Role.DUELIST] >= 2:
        warning = ctx.t("rec_duelist_warning")

    return Recommendation(
        map_info=map_info,
        team=team,
        analysis=analysis,
        best=best,
        alternatives=alternatives,
        best_role_to_fill=best_role,
        advice=advice_for_agent(best.agent.name, map_info, language),
        warning=warning,
    )


def _score_agent(
    agent_name: str,
    ctx: ScoringContext,
) -> CandidateScore:
    agent = AGENTS[agent_name]
    reasons: list[Reason] = []
    warnings: list[str] = []

    score = BASE_AGENT_SCORE
    score += _score_availability(agent, ctx, warnings)
    score += _score_missing_roles(agent, ctx, reasons)
    score += _score_role_stacking(agent, ctx, reasons, warnings)
    score += _score_critical_gaps(agent, ctx, warnings)
    score += _score_map_recommendations(agent, ctx, reasons)
    score += _score_map_notes(agent, ctx, reasons)
    score += _score_strong_weak_maps(agent, ctx, reasons, warnings)
    score += _score_missing_utility(agent, ctx, reasons)
    score += _score_utility_targets(agent, ctx, reasons)
    score += _score_map_features(agent, ctx, reasons, warnings)
    score += _score_team_synergy(agent, ctx, reasons, warnings)
    score += _score_profile_fit(agent, ctx, reasons, warnings)

    team_after = _team_score_after(agent, ctx)
    score += _score_team_delta(agent, team_after, ctx, reasons, warnings)

    if not reasons:
        reasons.append(Reason(ReasonKind.MAP, _default_agent_reason(agent, ctx)))

    return CandidateScore(agent, round(score, 1), _prioritize_reasons(reasons), tuple(dict.fromkeys(warnings)), team_after)


def _score_availability(
    agent: Agent,
    ctx: ScoringContext,
    warnings: list[str],
) -> float:
    if agent.name in ctx.locked_names:
        warnings.append(ctx.t("rec_locked_agent"))
        return -LOCKED_AGENT_PENALTY
    if agent.name in ctx.selected_names:
        warnings.append(ctx.t("rec_selected_agent"))
        return -SELECTED_AGENT_PENALTY
    if agent.name in ctx.picked_names:
        warnings.append(ctx.t("rec_taken_agent"))
        return -TAKEN_AGENT_PENALTY
    return 0.0


def _score_missing_roles(agent: Agent, ctx: ScoringContext, reasons: list[Reason]) -> float:
    analysis = ctx.analysis
    if agent.role not in analysis.missing_roles:
        return 0.0

    role_weight = _role_weight(ctx.map_info, agent.role)
    bonus = MISSING_ROLE_BONUS * role_weight
    if agent.role == Role.CONTROLLER and analysis.role_counts[Role.CONTROLLER] == 0:
        bonus = NO_CONTROLLER_BONUS * role_weight
        reasons.append(Reason(ReasonKind.COMPOSITION, ctx.t("rec_no_controller")))
    elif agent.role == Role.INITIATOR and analysis.role_counts[Role.INITIATOR] == 0:
        bonus = NO_INITIATOR_BONUS * role_weight
        reasons.append(Reason(ReasonKind.COMPOSITION, ctx.t("rec_no_initiator")))
    elif agent.role == Role.DUELIST and analysis.role_counts[Role.DUELIST] == 0:
        has_core_utility = (
            analysis.role_counts[Role.CONTROLLER] >= 1
            and analysis.role_counts[Role.INITIATOR] >= 1
            and analysis.role_counts[Role.SENTINEL] >= 1
        )
        base_bonus = NO_DUELIST_CORE_BONUS if has_core_utility else NO_DUELIST_INCOMPLETE_CORE_BONUS
        bonus = base_bonus * role_weight
        reasons.append(Reason(ReasonKind.COMPOSITION, ctx.t("rec_no_duelist")))
    else:
        reasons.append(Reason(ReasonKind.COMPOSITION, ctx.t("rec_missing_role", role=agent.role.value)))
    return bonus


def _score_role_stacking(agent: Agent, ctx: ScoringContext, reasons: list[Reason], warnings: list[str]) -> float:
    analysis = ctx.analysis
    role_count = analysis.role_counts[agent.role]
    score = 0.0
    if role_count >= 2 and agent.role != Role.CONTROLLER:
        score -= ROLE_STACK_PENALTY * (role_count - 1)
        warnings.append(ctx.t("rec_role_stack", count=role_count, role=agent.role.value))
    if agent.role == Role.DUELIST and analysis.role_counts[Role.DUELIST] >= 2:
        score -= THIRD_DUELIST_PENALTY
        warnings.append(ctx.t("rec_third_duelist"))
    if agent.role == Role.CONTROLLER and role_count >= 1:
        if _map_has_feature(ctx.map_info, "wall_map") and "wall" in agent.utility:
            score += SECOND_WALL_CONTROLLER_BONUS
            reasons.append(Reason(ReasonKind.MAP, ctx.t("rec_second_wall_controller")))
        else:
            score -= SECOND_CONTROLLER_PENALTY
            warnings.append(ctx.t("rec_second_controller_warning"))
    if agent.role == Role.SENTINEL and role_count >= 1 and (
        Role.CONTROLLER in analysis.missing_roles or Role.INITIATOR in analysis.missing_roles
    ):
        score -= SECOND_SENTINEL_WITH_CORE_GAP_PENALTY
        warnings.append(ctx.t("rec_second_sentinel_warning"))
    return score


def _score_critical_gaps(agent: Agent, ctx: ScoringContext, warnings: list[str]) -> float:
    analysis = ctx.analysis
    score = 0.0

    if analysis.role_counts[Role.CONTROLLER] == 0 and agent.role != Role.CONTROLLER:
        score -= NO_CONTROLLER_CRITICAL_GAP_PENALTY
        warnings.append(ctx.t("rec_no_smokes_over_profile"))

    has_controller = analysis.role_counts[Role.CONTROLLER] >= 1
    if has_controller and analysis.role_counts[Role.INITIATOR] == 0 and agent.role != Role.INITIATOR:
        score -= NO_INITIATOR_CRITICAL_GAP_PENALTY
        warnings.append(ctx.t("rec_no_initiator_warning"))

    has_initiator = analysis.role_counts[Role.INITIATOR] >= 1
    if has_controller and has_initiator and analysis.utility_counts.get("flank_watch", 0) == 0:
        if agent.role != Role.SENTINEL and "flank_watch" not in agent.utility:
            score -= NO_FLANK_WATCH_CRITICAL_GAP_PENALTY
            warnings.append(ctx.t("rec_no_flank_watch_warning"))

    has_sentinel = analysis.role_counts[Role.SENTINEL] >= 1
    if has_controller and has_initiator and has_sentinel and analysis.role_counts[Role.DUELIST] == 0:
        if agent.role != Role.DUELIST:
            score -= NO_ENTRY_CRITICAL_GAP_PENALTY
            warnings.append(ctx.t("rec_no_entry_warning"))

    return score


def _score_map_recommendations(agent: Agent, ctx: ScoringContext, reasons: list[Reason]) -> float:
    recommended_names = set(ctx.map_info.recommended_for_role(agent.role))
    if agent.name not in recommended_names:
        return 0.0

    reasons.append(
        Reason(
            ReasonKind.MAP,
            ctx.t("rec_map_recommended", agent=agent.name, map=ctx.map_info.name, role=agent.role.value),
        )
    )
    return _map_recommendation_rank_bonus(agent.name, ctx.map_info)


def _score_map_notes(agent: Agent, ctx: ScoringContext, reasons: list[Reason]) -> float:
    map_note = MAP_AGENT_NOTES.get(ctx.map_info.name, {}).get(agent.name)
    if not map_note:
        return 0.0
    note = localized_text(map_note, ctx.language)
    if note:
        reasons.append(Reason(ReasonKind.MAP, note))
    return MAP_NOTE_BONUS


def _score_strong_weak_maps(agent: Agent, ctx: ScoringContext, reasons: list[Reason], warnings: list[str]) -> float:
    score = 0.0
    if ctx.map_info.name in agent.strong_maps:
        score += STRONG_MAP_BONUS
        reasons.append(Reason(ReasonKind.MAP, ctx.t("rec_strong_map", agent=agent.name, map=ctx.map_info.name)))
    if ctx.map_info.name in agent.weak_maps:
        score -= WEAK_MAP_PENALTY
        warnings.append(ctx.t("rec_weak_map", agent=agent.name, map=ctx.map_info.name))
    return score


def _score_missing_utility(agent: Agent, ctx: ScoringContext, reasons: list[Reason]) -> float:
    matched_needs = [
        need for need in ctx.map_info.needs if need in agent.utility and need in ctx.analysis.missing_utility
    ]
    if not matched_needs:
        return 0.0
    reasons.append(Reason(ReasonKind.UTILITY, ctx.t("rec_missing_utility", utility=", ".join(matched_needs))))
    return MISSING_UTILITY_BONUS * len(matched_needs)


def _score_profile_fit(agent: Agent, ctx: ScoringContext, reasons: list[Reason], warnings: list[str]) -> float:
    score = 0.0
    if agent.solo_queue:
        score += SOLO_QUEUE_BONUS
        reasons.append(Reason(ReasonKind.PROFILE, ctx.t("rec_solo_queue")))

    style_matches = sorted(ctx.profile.preferred_styles & agent.playstyles)
    if style_matches:
        score += STYLE_MATCH_BASE_BONUS + STYLE_MATCH_PER_STYLE_BONUS * len(style_matches)
        reasons.append(Reason(ReasonKind.PROFILE, ctx.t("rec_style_match", styles=", ".join(style_matches))))
    if ctx.profile.beginner_mode:
        if agent.difficulty <= 2 or "beginner" in agent.playstyles:
            score += BEGINNER_FRIENDLY_BONUS
            reasons.append(Reason(ReasonKind.PROFILE, ctx.t("rec_beginner_good")))
        elif agent.difficulty >= 4:
            score -= BEGINNER_DIFFICULT_AGENT_PENALTY
            warnings.append(ctx.t("rec_beginner_hard"))
    return score


def _score_team_delta(
    agent: Agent,
    team_after: float,
    ctx: ScoringContext,
    reasons: list[Reason],
    warnings: list[str],
) -> float:
    score = (team_after - ctx.analysis.score) * TEAM_SCORE_DELTA_MULTIPLIER
    if team_after > ctx.analysis.score:
        reasons.append(Reason(ReasonKind.SCORE, ctx.t("rec_team_score_up", before=ctx.analysis.score, after=team_after)))
    elif team_after <= ctx.analysis.score and agent.name not in ctx.picked_names:
        score -= NO_BALANCE_IMPROVEMENT_PENALTY
        warnings.append(ctx.t("rec_team_score_flat"))
    return score


def _default_agent_reason(agent: Agent, ctx: ScoringContext) -> str:
    return localized_text(
        {
            "pl": agent.description,
            "en": ctx.t("rec_map_specific", agent=agent.name, map=ctx.map_info.name),
        },
        ctx.language,
    ) or ctx.t("rec_map_specific", agent=agent.name, map=ctx.map_info.name)


def _prioritize_reasons(reasons: list[Reason]) -> tuple[str, ...]:
    unique_reasons_by_text: dict[str, Reason] = {}
    for reason in reasons:
        unique_reasons_by_text.setdefault(reason.text, reason)
    priorities = {
        ReasonKind.COMPOSITION: 0,
        ReasonKind.UTILITY: 0,
        ReasonKind.SYNERGY: 1,
        ReasonKind.MAP: 1,
        ReasonKind.SCORE: 1,
        ReasonKind.PROFILE: 2,
    }
    return tuple(reason.text for reason in sorted(unique_reasons_by_text.values(), key=lambda reason: priorities[reason.kind]))


def _picked_agents(team: tuple[TeamSlot, ...]):
    return [
        AGENTS[slot.agent_name]
        for slot in team
        if slot.agent_name in AGENTS and slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
    ]


def _picked_name_sets(team: tuple[TeamSlot, ...]) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    picked_names = frozenset(
        slot.agent_name
        for slot in team
        if slot.agent_name and slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
    )
    selected_names = frozenset(
        slot.agent_name for slot in team if slot.agent_name and slot.state == SelectionState.SELECTED
    )
    locked_names = frozenset(
        slot.agent_name for slot in team if slot.agent_name and slot.state == SelectionState.LOCKED
    )
    return picked_names, selected_names, locked_names


def _team_score_after(
    agent: Agent,
    ctx: ScoringContext,
) -> float:
    role_counts = ctx.base_role_counts.copy()
    utility_counts = ctx.base_utility_counts.copy()
    role_counts[agent.role] += 1
    utility_counts.update(agent.utility)
    return calculate_team_score(role_counts, utility_counts, ctx.map_info)


def _score_utility_targets(
    agent: Agent,
    ctx: ScoringContext,
    reasons: list[Reason],
) -> float:
    tuning = MAP_TUNING.get(ctx.map_info.name)
    if not tuning:
        return 0.0
    score = 0.0
    filled: list[str] = []
    for utility, target in tuning.utility_targets.items():
        current = ctx.analysis.utility_counts.get(utility, 0)
        if current < target and utility in agent.utility:
            if utility == "smokes":
                weight = UTILITY_WEIGHT_SMOKES
            elif utility == "wall":
                weight = UTILITY_WEIGHT_WALL
            elif utility in {"flank_watch", "info"}:
                weight = UTILITY_WEIGHT_INFO_OR_FLANK
            else:
                weight = UTILITY_WEIGHT_DEFAULT
            if current == 0:
                score += weight
            else:
                score += weight * UTILITY_PARTIAL_TARGET_MULTIPLIER
            filled.append(utility)
    if filled:
        reasons.append(Reason(ReasonKind.UTILITY, ctx.t("rec_utility_thresholds", utility=", ".join(filled))))
    return score


def _score_map_features(agent: Agent, ctx: ScoringContext, reasons: list[Reason], warnings: list[str]) -> float:
    tuning = MAP_TUNING.get(ctx.map_info.name)
    if not tuning:
        return 0.0
    features = tuning.features
    score = 0.0

    feature_hits: list[str] = []
    if "wall_map" in features and "wall" in agent.utility:
        score += FEATURE_WALL_BONUS
        feature_hits.append(ctx.t("rec_feature_wall"))
    if "plant_wall" in features and {"wall", "plant"} & agent.utility:
        score += FEATURE_PLANT_BONUS
        feature_hits.append(ctx.t("rec_feature_plant"))
    if {"long_range", "wide_sites", "recon_lanes"} & features and {"info", "recon"} & agent.utility:
        score += FEATURE_INFO_BONUS
        feature_hits.append(ctx.t("rec_feature_info"))
    if {"tight_chokes", "standard_chokes"} & features and {"flash", "stun", "clear", "suppress"} & agent.utility:
        score += FEATURE_CLEAR_BONUS
        feature_hits.append(ctx.t("rec_feature_clear"))
        if agent.role == Role.DUELIST and "clear" in agent.utility:
            score += FEATURE_DUELIST_CLEAR_BONUS
    if {"three_sites", "flank_pressure", "pinch_attacks"} & features and {"flank_watch", "stall", "info"} & agent.utility:
        score += FEATURE_FLANK_BONUS
        feature_hits.append(ctx.t("rec_feature_flank"))
    if {"fast_exec", "pinch_attacks"} & features and {"mobility", "entry", "flash", "stun"} & agent.utility:
        score += FEATURE_EXECUTE_BONUS
        feature_hits.append(ctx.t("rec_feature_execute"))
    if "mid_control" in features and {"smokes", "info", "flash", "stall"} & agent.utility:
        score += FEATURE_MID_BONUS
        feature_hits.append(ctx.t("rec_feature_mid"))
    if "postplant" in features and "postplant" in agent.utility:
        score += FEATURE_POSTPLANT_BONUS
        feature_hits.append(ctx.t("rec_feature_postplant"))
    if "operator" in features and {"operator", "mobility"} & agent.utility:
        score += FEATURE_OPERATOR_BONUS
        feature_hits.append(ctx.t("rec_feature_operator"))

    if "wall_map" in features and agent.role == Role.CONTROLLER and "wall" not in agent.utility:
        score -= NON_WALL_CONTROLLER_ON_WALL_MAP_PENALTY
        warnings.append(ctx.t("rec_wall_controller_warning"))
    if "tight_chokes" in features and agent.role == Role.DUELIST and "clear" not in agent.utility and "mobility" not in agent.utility:
        score -= DUELIST_TIGHT_CHOKE_PENALTY
        warnings.append(ctx.t("rec_duelist_tight_warning"))

    if feature_hits:
        reasons.append(Reason(ReasonKind.MAP, ctx.t("rec_feature_fit", features=", ".join(dict.fromkeys(feature_hits)))))
    return score


def _score_team_synergy(
    agent: Agent,
    ctx: ScoringContext,
    reasons: list[Reason],
    warnings: list[str],
) -> float:
    allies = [
        AGENTS[slot.agent_name]
        for slot in ctx.team
        if slot.agent_name in AGENTS and slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
    ]
    score = 0.0
    synergy_reasons: list[Reason] = []

    for ally in allies:
        pair = frozenset({agent.name, ally.name})
        pair_bonus = PAIR_SYNERGIES.get(pair)
        if pair_bonus and (not pair_bonus[2] or ctx.map_info.name in pair_bonus[2]):
            score += pair_bonus[0]
            reason = localized_text(pair_bonus[1], ctx.language)
            if reason:
                synergy_reasons.append(Reason(ReasonKind.SYNERGY, reason))

    if agent.role == Role.DUELIST:
        support_count = sum(
            bool({"flash", "info", "clear", "stun", "suppress"} & ally.utility)
            for ally in allies
            if ally.role == Role.INITIATOR
        )
        if support_count:
            score += min(DUELIST_SUPPORT_BONUS_CAP, DUELIST_SUPPORT_BONUS_PER_INITIATOR * support_count)
            synergy_reasons.append(Reason(ReasonKind.SYNERGY, ctx.t("rec_duelist_support")))
        if ctx.analysis.role_counts[Role.INITIATOR] == 0:
            score -= DUELIST_WITHOUT_INITIATOR_PENALTY
            warnings.append(ctx.t("rec_duelist_no_initiator"))
        if "selfish" in agent.traits and ctx.analysis.role_counts[Role.DUELIST] >= 1:
            score -= SELFISH_DUELIST_STACK_PENALTY
            warnings.append(ctx.t("rec_selfish_duelist"))

    if agent.role == Role.INITIATOR and ctx.analysis.role_counts[Role.DUELIST] >= 1:
        if {"flash", "clear", "info", "stun"} & agent.utility:
            score += INITIATOR_WITH_DUELIST_BONUS
            synergy_reasons.append(Reason(ReasonKind.SYNERGY, ctx.t("rec_initiator_duelist")))

    if agent.role == Role.CONTROLLER:
        if ctx.analysis.role_counts[Role.SENTINEL] >= 1:
            score += CONTROLLER_WITH_SENTINEL_BONUS
            synergy_reasons.append(Reason(ReasonKind.SYNERGY, ctx.t("rec_controller_sentinel")))
        if ctx.analysis.role_counts[Role.INITIATOR] >= 1 and "flash" in agent.utility:
            score += CONTROLLER_FLASH_WITH_INITIATOR_BONUS
            synergy_reasons.append(Reason(ReasonKind.SYNERGY, ctx.t("rec_controller_flash")))

    if agent.role == Role.SENTINEL:
        if ctx.analysis.role_counts[Role.CONTROLLER] >= 1:
            score += SENTINEL_WITH_CONTROLLER_BONUS
            synergy_reasons.append(Reason(ReasonKind.SYNERGY, ctx.t("rec_sentinel_controller")))
        if ctx.analysis.role_counts[Role.CONTROLLER] == 0:
            score -= SENTINEL_WITHOUT_CONTROLLER_PENALTY
            warnings.append(ctx.t("rec_sentinel_no_controller"))

    if "postplant" in agent.utility and ctx.analysis.utility_counts.get("postplant", 0) >= 1:
        score += POSTPLANT_STACK_BONUS
        synergy_reasons.append(Reason(ReasonKind.SYNERGY, ctx.t("rec_postplant_stack")))

    if synergy_reasons:
        reasons.extend({reason.text: reason for reason in synergy_reasons}.values())
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
        return MAP_RECOMMENDATION_TOP_BONUS
    if rank == 1:
        return MAP_RECOMMENDATION_SECOND_BONUS
    if rank == 2:
        return MAP_RECOMMENDATION_THIRD_BONUS
    return MAP_RECOMMENDATION_OTHER_BONUS


def _best_role_to_fill(missing_roles: tuple[Role, ...]) -> Role | None:
    for role in ROLE_PRIORITY:
        if role in missing_roles:
            return role
    return None


def advice_for_agent(agent_name: str, map_info: MapInfo, language: str = "en") -> str:
    agent = AGENTS[agent_name]
    map_note = MAP_AGENT_NOTES.get(map_info.name, {}).get(agent.name)
    tip_text = MAP_AGENT_TIPS.get(map_info.name, {}).get(agent.name)
    prefix_parts = []
    if map_note:
        note = localized_text(map_note, language)
        if note:
            prefix_parts.append(t(language, "advice_map_prefix", agent=agent.name, map=map_info.name, note=note))
    if tip_text:
        tips = localized_texts(tip_text, language)
        if tips:
            prefix_parts.append(t(language, "advice_pro_tips", tips=" | ".join(tips)))
    prefix = " ".join(prefix_parts)
    if prefix:
        prefix += " "
    map_role_advice = MAP_ROLE_ADVICE.get(map_info.name, {}).get(agent.role)
    if map_role_advice:
        advice = localized_text(map_role_advice, language)
        if advice:
            return prefix + advice
    if agent.role == Role.CONTROLLER:
        return prefix + t(language, "advice_controller")
    if agent.role == Role.INITIATOR:
        return prefix + t(language, "advice_initiator")
    if agent.role == Role.SENTINEL:
        return prefix + t(language, "advice_sentinel")
    return prefix + t(language, "advice_duelist")
