from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    DUELIST = "Duelist"
    INITIATOR = "Initiator"
    CONTROLLER = "Controller"
    SENTINEL = "Sentinel"


class SelectionState(StrEnum):
    NONE = ""
    SELECTED = "selected"
    LOCKED = "locked"


class LiveStatus(StrEnum):
    NO_CLIENT = "NO_CLIENT"
    WAITING_FOR_AGENT_SELECT = "WAITING_FOR_AGENT_SELECT"
    AGENT_SELECT = "AGENT_SELECT"
    IN_GAME = "IN_GAME"
    ERROR = "ERROR"


class NormalizationIssueKind(StrEnum):
    UNKNOWN_MAP = "unknown_map"
    BAD_PREGAME_PAYLOAD = "bad_pregame_payload"
    BAD_COREGAME_PAYLOAD = "bad_coregame_payload"
    MISSING_PREGAME_MAP = "missing_pregame_map"
    MISSING_COREGAME_MAP = "missing_coregame_map"
    MISSING_ALLY_TEAM = "missing_ally_team"
    MISSING_ALLY_PLAYERS = "missing_ally_players"
    BAD_PLAYER = "bad_player"
    UNKNOWN_STATE = "unknown_state"
    UNKNOWN_CHARACTER = "unknown_character"
    MISSING_CORE_PLAYERS = "missing_core_players"
    NO_ALLIES = "no_allies"


class CompositionProblemKind(StrEnum):
    MISSING_CONTROLLER = "missing_controller"
    MISSING_INITIATOR = "missing_initiator"
    MISSING_SENTINEL = "missing_sentinel"
    MISSING_DUELIST = "missing_duelist"
    TOO_MANY_DUELISTS = "too_many_duelists"
    TWO_DUELISTS_NO_CONTROLLER = "two_duelists_no_controller"
    MISSING_UTILITY = "missing_utility"


@dataclass(frozen=True)
class Agent:
    name: str
    character_id: str
    role: Role
    difficulty: int
    playstyles: frozenset[str]
    solo_queue: bool
    strong_maps: tuple[str, ...]
    weak_maps: tuple[str, ...]
    utility: frozenset[str]
    description: str
    recommendation_reasons: tuple[str, ...]
    traits: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class MapInfo:
    name: str
    map_id: str
    recommended_controllers: tuple[str, ...]
    recommended_initiators: tuple[str, ...]
    recommended_sentinels: tuple[str, ...]
    recommended_duelists: tuple[str, ...]
    minimum_roles: dict[Role, int]
    needs: tuple[str, ...]
    notes: tuple[str, ...]

    def recommended_for_role(self, role: Role) -> tuple[str, ...]:
        if role == Role.CONTROLLER:
            return self.recommended_controllers
        if role == Role.INITIATOR:
            return self.recommended_initiators
        if role == Role.SENTINEL:
            return self.recommended_sentinels
        return self.recommended_duelists


@dataclass(frozen=True)
class TeamSlot:
    player_name: str
    agent_name: str | None = None
    state: SelectionState = SelectionState.NONE
    is_self: bool = False


@dataclass(frozen=True)
class PreGameNormalizationResult:
    map_info: MapInfo | None
    team: tuple[TeamSlot, ...]
    warnings: tuple["NormalizationIssue", ...]
    errors: tuple["NormalizationIssue", ...]
    match_id: str | None
    map_id: str | None


@dataclass(frozen=True)
class NormalizationIssue:
    kind: NormalizationIssueKind
    params: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CompositionProblem:
    kind: CompositionProblemKind
    params: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class UserProfile:
    preferred_styles: frozenset[str] = field(default_factory=frozenset)
    beginner_mode: bool = False


@dataclass(frozen=True)
class TeamAnalysis:
    role_counts: dict[Role, int]
    utility_counts: dict[str, int]
    selected_agents: tuple[str, ...]
    locked_agents: tuple[str, ...]
    problems: tuple[CompositionProblem, ...]
    missing_roles: tuple[Role, ...]
    missing_utility: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class CandidateScore:
    agent: Agent
    score: float
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    team_score_after_pick: float


@dataclass(frozen=True)
class Recommendation:
    map_info: MapInfo
    team: tuple[TeamSlot, ...]
    analysis: TeamAnalysis
    best: CandidateScore
    alternatives: tuple[CandidateScore, ...]
    best_role_to_fill: Role | None
    advice: str
    warning: str | None


@dataclass(frozen=True)
class LivePregameSnapshot:
    status: LiveStatus
    message: str
    valorant_running: bool = False
    lockfile_found: bool = False
    map_name: str | None = None
    mode: str | None = None
    game_state: str | None = None
    puuid: str | None = None
    party_id: str | None = None
    match_id: str | None = None
    region: str | None = None
    shard: str | None = None
    client_version: str | None = None
    normalized_match: PreGameNormalizationResult | None = None
    recommendation: Recommendation | None = None
