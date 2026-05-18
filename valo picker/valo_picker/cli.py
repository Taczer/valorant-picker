from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from textwrap import indent

from .data.agents import AGENTS
from .data.maps import MAPS
from .debug_log import DEFAULT_DEBUG_LOG_PATH, SafeDebugLogger
from .models import SelectionState, TeamSlot, UserProfile
from .recommender import recommend
from .terminal_ui import clear_terminal, render_agent_list, render_live_snapshot, render_recommendation
from .valorant_api import ValorantApiService


STYLE_OPTIONS = {
    "1": ("aggressive", "agresywny entry"),
    "2": ("support", "spokojny support"),
    "3": ("lurker", "lurker"),
    "4": ("controller", "smoker/controller"),
    "5": ("defensive", "sentinel/defensywny"),
    "6": ("initiator", "initiator/support"),
    "7": ("solo_queue", "solo queue"),
    "8": ("beginner", "początkujący"),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="Valo Picker")
    parser.add_argument("--manual", action="store_true", help="wymuś ręczny tryb CMD")
    parser.add_argument("--sample", action="store_true", help="uruchom przykładowe lobby Ascent")
    parser.add_argument("--status", action="store_true", help="sprawdź lokalny status Valoranta/Riot lockfile")
    parser.add_argument("--refresh", type=float, default=5.0, help="częstotliwość odświeżania live 2.0-10.0s")
    parser.add_argument("--debug", action="store_true", help="zapisz bezpieczny debug log bez tokenów")
    parser.add_argument("--debug-log", default=str(DEFAULT_DEBUG_LOG_PATH), help="ścieżka debug logu")
    args = parser.parse_args()
    debug_logger = _debug_logger_from_args(args)

    if args.status:
        print_status(debug_logger)
        return
    if args.sample:
        print(render_recommendation(sample_recommendation()))
        return
    if args.manual:
        run_interactive()
        return

    run_live_first(_clamp_refresh(args.refresh), debug_logger)


def print_status(debug_logger: SafeDebugLogger | None = None) -> None:
    print_header()
    if debug_logger:
        print(f"Debug log: {debug_logger.path}")
    print("Status lokalnego klienta:")
    print(f"- Valorant uruchomiony: {'tak' if ValorantApiService.is_valorant_running() else 'nie'}")
    auth = ValorantApiService.try_load_local_auth()
    if auth is None:
        print("- Lockfile Riot Client: nie znaleziono albo brak dostępu")
        print("- Integracja API: niedostępna w tej sesji")
        return
    print("- Lockfile Riot Client: znaleziono")
    print(f"- Lokalny endpoint: {auth.protocol}://127.0.0.1:{auth.port}")
    print("- Token lockfile nie został zapisany ani wyświetlony")
    snapshot = ValorantApiService.read_live_snapshot(debug_logger)
    print(f"- Live status: {snapshot.status.value}")
    if snapshot.region or snapshot.shard:
        print(f"- Region/shard: {snapshot.region or '?'} / {snapshot.shard or '?'}")
    if snapshot.puuid:
        print(f"- PUUID: {_mask_id(snapshot.puuid)}")
    if snapshot.party_id:
        print(f"- PartyID: {snapshot.party_id}")
    if snapshot.match_id:
        print(f"- MatchID: {snapshot.match_id}")
    if snapshot.client_version:
        print(f"- Client version: {snapshot.client_version}")
    if snapshot.normalized_match and snapshot.normalized_match.team:
        print("- Team:")
        for slot in snapshot.normalized_match.team:
            print(f"  - {slot.player_name} ({slot.agent_name or 'Unknown'})")
    print(f"- Komunikat: {snapshot.message}")


def run_live_first(refresh_seconds: float, debug_logger: SafeDebugLogger | None = None) -> None:
    snapshot = ValorantApiService.read_live_snapshot(debug_logger)
    while True:
        clear_terminal()
        print(render_live_snapshot(snapshot))
        print(f"\nRefresh interval: {refresh_seconds:.1f}s")
        if debug_logger:
            print(f"Debug log: {debug_logger.path}")
        choice = _read_menu_choice(refresh_seconds)
        if choice is None:
            return
        if choice == "0":
            return
        if choice == "5":
            run_interactive()
            return
        if choice == "4":
            clear_terminal()
            print(render_agent_list())
            input("\nPress Enter to return to menu...")
            continue
        if choice in {"1", "2"}:
            continue
        if choice == "3" or choice == "":
            snapshot = ValorantApiService.read_live_snapshot(debug_logger)
            continue
        print("Unknown menu option.")
        try:
            input("Press Enter to continue...")
        except EOFError:
            return


def run_interactive() -> None:
    print_header()
    print("Tryb ręczny MVP. Wpisz mapę i aktualne picki teamu.")
    print("Dostępne mapy:", ", ".join(sorted(MAPS)))
    map_name = _ask_map()
    team = _ask_team()
    profile = _ask_profile()
    print()
    print_recommendation(recommend(team, MAPS[map_name], profile))


def sample_recommendation():
    team = (
        TeamSlot("Gracz 1", "Jett", SelectionState.LOCKED),
        TeamSlot("Gracz 2", "Reyna", SelectionState.SELECTED),
        TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
        TeamSlot("Gracz 4", "Sova", SelectionState.LOCKED),
        TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
    )
    profile = UserProfile(preferred_styles=frozenset({"controller", "solo_queue"}))
    return recommend(team, MAPS["Ascent"], profile)


