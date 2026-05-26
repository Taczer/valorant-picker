from __future__ import annotations

from collections import Counter

from .data.agents import AGENTS
from .i18n import t
from .models import Agent, MapInfo, Role, SelectionState, TeamAnalysis, TeamSlot


CORE_UTILITY = ("smokes", "info", "flash", "flank_watch", "postplant")


def known_agent(name: str | None) -> Agent | None:
    if not name:
        return None
    return AGENTS.get(name.strip())


def analyze_team(team: tuple[TeamSlot, ...], map_info: MapInfo, language: str = "en") -> TeamAnalysis:
    picked_agents = [
        agent
        for slot in team
        if slot.state in {SelectionState.SELECTED, SelectionState.LOCKED}
        for agent in [known_agent(slot.agent_name)]
        if agent is not None
    ]
    locked_agents = [
        agent.name
        for slot in team
        if slot.state == SelectionState.LOCKED
        for agent in [known_agent(slot.agent_name)]
        if agent is not None
    ]
    selected_agents = [
        agent.name
        for slot in team
        if slot.state == SelectionState.SELECTED
        for agent in [known_agent(slot.agent_name)]
        if agent is not None
    ]

    role_counts: Counter[Role] = Counter(agent.role for agent in picked_agents)
    utility_counts: Counter[str] = Counter()
    for agent in picked_agents:
        utility_counts.update(agent.utility)

    missing_roles = tuple(
        role for role, minimum in map_info.minimum_roles.items() if role_counts[role] < minimum
    )
    missing_utility = tuple(need for need in map_info.needs if utility_counts[need] == 0)
    problems = list(_detect_problems(role_counts, utility_counts, missing_roles, missing_utility, map_info, language))

    score = calculate_team_score(role_counts, utility_counts, map_info)
    return TeamAnalysis(
        role_counts={role: role_counts[role] for role in Role},
        utility_counts={utility: utility_counts[utility] for utility in sorted(set(CORE_UTILITY) | set(map_info.needs))},
        selected_agents=tuple(selected_agents),
        locked_agents=tuple(locked_agents),
        problems=tuple(problems),
        missing_roles=missing_roles,
        missing_utility=missing_utility,
        score=score,
    )


def calculate_team_score(
    role_counts: dict[Role, int] | Counter[Role],
    utility_counts: dict[str, int] | Counter[str],
    map_info: MapInfo,
) -> float:
    score = 3.0
    for role, minimum in map_info.minimum_roles.items():
        if role_counts[role] >= minimum:
            score += 1.0
        else:
            score -= 0.8 * (minimum - role_counts[role])

    for need in map_info.needs:
        score += 0.45 if utility_counts[need] else -0.45

    if role_counts[Role.CONTROLLER] == 0:
        score -= 1.2
    if role_counts[Role.DUELIST] >= 3:
        score -= 1.3
    if role_counts[Role.DUELIST] == 0:
        score -= 0.4
    if role_counts[Role.CONTROLLER] >= 2 and role_counts[Role.INITIATOR] == 0:
        score -= 0.4

    return round(max(1.0, min(10.0, score)), 1)


def _detect_problems(
    role_counts: Counter[Role],
    utility_counts: Counter[str],
    missing_roles: tuple[Role, ...],
    missing_utility: tuple[str, ...],
    map_info: MapInfo,
    language: str,
) -> tuple[str, ...]:
    problems: list[str] = []
    role_labels = {
        Role.CONTROLLER: t(language, "analysis_missing_controller"),
        Role.INITIATOR: t(language, "analysis_missing_initiator"),
        Role.SENTINEL: t(language, "analysis_missing_sentinel"),
        Role.DUELIST: t(language, "analysis_missing_duelist"),
    }

    for role in missing_roles:
        problems.append(role_labels[role])

    if role_counts[Role.DUELIST] >= 3:
        problems.append(t(language, "analysis_too_many_duelists"))
    elif role_counts[Role.DUELIST] == 2 and Role.CONTROLLER in missing_roles:
        problems.append(t(language, "analysis_two_duelists_no_controller"))

    utility_labels = {
        "smokes": t(language, "analysis_missing_smokes"),
        "info": t(language, "analysis_missing_info"),
        "flash": t(language, "analysis_missing_flash"),
        "flank_watch": t(language, "analysis_missing_flank_watch"),
        "postplant": t(language, "analysis_missing_postplant"),
        "wall": t(language, "analysis_missing_wall"),
        "clear": t(language, "analysis_missing_clear"),
        "stall": t(language, "analysis_missing_stall"),
    }
    for utility in missing_utility:
        label = utility_labels.get(utility)
        if label:
            problems.append(label)

    for note in map_info.notes[:1]:
        if role_counts[Role.CONTROLLER] == 0 or utility_counts["flank_watch"] == 0:
            localized_note = note if language == "pl" else map_info.name
            problems.append(t(language, "analysis_map_context", note=localized_note))

    return tuple(dict.fromkeys(problems))
