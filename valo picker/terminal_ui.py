from __future__ import annotations

import os
from textwrap import wrap

from .data.agents import AGENTS
from .models import LivePregameSnapshot, LiveStatus, Recommendation, SelectionState, TeamSlot
from .recommender import advice_for_agent


WIDTH = 70


def render_live_snapshot(snapshot: LivePregameSnapshot) -> str:
    lines = _header(_title_for(snapshot.status))
    normalized = snapshot.normalized_match
    recommendation = snapshot.recommendation
    map_name = snapshot.map_name or "Unknown"
    if recommendation:
        map_name = recommendation.map_info.name
    elif normalized and normalized.map_info:
        map_name = normalized.map_info.name
    mode = snapshot.mode or "pre-game / agent-select"
    game_state = snapshot.game_state or snapshot.status.value

    lines.extend(_snapshot_summary(snapshot, map_name, mode, game_state))
    lines.append(_line("-"))

    team = recommendation.team if recommendation else (normalized.team if normalized else ())
    lines.extend(_team_section(team, in_game=snapshot.status == LiveStatus.IN_GAME))
    lines.append(_line("-"))

    if recommendation:
        lines.extend(_recommendation_section(recommendation))
    elif snapshot.status == LiveStatus.IN_GAME:
        advice = _in_game_advice(snapshot)
        lines.append("Status:")
        lines.append(f"  {snapshot.message}")
        if advice:
            lines.append("Your Agent Advice:")
            lines.extend(_wrapped_text(advice))
    else:
        lines.append("Status:")
        lines.append(f"  {snapshot.message}")
    if normalized:
        for warning in normalized.warnings[:4]:
            lines.append(f"Warning: {warning}")
        for error in normalized.errors[:4]:
            lines.append(f"Error: {error}")
    lines.extend(_menu())
    return "\n".join(lines)


def render_recommendation(recommendation: Recommendation) -> str:
    snapshot = LivePregameSnapshot(
        status=LiveStatus.AGENT_SELECT,
        message="Sample pre-game lobby.",
        normalized_match=None,
        recommendation=recommendation,
    )
    return render_live_snapshot(snapshot)


def render_agent_list() -> str:
    lines = _header("ALL AGENTS")
    for name in sorted(AGENTS):
        agent = AGENTS[name]
        lines.append(f"[{agent.name:<12}] {agent.role.value:<10} Difficulty {agent.difficulty}/5")
    lines.extend(_menu())
    return "\n".join(lines)


def clear_terminal() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def _header(title: str) -> list[str]:
    return [_line("="), title.center(WIDTH), _line("=")]


def _title_for(status: LiveStatus) -> str:
    if status == LiveStatus.AGENT_SELECT:
        return "PRE-GAME (AGENT SELECT)"
    if status == LiveStatus.IN_GAME:
        return "CURRENT GAME"
    if status == LiveStatus.NO_CLIENT:
        return "VALO PICKER - NO CLIENT"
    if status == LiveStatus.ERROR:
        return "VALO PICKER - ERROR"
    return "VALO PICKER - WAITING"


def _team_section(team: tuple[TeamSlot, ...], in_game: bool = False) -> list[str]:
    lines = ["Your Team:"]
    if not team:
        lines.append("  No players found.")
        return lines
    for slot in team:
        agent_label = _agent_label(slot)
        state = _state_label(slot.state)
        if in_game:
            lines.append(f"{slot.player_name} ({agent_label})")
        else:
            lines.append(f"[{agent_label:<12}] {slot.player_name} ({state}/Lvl ?)")
    return lines


def _recommendation_section(recommendation: Recommendation) -> list[str]:
    best = recommendation.best
    lines = [
        "Recommendation:",
        f"  Best Pick: {best.agent.name} ({best.agent.role.value})",
        f"  Score: {recommendation.analysis.score}/10 -> {best.team_score_after_pick}/10",
    ]
    if recommendation.best_role_to_fill:
        lines.append(f"  Fill Role: {recommendation.best_role_to_fill.value}")
    alternatives = ", ".join(candidate.agent.name for candidate in recommendation.alternatives[:4])
    if alternatives:
        lines.append(f"  Alternatives: {alternatives}")
    lines.append("Problems:")
    problems = recommendation.analysis.problems[:3]
    if problems:
        lines.extend(f"  - {problem}" for problem in problems)
    else:
        lines.append("  - No major composition problems.")
    lines.append("Why:")
    lines.extend(f"  - {reason}" for reason in best.reasons[:3])
    if best.warnings:
        lines.append("Watch:")
        lines.extend(f"  - {warning}" for warning in best.warnings[:2])
    lines.append("Advice:")
    lines.extend(_wrapped_text(_short_advice(recommendation.advice)))
    return lines


def _snapshot_summary(snapshot: LivePregameSnapshot, map_name: str, mode: str, game_state: str) -> list[str]:
    if snapshot.status == LiveStatus.AGENT_SELECT:
        details = [f"Map: {map_name}", f"State: {game_state}"]
        if snapshot.region or snapshot.shard:
            details.append(f"Region: {snapshot.region or '?'}/{snapshot.shard or '?'}")
        lines = [" | ".join(details)]
        if snapshot.match_id:
            lines.append(f"Match: {_short_id(snapshot.match_id)}")
        return lines
    if snapshot.status == LiveStatus.IN_GAME:
        lines = [f"Map: {map_name}", f"Mode: {mode}", f"State: {game_state}"]
        if snapshot.match_id:
            lines.append(f"Match: {_short_id(snapshot.match_id)}")
        return lines

    lines = [f"State: {game_state}", f"Map: {map_name}"]
    if snapshot.valorant_running or snapshot.lockfile_found:
        lines.append(
            "Client: "
            f"Valorant {'yes' if snapshot.valorant_running else 'no'}, "
            f"lockfile {'yes' if snapshot.lockfile_found else 'no'}"
        )
    return lines


def _in_game_advice(snapshot: LivePregameSnapshot) -> str | None:
    normalized = snapshot.normalized_match
    if not normalized or not normalized.map_info:
        return None
    self_slot = next((slot for slot in normalized.team if slot.is_self and slot.agent_name in AGENTS), None)
    if self_slot is None:
        return None
    return advice_for_agent(self_slot.agent_name or "", normalized.map_info)


def _menu() -> list[str]:
    return [
        _line("="),
        "---- Menu ----",
        "1. Refresh Now",
        "2. List all agents",
        "3. Manual Mode",
        "4. Settings",
        "0. Exit",
    ]


def _agent_label(slot: TeamSlot) -> str:
    if slot.agent_name in AGENTS:
        return slot.agent_name or "Unknown"
    if slot.state == SelectionState.NONE:
        return "brak wyboru"
    return "Unknown"


def _state_label(state: SelectionState) -> str:
    if state == SelectionState.LOCKED:
        return "locked"
    if state == SelectionState.SELECTED:
        return "selected"
    return "brak wyboru"


def _line(char: str) -> str:
    return char * WIDTH


def _wrapped_text(text: str, indent: str = "  ") -> list[str]:
    return [indent + line for line in wrap(text, width=WIDTH - len(indent), break_long_words=False)] or [indent]


def _short_advice(text: str) -> str:
    parts = [part.strip() for part in text.split(". ") if part.strip()]
    if len(parts) <= 2:
        return text
    return ". ".join(parts[:2]) + "."


def _short_id(value: str) -> str:
    if len(value) <= 14:
        return value
    return f"{value[:8]}...{value[-4:]}"


def _masked_id(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"
