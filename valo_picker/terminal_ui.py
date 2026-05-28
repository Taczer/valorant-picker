from __future__ import annotations

import os
import re
from textwrap import wrap

from .analyzer import format_composition_problem
from .data.agents import AGENTS
from .i18n import t
from .models import LivePregameSnapshot, LiveStatus, Recommendation, SelectionState, TeamSlot
from .normalizer import format_normalization_issue
from .recommender import advice_for_agent


WIDTH = 70
MAX_NORMALIZATION_WARNINGS = 4
MAX_NORMALIZATION_ERRORS = 4
MAX_ALTERNATIVES = 4
MAX_PROBLEMS = 3
MAX_REASONS = 3
MAX_WARNINGS = 2


def render_live_snapshot(snapshot: LivePregameSnapshot, language: str = "en") -> str:
    lines = _header(_title_for(snapshot.status, language))
    normalized = snapshot.normalized_match
    recommendation = snapshot.recommendation
    map_name = snapshot.map_name or t(language, "unknown_map")
    if recommendation:
        map_name = recommendation.map_info.name
    elif normalized and normalized.map_info:
        map_name = normalized.map_info.name
    mode = snapshot.mode or t(language, "default_mode")
    game_state = snapshot.game_state or snapshot.status.value

    lines.extend(_snapshot_summary(snapshot, map_name, mode, game_state, language))
    lines.append(_line("-"))

    team = recommendation.team if recommendation else (normalized.team if normalized else ())
    lines.extend(_team_section(team, in_game=snapshot.status == LiveStatus.IN_GAME, language=language))
    lines.append(_line("-"))

    if recommendation:
        lines.extend(_recommendation_section(recommendation, language))
    elif snapshot.status == LiveStatus.IN_GAME:
        advice = _in_game_advice(snapshot, language)
        lines.append(t(language, "render_status"))
        lines.append(f"  {snapshot.message}")
        if advice:
            lines.append(t(language, "render_agent_advice"))
            lines.extend(_wrapped_text(advice))
    else:
        lines.append(t(language, "render_status"))
        lines.append(f"  {snapshot.message}")
    if normalized:
        for warning in normalized.warnings[:MAX_NORMALIZATION_WARNINGS]:
            lines.append(t(language, "render_warning", warning=format_normalization_issue(warning, language)))
        for error in normalized.errors[:MAX_NORMALIZATION_ERRORS]:
            lines.append(t(language, "render_error", error=format_normalization_issue(error, language)))
    lines.extend(_menu(language))
    return "\n".join(lines)


def render_recommendation(recommendation: Recommendation, language: str = "en") -> str:
    snapshot = LivePregameSnapshot(
        status=LiveStatus.AGENT_SELECT,
        message="Sample pre-game lobby.",
        normalized_match=None,
        recommendation=recommendation,
    )
    return render_live_snapshot(snapshot, language)


def render_agent_list(language: str = "en") -> str:
    lines = _header(t(language, "render_all_agents"))
    for name in sorted(AGENTS):
        agent = AGENTS[name]
        lines.append(t(language, "render_agent_row", name=agent.name, role=agent.role.value, difficulty=agent.difficulty))
    lines.extend(_menu(language))
    return "\n".join(lines)


def clear_terminal() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def _header(title: str) -> list[str]:
    return [_line("="), title.center(WIDTH), _line("=")]


def _title_for(status: LiveStatus, language: str) -> str:
    if status == LiveStatus.AGENT_SELECT:
        return t(language, "snapshot_title_agent_select")
    if status == LiveStatus.IN_GAME:
        return t(language, "snapshot_title_current_game")
    if status == LiveStatus.NO_CLIENT:
        return t(language, "snapshot_title_no_client")
    if status == LiveStatus.ERROR:
        return t(language, "snapshot_title_error")
    return t(language, "snapshot_title_waiting")


def _team_section(team: tuple[TeamSlot, ...], in_game: bool = False, language: str = "en") -> list[str]:
    lines = [t(language, "render_team")]
    if not team:
        lines.append(t(language, "render_no_players"))
        return lines
    for slot in team:
        agent_label = _agent_label(slot, language)
        player_label = _player_label(slot, language)
        state = _state_label(slot.state, language)
        if in_game:
            lines.append(f"{player_label} ({agent_label})")
        else:
            lines.append(f"[{agent_label:<12}] {player_label} ({state}/{t(language, 'render_level_unknown')})")
    return lines


