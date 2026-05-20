from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from textwrap import indent

from .app_settings import (
    AppSettings,
    default_settings_path,
    load_settings,
    save_settings,
    with_profile,
    with_refresh,
    with_start_mode,
)
from .data.agents import AGENTS
from .data.maps import MAPS
from .debug_log import DEFAULT_DEBUG_LOG_PATH, SafeDebugLogger
from .models import SelectionState, TeamSlot, UserProfile
from .recommender import recommend
from .terminal_ui import clear_terminal, render_agent_list, render_live_snapshot, render_recommendation
from .valorant_api import ValorantApiService


STYLE_OPTIONS = {
    "1": ("aggressive", "aggressive entry"),
    "2": ("support", "support"),
    "3": ("lurker", "lurker"),
    "4": ("controller", "smoker/controller"),
    "5": ("defensive", "sentinel/defensive"),
    "6": ("initiator", "initiator/support"),
    "7": ("solo_queue", "solo queue"),
    "8": ("beginner", "beginner"),
}


def main() -> None:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(prog="Valo Picker")
    parser.add_argument("--manual", action="store_true", help="wymuś ręczny tryb CMD")
    parser.add_argument("--live", action="store_true", help="wymuś ekran live nawet przy innym domyślnym trybie")
    parser.add_argument("--sample", action="store_true", help="uruchom przykładowe lobby Ascent")
    parser.add_argument("--status", action="store_true", help="sprawdź lokalny status Valoranta/Riot lockfile")
    parser.add_argument("--refresh", type=float, default=None, help="częstotliwość odświeżania live 2.0-10.0s")
    parser.add_argument("--debug", action="store_true", help="zapisz bezpieczny debug log bez tokenów")
    parser.add_argument("--debug-log", default=str(DEFAULT_DEBUG_LOG_PATH), help="ścieżka debug logu")
    args = parser.parse_args()
    debug_logger = _debug_logger_from_args(args)
    settings = load_settings()
    if args.refresh is not None:
        settings = with_refresh(settings, args.refresh)

    if args.status:
        print_status(debug_logger)
        return
    if args.sample:
        print(render_recommendation(sample_recommendation()))
        return
    if args.manual:
        run_interactive(settings.profile)
        return

    if not args.live and settings.default_start_mode == "manual":
        run_interactive(settings.profile)
        return
    if not args.live and settings.default_start_mode == "status":
        print_status(debug_logger)
        return

    run_live_first(settings, debug_logger)


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


def _configure_console_encoding() -> None:
    if os.name != "nt":
        return
    output_is_console = sys.stdout.isatty()
    input_is_console = sys.stdin.isatty()
    encoding = "utf-8"

    if output_is_console or input_is_console:
        _use_readable_console_font()
        encoding = _windows_oem_encoding()

    for stream in (sys.stdout, sys.stderr):
        _reconfigure_stream(stream, encoding)
    _reconfigure_stream(sys.stdin, encoding if input_is_console else "utf-8")


def _windows_oem_encoding() -> str:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        code_page = kernel32.GetOEMCP()
        if code_page:
            kernel32.SetConsoleOutputCP(code_page)
            kernel32.SetConsoleCP(code_page)
            return f"cp{code_page}"
    except Exception:
        return "utf-8"
    return "utf-8"


def _use_readable_console_font() -> None:
    try:
        import ctypes
        from ctypes import wintypes

        class Coord(ctypes.Structure):
            _fields_ = [
                ("X", wintypes.SHORT),
                ("Y", wintypes.SHORT),
            ]

        class ConsoleFontInfoEx(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.ULONG),
                ("nFont", wintypes.DWORD),
                ("dwFontSize", Coord),
                ("FontFamily", wintypes.UINT),
                ("FontWeight", wintypes.UINT),
                ("FaceName", wintypes.WCHAR * 32),
            ]

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        if handle in (0, -1):
            return
        info = ConsoleFontInfoEx()
        info.cbSize = ctypes.sizeof(ConsoleFontInfoEx)
        if not kernel32.GetCurrentConsoleFontEx(handle, False, ctypes.byref(info)):
            return
        info.FaceName = "Consolas"
        kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(info))
    except Exception:
        pass


def _reconfigure_stream(stream, encoding: str) -> None:
    try:
        stream.reconfigure(encoding=encoding, errors="replace")
    except Exception:
        pass


def run_live_first(settings: AppSettings, debug_logger: SafeDebugLogger | None = None) -> None:
    snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile)
    while True:
        clear_terminal()
        print(render_live_snapshot(snapshot))
        print(f"\nRefresh interval: {settings.refresh_seconds:.1f}s")
        print(f"Profile: {_profile_label(settings.profile)}")
        if debug_logger:
            print(f"Debug log: {debug_logger.path}")
        choice = _read_menu_choice(settings.refresh_seconds)
        if choice is None:
            return
        if choice == "0":
            return
        if choice == "3":
            run_interactive(settings.profile)
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile)
            continue
        if choice == "4":
            settings = _settings_menu(settings)
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile)
            continue
        if choice == "2":
            clear_terminal()
            print(render_agent_list())
            input("\nPress Enter to return to menu...")
            continue
        if choice == "1" or choice == "":
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile)
            continue
        print("Unknown menu option.")
        try:
            input("Press Enter to continue...")
        except EOFError:
            return


