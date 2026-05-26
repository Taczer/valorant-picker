from __future__ import annotations

from dataclasses import dataclass

from valo_picker.models import Role


@dataclass(frozen=True)
class MapTuning:
    features: frozenset[str]
    utility_targets: dict[str, int]
    role_weights: dict[Role, float]


DEFAULT_ROLE_WEIGHTS = {
    Role.CONTROLLER: 1.25,
    Role.INITIATOR: 1.1,
    Role.SENTINEL: 1.0,
    Role.DUELIST: 0.9,
}


MAP_TUNING: dict[str, MapTuning] = {
    "Ascent": MapTuning(
        frozenset({"mid_control", "recon_lanes", "standard_chokes", "postplant"}),
        {"smokes": 1, "info": 1, "flash": 1, "flank_watch": 1, "postplant": 1, "clear": 1},
        {Role.CONTROLLER: 1.35, Role.INITIATOR: 1.2, Role.SENTINEL: 1.1, Role.DUELIST: 0.9},
    ),
    "Bind": MapTuning(
        frozenset({"teleporters", "tight_chokes", "fast_exec", "postplant"}),
        {"smokes": 1, "flash": 1, "flank_watch": 1, "postplant": 1, "clear": 1},
        {Role.CONTROLLER: 1.35, Role.INITIATOR: 1.1, Role.SENTINEL: 1.0, Role.DUELIST: 1.0},
    ),
    "Breeze": MapTuning(
        frozenset({"long_range", "wide_sites", "wall_map", "flank_pressure", "operator"}),
        {"smokes": 1, "wall": 1, "info": 1, "flank_watch": 1},
        {Role.CONTROLLER: 1.45, Role.INITIATOR: 1.15, Role.SENTINEL: 1.15, Role.DUELIST: 0.9},
    ),
    "Fracture": MapTuning(
        frozenset({"pinch_attacks", "flank_pressure", "fast_exec", "tight_chokes", "stall"}),
        {"smokes": 1, "flash": 1, "flank_watch": 1, "stall": 1, "clear": 1},
        {Role.CONTROLLER: 1.25, Role.INITIATOR: 1.25, Role.SENTINEL: 1.15, Role.DUELIST: 0.95},
    ),
    "Haven": MapTuning(
        frozenset({"three_sites", "long_rotations", "recon_lanes", "flank_pressure"}),
        {"smokes": 1, "info": 2, "flash": 1, "flank_watch": 1, "stall": 1},
        {Role.CONTROLLER: 1.3, Role.INITIATOR: 1.25, Role.SENTINEL: 1.15, Role.DUELIST: 0.9},
    ),
    "Icebox": MapTuning(
        frozenset({"verticality", "wall_map", "plant_wall", "postplant", "long_range"}),
        {"wall": 1, "smokes": 1, "info": 1, "postplant": 1, "stall": 1},
        {Role.CONTROLLER: 1.45, Role.INITIATOR: 1.1, Role.SENTINEL: 1.05, Role.DUELIST: 0.9},
    ),
    "Lotus": MapTuning(
        frozenset({"three_sites", "rotating_doors", "tight_chokes", "flank_pressure", "postplant"}),
        {"smokes": 1, "flash": 1, "flank_watch": 1, "postplant": 1, "clear": 1, "info": 1},
        {Role.CONTROLLER: 1.3, Role.INITIATOR: 1.25, Role.SENTINEL: 1.15, Role.DUELIST: 0.95},
    ),
    "Pearl": MapTuning(
        frozenset({"long_range", "mid_control", "wide_sites", "postplant"}),
        {"smokes": 1, "info": 1, "flank_watch": 1, "postplant": 1, "wall": 1},
        {Role.CONTROLLER: 1.35, Role.INITIATOR: 1.15, Role.SENTINEL: 1.1, Role.DUELIST: 0.9},
    ),
    "Split": MapTuning(
        frozenset({"verticality", "tight_chokes", "mid_control", "stall"}),
        {"smokes": 1, "flash": 1, "wall": 1, "flank_watch": 1, "clear": 1, "stall": 1},
        {Role.CONTROLLER: 1.3, Role.INITIATOR: 1.2, Role.SENTINEL: 1.1, Role.DUELIST: 0.95},
    ),
    "Sunset": MapTuning(
        frozenset({"mid_control", "tight_chokes", "postplant", "flank_pressure"}),
        {"smokes": 1, "info": 1, "flank_watch": 1, "postplant": 1, "clear": 1},
        {Role.CONTROLLER: 1.3, Role.INITIATOR: 1.15, Role.SENTINEL: 1.2, Role.DUELIST: 0.9},
    ),
    "Abyss": MapTuning(
        frozenset({"long_range", "wide_sites", "death_drops", "flank_pressure", "wall_map"}),
        {"smokes": 1, "info": 1, "flank_watch": 1, "wall": 1},
        {Role.CONTROLLER: 1.4, Role.INITIATOR: 1.15, Role.SENTINEL: 1.15, Role.DUELIST: 0.9},
    ),
    "Corrode": MapTuning(
        frozenset({"three_lane", "mid_control", "tight_chokes", "postplant"}),
        {"smokes": 1, "info": 1, "flash": 1, "flank_watch": 1, "clear": 1},
        {Role.CONTROLLER: 1.3, Role.INITIATOR: 1.15, Role.SENTINEL: 1.1, Role.DUELIST: 0.95},
    ),
}