def _recommendation_section(recommendation: Recommendation, language: str) -> list[str]:
    best = recommendation.best
    lines = [
        t(language, "render_recommendation"),
        t(language, "render_best_pick", agent=best.agent.name, role=best.agent.role.value),
        t(language, "render_score", before=recommendation.analysis.score, after=best.team_score_after_pick),
    ]
    if recommendation.best_role_to_fill:
        lines.append(t(language, "render_fill_role", role=recommendation.best_role_to_fill.value))
    alternatives = ", ".join(candidate.agent.name for candidate in recommendation.alternatives[:MAX_ALTERNATIVES])
    if alternatives:
        lines.append(t(language, "render_alternatives", alternatives=alternatives))
    lines.append(t(language, "render_problems"))
    problems = recommendation.analysis.problems[:MAX_PROBLEMS]
    if problems:
        lines.extend(f"  - {format_composition_problem(problem, language)}" for problem in problems)
    else:
        lines.append(t(language, "render_no_problems"))
    lines.append(t(language, "render_why"))
    lines.extend(f"  - {reason}" for reason in best.reasons[:MAX_REASONS])
    if best.warnings:
        lines.append(t(language, "render_watch"))
        lines.extend(f"  - {warning}" for warning in best.warnings[:MAX_WARNINGS])
    lines.append(t(language, "render_advice"))
    lines.extend(_wrapped_text(_short_advice(recommendation.advice)))
    return lines


def _snapshot_summary(snapshot: LivePregameSnapshot, map_name: str, mode: str, game_state: str, language: str) -> list[str]:
    if snapshot.status == LiveStatus.AGENT_SELECT:
        details = [t(language, "snapshot_map", map=map_name), t(language, "snapshot_state", state=game_state)]
        if snapshot.region or snapshot.shard:
            details.append(t(language, "snapshot_region", region=snapshot.region or "?", shard=snapshot.shard or "?"))
        lines = [" | ".join(details)]
        if snapshot.match_id:
            lines.append(t(language, "snapshot_match", match_id=_short_id(snapshot.match_id)))
        return lines
    if snapshot.status == LiveStatus.IN_GAME:
        lines = [
            t(language, "snapshot_map", map=map_name),
            t(language, "snapshot_mode", mode=mode),
            t(language, "snapshot_state", state=game_state),
        ]
        if snapshot.match_id:
            lines.append(t(language, "snapshot_match", match_id=_short_id(snapshot.match_id)))
        return lines

    lines = [t(language, "snapshot_state", state=game_state), t(language, "snapshot_map", map=map_name)]
    if snapshot.valorant_running or snapshot.lockfile_found:
        lines.append(
            t(
                language,
                "snapshot_client",
                valorant=t(language, "status_yes") if snapshot.valorant_running else t(language, "status_no"),
                lockfile=t(language, "status_yes") if snapshot.lockfile_found else t(language, "status_no"),
            )
        )
    return lines


def _in_game_advice(snapshot: LivePregameSnapshot, language: str) -> str | None:
    normalized = snapshot.normalized_match
    if not normalized or not normalized.map_info:
        return None
    self_slot = next((slot for slot in normalized.team if slot.is_self and slot.agent_name in AGENTS), None)
    if self_slot is None:
        return None
    return advice_for_agent(self_slot.agent_name or "", normalized.map_info, language)


def _menu(language: str) -> list[str]:
    return [
        _line("="),
        t(language, "menu_title"),
        t(language, "menu_refresh"),
        t(language, "menu_agents"),
        t(language, "menu_manual"),
        t(language, "menu_settings"),
        t(language, "menu_exit"),
    ]


def _agent_label(slot: TeamSlot, language: str) -> str:
    if slot.agent_name in AGENTS:
        return slot.agent_name or t(language, "unknown_agent")
    if slot.state == SelectionState.NONE:
        return t(language, "state_none")
    return t(language, "unknown_agent")


def _player_label(slot: TeamSlot, language: str) -> str:
    if slot.is_self and slot.player_name == "You":
        return t(language, "manual_self")
    match = re.fullmatch(r"Player (\d+)", slot.player_name)
    if match:
        return t(language, "manual_player", index=int(match.group(1)))
    return slot.player_name


def _state_label(state: SelectionState, language: str) -> str:
    if state == SelectionState.LOCKED:
        return t(language, "state_locked")
    if state == SelectionState.SELECTED:
        return t(language, "state_selected")
    return t(language, "state_none")


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
