from __future__ import annotations

from collections import Counter

from .data.agents import AGENTS
from .i18n import t
from .models import Agent, CompositionProblem, CompositionProblemKind, MapInfo, Role, SelectionState, TeamAnalysis, TeamSlot


CORE_UTILITY = ("smokes", "info", "flash", "flank_watch", "postplant")


def known_agent(name: str | None) -> Agent | None:
    if not name:
        return None
    return AGENTS.get(name.strip())


ROLE_PROBLEM_KINDS = {
    Role.CONTROLLER: CompositionProblemKind.MISSING_CONTROLLER,
    Role.INITIATOR: CompositionProblemKind.MISSING_INITIATOR,
    Role.SENTINEL: CompositionProblemKind.MISSING_SENTINEL,
    Role.DUELIST: CompositionProblemKind.MISSING_DUELIST,
}


def analyze_team(team: tuple[TeamSlot, ...], map_info: MapInfo) -> TeamAnalysis:
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
    problems = list(_detect_problems(role_counts, utility_counts, missing_roles, missing_utility, map_info))

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
) -> tuple[CompositionProblem, ...]:
    problems: list[CompositionProblem] = []

    for role in missing_roles:
        problems.append(_problem(ROLE_PROBLEM_KINDS[role], role=role.value))

    if role_counts[Role.DUELIST] >= 3:
        problems.append(_problem(CompositionProblemKind.TOO_MANY_DUELISTS))
    elif role_counts[Role.DUELIST] == 2 and Role.CONTROLLER in missing_roles:
        problems.append(_problem(CompositionProblemKind.TWO_DUELISTS_NO_CONTROLLER))

    for utility in missing_utility:
        problems.append(_problem(CompositionProblemKind.MISSING_UTILITY, utility=utility))

    return _dedupe_problems(problems)


def format_composition_problem(problem: CompositionProblem, language: str = "en") -> str:
    key_by_kind = {
        CompositionProblemKind.MISSING_CONTROLLER: "analysis_missing_controller",
        CompositionProblemKind.MISSING_INITIATOR: "analysis_missing_initiator",
        CompositionProblemKind.MISSING_SENTINEL: "analysis_missing_sentinel",
        CompositionProblemKind.MISSING_DUELIST: "analysis_missing_duelist",
        CompositionProblemKind.TOO_MANY_DUELISTS: "analysis_too_many_duelists",
        CompositionProblemKind.TWO_DUELISTS_NO_CONTROLLER: "analysis_two_duelists_no_controller",
    }
    if problem.kind in key_by_kind:
        return t(language, key_by_kind[problem.kind])
    if problem.kind == CompositionProblemKind.MISSING_UTILITY:
        utility = str(problem.params.get("utility", ""))
        return t(language, _utility_problem_key(utility), utility=utility)
    raise ValueError(f"Unhandled CompositionProblemKind: {problem.kind}")


def _utility_problem_key(utility: str) -> str:
    return {
        "smokes": "analysis_missing_smokes",
        "info": "analysis_missing_info",
        "flash": "analysis_missing_flash",
        "flank_watch": "analysis_missing_flank_watch",
        "postplant": "analysis_missing_postplant",
        "wall": "analysis_missing_wall",
        "clear": "analysis_missing_clear",
        "stall": "analysis_missing_stall",
    }.get(utility, "analysis_missing_utility")


def _problem(kind: CompositionProblemKind, **params: object) -> CompositionProblem:
    return CompositionProblem(kind, params)


def _dedupe_problems(problems: list[CompositionProblem]) -> tuple[CompositionProblem, ...]:
    deduped: list[CompositionProblem] = []
    seen: set[tuple[CompositionProblemKind, tuple[tuple[str, object], ...]]] = set()
    for problem in problems:
        key = (problem.kind, tuple(sorted(problem.params.items())))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(problem)
    return tuple(deduped)
