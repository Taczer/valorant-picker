from __future__ import annotations

from typing import Any

from .data.agents import AGENTS_BY_ID
from .data.maps import MAPS_BY_ID
from .models import MapInfo, PreGameNormalizationResult, SelectionState, TeamSlot


def map_from_id(map_id: str) -> MapInfo | None:
    return MAPS_BY_ID.get((map_id or "").lower())


def agent_name_from_id(character_id: str) -> str | None:
    agent = AGENTS_BY_ID.get((character_id or "").lower())
    return agent.name if agent else None


def team_from_pregame_match(payload: dict[str, Any], self_puuid: str | None = None) -> tuple[TeamSlot, ...]:
    return _normalize_team(payload, self_puuid)[0]


def team_from_coregame_match(
    payload: dict[str, Any],
    self_puuid: str | None = None,
    player_names: dict[str, str] | None = None,
) -> tuple[TeamSlot, ...]:
    return _normalize_coregame_team(payload, self_puuid, player_names)[0]


def normalize_pregame_match(payload: dict[str, Any], self_puuid: str | None = None) -> PreGameNormalizationResult:
    warnings: list[str] = []
    errors: list[str] = []
    match_id = _optional_str(payload.get("ID") or payload.get("MatchID"))
    map_id = _optional_str(payload.get("MapID"))

    map_info = None
    if map_id:
        map_info = map_from_id(map_id)
        if map_info is None:
            warnings.append(f"Nieznany MapID: {map_id}")
    else:
        errors.append("Brak MapID w danych pre-game.")

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
    payload: dict[str, Any],
    self_puuid: str | None = None,
    player_names: dict[str, str] | None = None,
) -> PreGameNormalizationResult:
    warnings: list[str] = []
    errors: list[str] = []
    match_id = _optional_str(payload.get("MatchID") or payload.get("ID"))
    map_id = _optional_str(payload.get("MapID"))

    map_info = None
    if map_id:
        map_info = map_from_id(map_id)
        if map_info is None:
            warnings.append(f"Nieznany MapID: {map_id}")
    else:
        errors.append("Brak MapID w danych current-game.")

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
) -> tuple[tuple[TeamSlot, ...], tuple[str, ...], tuple[str, ...]]:
    warnings: list[str] = []
    errors: list[str] = []
    ally_team = payload.get("AllyTeam")
    if not isinstance(ally_team, dict):
        return (), (), ("Brak AllyTeam w danych pre-game.",)

    players = ally_team.get("Players")
    if not isinstance(players, list) or not players:
        return (), (), ("Brak AllyTeam.Players w danych pre-game.",)

    slots: list[TeamSlot] = []
    for index, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            warnings.append(f"Gracz {index}: nieprawidłowy format danych gracza.")
            slots.append(TeamSlot(player_name=f"Gracz {index}"))
            continue

        subject = _optional_str(player.get("Subject")) or f"player-{index}"
        raw_state = _optional_str(player.get("CharacterSelectionState")) or ""
        state = _selection_state_from_raw(raw_state)
        if state == SelectionState.NONE and raw_state not in {"", SelectionState.NONE.value}:
            warnings.append(f"Gracz {index}: nieznany CharacterSelectionState: {raw_state}")

        character_id = _optional_str(player.get("CharacterID")) or ""
        agent_name = agent_name_from_id(character_id)
        if character_id and agent_name is None:
            warnings.append(f"Gracz {index}: nieznany CharacterID: {character_id}")

        is_self = bool(self_puuid and subject == self_puuid)
        slots.append(
            TeamSlot(
                player_name="Ty" if is_self else f"Gracz {index}",
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
) -> tuple[tuple[TeamSlot, ...], tuple[str, ...], tuple[str, ...]]:
    warnings: list[str] = []
    players = payload.get("Players")
    if not isinstance(players, list) or not players:
        return (), (), ("Brak Players w danych current-game.",)

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
        return (), (), ("Nie znaleziono sojuszników w danych current-game.",)

    names = player_names or {}
    slots: list[TeamSlot] = []
    for index, player in enumerate(team_players, start=1):
        subject = _optional_str(player.get("Subject")) or f"player-{index}"
        character_id = _optional_str(player.get("CharacterID")) or ""
        agent_name = agent_name_from_id(character_id)
        if character_id and agent_name is None:
            warnings.append(f"Gracz {index}: nieznany CharacterID: {character_id}")

        is_self = bool(self_puuid and subject == self_puuid)
        player_name = names.get(subject) or ("Ty" if is_self else f"Gracz {index}")
        slots.append(
            TeamSlot(
                player_name=player_name,
                agent_name=agent_name,
                state=SelectionState.LOCKED if agent_name else SelectionState.NONE,
                is_self=is_self,
            )
        )

    return tuple(slots), tuple(warnings), ()


def _selection_state_from_raw(raw_state: str) -> SelectionState:
    if raw_state in {SelectionState.SELECTED.value, SelectionState.LOCKED.value}:
        return SelectionState(raw_state)
    return SelectionState.NONE


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None
