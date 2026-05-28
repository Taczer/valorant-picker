from __future__ import annotations

from typing import Any

from .data.agents import AGENTS_BY_ID
from .data.maps import MAPS_BY_ID
from .i18n import t
from .models import MapInfo, NormalizationIssue, NormalizationIssueKind, PreGameNormalizationResult, SelectionState, TeamSlot


def map_from_id(map_id: str) -> MapInfo | None:
    return MAPS_BY_ID.get((map_id or "").lower())


def agent_name_from_id(character_id: str) -> str | None:
    agent = AGENTS_BY_ID.get((character_id or "").lower())
    return agent.name if agent else None


def team_from_pregame_match(payload: Any, self_puuid: str | None = None) -> tuple[TeamSlot, ...]:
    return normalize_pregame_match(payload, self_puuid).team


def team_from_coregame_match(
    payload: Any,
    self_puuid: str | None = None,
    player_names: dict[str, str] | None = None,
) -> tuple[TeamSlot, ...]:
    return normalize_coregame_match(payload, self_puuid, player_names).team


def normalize_pregame_match(payload: Any, self_puuid: str | None = None) -> PreGameNormalizationResult:
    warnings: list[NormalizationIssue] = []
    errors: list[NormalizationIssue] = []
    if not isinstance(payload, dict):
        return PreGameNormalizationResult(
            map_info=None,
            team=(),
            warnings=(),
            errors=(_issue(NormalizationIssueKind.BAD_PREGAME_PAYLOAD),),
            match_id=None,
            map_id=None,
        )

    match_id = _optional_str(payload.get("ID") or payload.get("MatchID"))
    map_id = _optional_str(payload.get("MapID"))

    map_info = None
    if map_id:
        map_info = map_from_id(map_id)
        if map_info is None:
            warnings.append(_issue(NormalizationIssueKind.UNKNOWN_MAP, map_id=map_id))
    else:
        errors.append(_issue(NormalizationIssueKind.MISSING_PREGAME_MAP))

    team, team_warnings, team_errors = _normalize_team(payload, self_puuid)
    warnings.extend(team_warnings)
    errors.extend(team_errors)

    return PreGameNormalizationResult(
        map_info=map_info,
        team=team,
        warnings=tuple(warnings),
        errors=tuple(errors),
        match_id=match_id,
        map_id=map_id,
    )


def normalize_coregame_match(
    payload: Any,
    self_puuid: str | None = None,
    player_names: dict[str, str] | None = None,
) -> PreGameNormalizationResult:
    warnings: list[NormalizationIssue] = []
    errors: list[NormalizationIssue] = []
    if not isinstance(payload, dict):
        return PreGameNormalizationResult(
            map_info=None,
            team=(),
            warnings=(),
            errors=(_issue(NormalizationIssueKind.BAD_COREGAME_PAYLOAD),),
            match_id=None,
            map_id=None,
        )

    match_id = _optional_str(payload.get("MatchID") or payload.get("ID"))
    map_id = _optional_str(payload.get("MapID"))

    map_info = None
    if map_id:
        map_info = map_from_id(map_id)
        if map_info is None:
            warnings.append(_issue(NormalizationIssueKind.UNKNOWN_MAP, map_id=map_id))
    else:
        errors.append(_issue(NormalizationIssueKind.MISSING_COREGAME_MAP))

    team, team_warnings, team_errors = _normalize_coregame_team(payload, self_puuid, player_names)
    warnings.extend(team_warnings)
    errors.extend(team_errors)

    return PreGameNormalizationResult(
        map_info=map_info,
        team=team,
        warnings=tuple(warnings),
        errors=tuple(errors),
        match_id=match_id,
        map_id=map_id,
    )