def print_recommendation(result) -> None:
    print_header()
    print(f"Mapa: {result.map_info.name}")
    print("Aktualny team:")
    for slot in result.team:
        agent = slot.agent_name or "brak wyboru"
        state = _state_label(slot.state)
        role = AGENTS[slot.agent_name].role.value if slot.agent_name in AGENTS else "-"
        print(f"- {slot.player_name}: {agent} - {state} - {role}")

    print()
    if result.best_role_to_fill:
        print(f"Najlepsza rola do uzupełnienia: {result.best_role_to_fill.value}")
    print("Największe problemy teamu:")
    if result.analysis.problems:
        print(indent("\n".join(f"- {problem}" for problem in result.analysis.problems[:6]), "  "))
    else:
        print("  - Brak dużych problemów kompozycji.")

    best = result.best
    print()
    print(f"Najlepszy pick: {best.agent.name} ({best.agent.role.value})")
    print("Dlaczego:")
    print(indent("\n".join(f"- {reason}" for reason in best.reasons[:6]), "  "))
    if best.warnings:
        print("Uwagi:")
        print(indent("\n".join(f"- {warning}" for warning in best.warnings[:3]), "  "))

    print()
    print("Alternatywy:")
    for index, candidate in enumerate(result.alternatives, start=1):
        first_reason = candidate.reasons[0] if candidate.reasons else candidate.agent.description
        print(f"{index}. {candidate.agent.name} ({candidate.agent.role.value}) - {first_reason}")

    print()
    print(f"Ocena teamu teraz: {result.analysis.score}/10")
    print(f"Ocena teamu po picku {best.agent.name}: {best.team_score_after_pick}/10")
    if result.warning:
        print(f"Ostrzeżenie: {result.warning}")
    print(f"Porada: {result.advice}")


def _ask_map() -> str:
    while True:
        raw = input("Mapa: ").strip()
        match = _find_key(raw, MAPS)
        if match:
            return match
        print("Nie znam tej mapy. Spróbuj np. Ascent, Bind, Haven, Lotus.")


def _ask_team() -> tuple[TeamSlot, ...]:
    team: list[TeamSlot] = []
    print()
    print("Wpisuj agentów sojuszników. Puste pole oznacza brak wyboru.")
    print("Stan: l = locked, s = selected, puste = brak wyboru.")
    for index in range(1, 6):
        is_self = index == 5
        player = "Ty" if is_self else f"Gracz {index}"
        agent_name = _ask_agent(player)
        state = SelectionState.NONE
        if agent_name:
            state = _ask_state(player)
        team.append(TeamSlot(player, agent_name, state, is_self=is_self))
    return tuple(team)


def _ask_agent(player: str) -> str | None:
    while True:
        raw = input(f"{player} - agent: ").strip()
        if not raw:
            return None
        match = _find_key(raw, AGENTS)
        if match:
            return match
        print("Nie znam tego agenta. Przykłady: Omen, Sova, Jett, Killjoy.")


def _ask_state(player: str) -> SelectionState:
    raw = input(f"{player} - stan [l/s/puste]: ").strip().lower()
    if raw == "l":
        return SelectionState.LOCKED
    if raw == "s":
        return SelectionState.SELECTED
    return SelectionState.NONE


def _ask_profile() -> UserProfile:
    print()
    print("Profil gracza:")
    for key, (_, label) in STYLE_OPTIONS.items():
        print(f"{key}. {label}")
    raw_styles = input("Style po przecinku, np. 4,7 albo puste: ").strip()
    selected_styles = set()
    for item in raw_styles.replace(" ", "").split(","):
        if item in STYLE_OPTIONS:
            selected_styles.add(STYLE_OPTIONS[item][0])

    beginner = "beginner" in selected_styles
    return UserProfile(
        preferred_styles=frozenset(selected_styles),
        beginner_mode=beginner,
    )


def _find_key(raw: str, options: dict) -> str | None:
    raw_folded = raw.strip().lstrip("\ufeff").casefold()
    for key in options:
        if key.casefold() == raw_folded:
            return key
    return None


def _clamp_refresh(value: float) -> float:
    return max(2.0, min(10.0, value))


def _debug_logger_from_args(args) -> SafeDebugLogger | None:
    if not args.debug:
        return None
    return SafeDebugLogger(Path(args.debug_log))


def _read_menu_choice(timeout_seconds: float) -> str | None:
    if not sys.stdin.isatty():
        try:
            return input("Choice: ").strip().lstrip("\ufeff")
        except EOFError:
            return None
    if os.name == "nt":
        return _read_windows_choice(timeout_seconds)
    try:
        import select

        print("Choice: ", end="", flush=True)
        readable, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if readable:
            return sys.stdin.readline().strip().lstrip("\ufeff")
        return ""
    except Exception:
        try:
            return input("Choice: ").strip().lstrip("\ufeff")
        except EOFError:
            return None


def _read_windows_choice(timeout_seconds: float) -> str:
    import msvcrt

    print("Choice: ", end="", flush=True)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            char = msvcrt.getwch()
            if char in {"\r", "\n"}:
                print()
                return ""
            print(char)
            return char.strip().lstrip("\ufeff")
        time.sleep(0.05)
    print()
    return ""


def _mask_id(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _state_label(state: SelectionState) -> str:
    if state == SelectionState.LOCKED:
        return "locked"
    if state == SelectionState.SELECTED:
        return "selected"
    return "brak wyboru"


def print_header() -> None:
    print("=" * 58)
    print("VALO PICKER - CMD MVP")
    print("=" * 58)