def run_interactive(default_profile: UserProfile | None = None) -> None:
    print_header()
    print("Tryb ręczny MVP. Wpisz mapę i aktualne picki teamu.")
    print("Dostępne mapy:", ", ".join(sorted(MAPS)))
    map_name = _ask_map()
    team = _ask_team()
    profile = _ask_profile(default_profile)
    print()
    print_recommendation(recommend(team, MAPS[map_name], profile))
    _pause_after_manual_result()


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


def _ask_profile(default_profile: UserProfile | None = None) -> UserProfile:
    print()
    print("Player profile:")
    for key, (_, label) in STYLE_OPTIONS.items():
        print(f"{key}. {label}")
    if default_profile is not None:
        print(f"Saved profile: {_profile_label(default_profile)}")
        print("Enter = use saved profile, '-' = no profile.")
    raw_styles = input("Style numbers, e.g. 4,7 or empty: ").strip()
    if default_profile is not None and not raw_styles:
        return default_profile
    if raw_styles == "-":
        return UserProfile()
    styles, beginner = _parse_style_choices(raw_styles)
    return UserProfile(preferred_styles=frozenset(styles), beginner_mode=beginner)


def _find_key(raw: str, options: dict) -> str | None:
    raw_folded = raw.strip().lstrip("\ufeff").casefold()
    for key in options:
        if key.casefold() == raw_folded:
            return key
    return None


def _settings_menu(settings: AppSettings) -> AppSettings:
    clear_terminal()
    print_header()
    print("Ustawienia aplikacji")
    print(f"Plik: {default_settings_path()}")
    print()
    print(f"1. Refresh interval: {settings.refresh_seconds:.1f}s")
    print(f"2. Domyślny tryb startu: {_start_mode_label(settings.default_start_mode)}")
    print(f"3. Player profile: {_profile_label(settings.profile)}")
    print()
    print("Enter bez wartości zostawia aktualne ustawienie.")

    raw_refresh = input("Nowy refresh 2-10s: ").strip().replace(",", ".")
    if raw_refresh:
        try:
            settings = with_refresh(settings, float(raw_refresh))
        except ValueError:
            print("Nieprawidłowy refresh, zostawiam poprzednią wartość.")

    print()
    print("Tryb startu:")
    print("1. Live")
    print("2. Manual")
    print("3. Status")
    raw_mode = input("Wybór: ").strip()
    mode_by_choice = {"1": "live", "2": "manual", "3": "status"}
    if raw_mode in mode_by_choice:
        settings = with_start_mode(settings, mode_by_choice[raw_mode])

    profile = settings.profile
    print()
    print("Player profile:")
    for key, (_, label) in STYLE_OPTIONS.items():
        print(f"{key}. {label}")
    print(f"Current: {_profile_label(profile)}")
    print("Type numbers, e.g. 4,7 or 4,7,8. '-' clears profile. Empty = no change.")

    raw_profile = input("Profile numbers: ").strip()
    if raw_profile == "-":
        profile = UserProfile()
    elif raw_profile:
        styles, beginner_from_choice = _parse_style_choices(raw_profile)
        profile = UserProfile(
            preferred_styles=frozenset(styles),
            beginner_mode=beginner_from_choice,
        )

    settings = with_profile(settings, profile)

    try:
        save_settings(settings)
        print("\nZapisano ustawienia.")
    except OSError as exc:
        print(f"\nNie udało się zapisać ustawień: {exc}")
    input("Press Enter to return to menu...")
    return settings


def _start_mode_label(start_mode: str) -> str:
    labels = {
        "live": "Live",
        "manual": "Manual",
        "status": "Status",
    }
    return labels.get(start_mode, "Live")


def _debug_logger_from_args(args) -> SafeDebugLogger | None:
    if not args.debug:
        return None
    return SafeDebugLogger(Path(args.debug_log))


def _parse_style_choices(raw_styles: str) -> tuple[set[str], bool]:
    selected_styles: set[str] = set()
    beginner = False
    for item in (part.strip() for part in raw_styles.split(",")):
        if item in STYLE_OPTIONS:
            style = STYLE_OPTIONS[item][0]
            if style == "beginner":
                beginner = True
            else:
                selected_styles.add(style)
    return selected_styles, beginner


def _profile_label(profile: UserProfile) -> str:
    labels = [
        label
        for style, label in STYLE_OPTIONS.values()
        if style != "beginner" and style in profile.preferred_styles
    ]
    if profile.beginner_mode:
        labels.append("beginner")
    return ", ".join(labels) if labels else "no preferences"


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


def _pause_after_manual_result() -> None:
    try:
        input("\nNaciśnij Enter, żeby wrócić do menu albo zamknąć tryb ręczny...")
    except EOFError:
        return


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