def _normalize_team(
    payload: dict[str, Any], self_puuid: str | None = None
) -> tuple[tuple[TeamSlot, ...], tuple[NormalizationIssue, ...], tuple[NormalizationIssue, ...]]:
    warnings: list[NormalizationIssue] = []
    errors: list[NormalizationIssue] = []
    ally_team = payload.get("AllyTeam")
    if not isinstance(ally_team, dict):
        return (), (), (_issue(NormalizationIssueKind.MISSING_ALLY_TEAM),)

    players = ally_team.get("Players")
    if not isinstance(players, list) or not players:
        return (), (), (_issue(NormalizationIssueKind.MISSING_ALLY_PLAYERS),)

    slots: list[TeamSlot] = []
    for index, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            warnings.append(_issue(NormalizationIssueKind.BAD_PLAYER, index=index))
            slots.append(TeamSlot(player_name=_player_label(index)))
            continue

        subject = _optional_str(player.get("Subject")) or f"player-{index}"
        raw_state = _optional_str(player.get("CharacterSelectionState")) or ""
        state = _selection_state_from_raw(raw_state)
        if state == SelectionState.NONE and raw_state not in {"", SelectionState.NONE.value}:
            warnings.append(_issue(NormalizationIssueKind.UNKNOWN_STATE, index=index, state=raw_state))

        character_id = _optional_str(player.get("CharacterID")) or ""
        agent_name = agent_name_from_id(character_id)
        if character_id and agent_name is None:
            warnings.append(_issue(NormalizationIssueKind.UNKNOWN_CHARACTER, index=index, character_id=character_id))

        is_self = bool(self_puuid and subject == self_puuid)
        slots.append(
            TeamSlot(
                player_name="You" if is_self else _player_label(index),
                agent_name=agent_name,
                state=state,
                is_self=is_self,
            )
        )

    return tuple(slots), tuple(warnings), tuple(errors)


def _normalize_coregame_team(
    payload: dict[str, Any],
    self_puuid: str | None = None,
    player_names: dict[str, str] | None = None,
) -> tuple[tuple[TeamSlot, ...], tuple[NormalizationIssue, ...], tuple[NormalizationIssue, ...]]:
    warnings: list[NormalizationIssue] = []
    players = payload.get("Players")
    if not isinstance(players, list) or not players:
        return (), (), (_issue(NormalizationIssueKind.MISSING_CORE_PLAYERS),)

    self_team_id = None
    if self_puuid:
        for player in players:
            if isinstance(player, dict) and player.get("Subject") == self_puuid:
                self_team_id = _optional_str(player.get("TeamID"))
                break

    team_players = [
        player
        for player in players
        if isinstance(player, dict) and (self_team_id is None or player.get("TeamID") == self_team_id)
    ]
    if not team_players:
        return (), (), (_issue(NormalizationIssueKind.NO_ALLIES),)

    names = player_names or {}
    slots: list[TeamSlot] = []
    for index, player in enumerate(team_players, start=1):
        subject = _optional_str(player.get("Subject")) or f"player-{index}"
        character_id = _optional_str(player.get("CharacterID")) or ""
        agent_name = agent_name_from_id(character_id)
        if character_id and agent_name is None:
            warnings.append(_issue(NormalizationIssueKind.UNKNOWN_CHARACTER, index=index, character_id=character_id))

        is_self = bool(self_puuid and subject == self_puuid)
        player_name = names.get(subject) or ("You" if is_self else _player_label(index))
        slots.append(
            TeamSlot(
                player_name=player_name,
                agent_name=agent_name,
                state=SelectionState.LOCKED if agent_name else SelectionState.NONE,
                is_self=is_self,
            )
        )

    return tuple(slots), tuple(warnings), ()


def format_normalization_issue(issue: NormalizationIssue, language: str = "en") -> str:
    return t(language, f"normalizer_{issue.kind.value}", **issue.params)


def _issue(kind: NormalizationIssueKind, **params: object) -> NormalizationIssue:
    return NormalizationIssue(kind, params)


def _player_label(index: int) -> str:
    return f"Player {index}"


def _selection_state_from_raw(raw_state: str) -> SelectionState:
    if raw_state in {SelectionState.SELECTED.value, SelectionState.LOCKED.value}:
        return SelectionState(raw_state)
    return SelectionState.NONE


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None
