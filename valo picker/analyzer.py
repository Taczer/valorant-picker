from __future__ import annotations

from collections import Counter

from .data.agents import AGENTS
from .models import Agent, MapInfo, Role, SelectionState, TeamAnalysis, TeamSlot


CORE_UTILITY = ("smokes", "info", "flash", "flank_watch", "postplant")


def known_agent(name: str | None) -> Agent | None:
    if not name:
        return None
    return AGENTS.get(name.strip())


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
) -> tuple[str, ...]:
    problems: list[str] = []
    role_labels = {
        Role.CONTROLLER: "Brak controllera / smoke'ów.",
        Role.INITIATOR: "Brak inicjatora do informacji, flasha lub czyszczenia pozycji.",
        Role.SENTINEL: "Brak sentinela lub stabilnego flank watcha.",
        Role.DUELIST: "Brak duelista/entry do otwierania site'u.",
    }

    for role in missing_roles:
        problems.append(role_labels[role])

    if role_counts[Role.DUELIST] >= 3:
        problems.append("Team ma za dużo duelistów; kolejny duelist mocno obniży balans składu.")
    elif role_counts[Role.DUELIST] == 2 and Role.CONTROLLER in missing_roles:
        problems.append("Team ma już dwóch duelistów, a nadal brakuje controllera.")

    utility_labels = {
        "smokes": "Brakuje smoke'ów do bezpiecznego wejścia i odcięcia rotacji.",
        "info": "Brakuje źródła informacji typu recon, eye, drone, dog lub turret.",
        "flash": "Brakuje flash supportu pod wejścia.",
        "flank_watch": "Brakuje flank watcha, więc lurk przeciwnika będzie trudny do kontroli.",
        "postplant": "Brakuje mocnego utility pod post-plant.",
        "wall": "Mapa mocno lubi wall controllera albo ścianę pod plant.",
        "clear": "Brakuje utility do czyszczenia bliskich kątów.",
        "stall": "Brakuje utility do zatrzymywania szybkich wejść.",
    }
    for utility in missing_utility:
        label = utility_labels.get(utility)
        if label:
            problems.append(label)

    for note in map_info.notes[:1]:
        if role_counts[Role.CONTROLLER] == 0 or utility_counts["flank_watch"] == 0:
            problems.append(f"Kontekst mapy: {note}")

    return tuple(dict.fromkeys(problems))

