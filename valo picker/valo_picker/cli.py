from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from textwrap import indent

from . import __version__
from .app_settings import (
    AppSettings,
    default_settings_path,
    load_settings,
    save_settings,
    with_language,
    with_profile,
    with_refresh,
    with_start_mode,
)
from .data.agents import AGENTS
from .data.maps import MAPS
from .analyzer import format_composition_problem
from .debug_log import DEFAULT_DEBUG_LOG_PATH, SafeDebugLogger
from .i18n import t
from .models import LivePregameSnapshot, SelectionState, TeamSlot, UserProfile
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


class ManualBackToMenu(Exception):
    pass


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
    parser.add_argument("--version", action="store_true", help="pokaż wersję aplikacji")
    args = parser.parse_args()
    if args.version:
        print(f"Valo Picker {__version__}")
        return
    debug_logger = _debug_logger_from_args(args)
    settings = load_settings()
    if args.refresh is not None:
        settings = with_refresh(settings, args.refresh)

    if args.status:
        print_status(debug_logger, settings.language)
        return
    if args.sample:
        print(render_recommendation(sample_recommendation(settings.language), settings.language))
        return
    if args.manual:
        run_interactive(settings.profile, settings.language)
        return

    if not args.live and settings.default_start_mode == "manual":
        run_interactive(settings.profile, settings.language)
        return
    if not args.live and settings.default_start_mode == "status":
        print_status(debug_logger, settings.language)
        return

    run_live_first(settings, debug_logger)


def print_status(debug_logger: SafeDebugLogger | None = None, language: str = "en") -> None:
    print_header(language)
    if debug_logger:
        print(t(language, "status_debug_log", path=debug_logger.path))
    print(t(language, "status_title"))
    print(t(language, "status_valorant", value=t(language, "status_yes") if ValorantApiService.is_valorant_running() else t(language, "status_no")))
    auth = ValorantApiService.try_load_local_auth()
    if auth is None:
        print(t(language, "status_lockfile_missing"))
        print(t(language, "status_api_unavailable"))
        return
    print(t(language, "status_lockfile_found"))
    print(t(language, "status_endpoint", endpoint=f"{auth.protocol}://127.0.0.1:{auth.port}"))
    print(t(language, "status_token_safe"))
    snapshot = ValorantApiService.read_live_snapshot(debug_logger, language=language)
    print(t(language, "status_live", status=snapshot.status.value))
    if snapshot.region or snapshot.shard:
        print(t(language, "status_region", region=snapshot.region or "?", shard=snapshot.shard or "?"))
    if snapshot.puuid:
        print(t(language, "status_puuid", puuid=_mask_id(snapshot.puuid)))
    if snapshot.party_id:
        print(t(language, "status_party", party_id=snapshot.party_id))
    if snapshot.match_id:
        print(t(language, "status_match", match_id=snapshot.match_id))
    if snapshot.client_version:
        print(t(language, "status_client_version", client_version=snapshot.client_version))
    if snapshot.normalized_match and snapshot.normalized_match.team:
        print(t(language, "status_team"))
        for slot in snapshot.normalized_match.team:
            print(f"  - {_player_label(slot, language)} ({slot.agent_name or t(language, 'unknown_agent')})")
    print(t(language, "status_message", message=snapshot.message))


def _configure_console_encoding() -> None:
    if os.name != "nt":
        return
    output_is_console = sys.stdout.isatty()
    input_is_console = sys.stdin.isatty()
    encoding = "utf-8"

    if output_is_console or input_is_console:
        _set_console_layout()
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

        LF_FACESIZE = 32
        TMPF_TRUETYPE = 0x04
        FF_DONTCARE = 0x00
        FW_NORMAL = 400
        STD_OUTPUT_HANDLE = -11
        STD_ERROR_HANDLE = -12

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
                ("FaceName", wintypes.WCHAR * LF_FACESIZE),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE
        kernel32.GetCurrentConsoleFontEx.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(ConsoleFontInfoEx)]
        kernel32.GetCurrentConsoleFontEx.restype = wintypes.BOOL
        kernel32.SetCurrentConsoleFontEx.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(ConsoleFontInfoEx)]
        kernel32.SetCurrentConsoleFontEx.restype = wintypes.BOOL

        for std_handle in (STD_OUTPUT_HANDLE, STD_ERROR_HANDLE):
            handle = kernel32.GetStdHandle(std_handle)
            if not handle or handle == wintypes.HANDLE(-1).value:
                continue
            info = ConsoleFontInfoEx()
            info.cbSize = ctypes.sizeof(ConsoleFontInfoEx)
            if not kernel32.GetCurrentConsoleFontEx(handle, False, ctypes.byref(info)):
                continue
            info.nFont = 0
            info.dwFontSize.X = 0
            info.dwFontSize.Y = max(info.dwFontSize.Y, 16)
            info.FontFamily = FF_DONTCARE | TMPF_TRUETYPE
            info.FontWeight = FW_NORMAL
            info.FaceName = "Consolas"
            kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(info))
    except Exception:
        pass


def _set_console_layout() -> None:
    if os.name != "nt" or not sys.stdout.isatty():
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW("Valo Picker")
    except Exception:
        pass
    try:
        subprocess.run(
            ["mode.com", "con:", "cols=107", "lines=70"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass


def _reconfigure_stream(stream, encoding: str) -> None:
    try:
        stream.reconfigure(encoding=encoding, errors="replace")
    except Exception:
        pass


def run_live_first(settings: AppSettings, debug_logger: SafeDebugLogger | None = None) -> None:
    snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile, settings.language)
    last_render_signature = None
    force_render = True
    while True:
        render_signature = _live_render_signature(snapshot)
        rendered_now = False
        if force_render or render_signature != last_render_signature:
            clear_terminal()
            print(render_live_snapshot(snapshot, settings.language))
            print("\n" + t(settings.language, "live_refresh", seconds=settings.refresh_seconds))
            print(t(settings.language, "live_profile", profile=_profile_label(settings.profile, settings.language)))
            if debug_logger:
                print(t(settings.language, "status_debug_log", path=debug_logger.path))
            last_render_signature = render_signature
            force_render = False
            rendered_now = True
        choice = _read_menu_choice(settings.refresh_seconds, settings.language, show_prompt=rendered_now)
        if choice is None:
            return
        if choice == "0":
            return
        if choice == "3":
            run_interactive(settings.profile, settings.language)
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile, settings.language)
            force_render = True
            continue
        if choice == "4":
            settings = _settings_menu(settings)
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile, settings.language)
            force_render = True
            continue
        if choice == "2":
            clear_terminal()
            print(render_agent_list(settings.language))
            input("\n" + t(settings.language, "settings_return"))
            force_render = True
            continue
        if choice == "1":
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile, settings.language)
            force_render = True
            continue
        if choice == "":
            snapshot = ValorantApiService.read_live_snapshot(debug_logger, settings.profile, settings.language)
            continue
        print(t(settings.language, "menu_unknown"))
        try:
            input(t(settings.language, "menu_continue"))
        except EOFError:
            return
        force_render = True


def _live_render_signature(snapshot: LivePregameSnapshot) -> tuple:
    normalized = snapshot.normalized_match
    recommendation = snapshot.recommendation
    team = recommendation.team if recommendation else (normalized.team if normalized else ())
    team_signature = tuple((slot.player_name, slot.agent_name, slot.state.value, slot.is_self) for slot in team)
    best_signature = recommendation.best.agent.name if recommendation else None
    map_signature = normalized.map_info.name if normalized and normalized.map_info else snapshot.map_name
    warning_signature = tuple((issue.kind.value, tuple(sorted(issue.params.items()))) for issue in normalized.warnings) if normalized else ()
    error_signature = tuple((issue.kind.value, tuple(sorted(issue.params.items()))) for issue in normalized.errors) if normalized else ()
    return (
        snapshot.status.value,
        snapshot.message,
        map_signature,
        snapshot.mode,
        snapshot.game_state,
        snapshot.match_id,
        snapshot.region,
        snapshot.shard,
        team_signature,
        best_signature,
        warning_signature,
        error_signature,
    )


def run_interactive(default_profile: UserProfile | None = None, language: str = "en") -> bool:
    print_header(language)
    print(t(language, "manual_intro"))
    print(t(language, "manual_back_hint"))
    print(t(language, "manual_maps", maps=", ".join(sorted(MAPS))))
    try:
        map_name = _ask_map(language)
        team = _ask_team(language)
        profile = _ask_profile(default_profile, language)
    except ManualBackToMenu:
        print("\n" + t(language, "manual_back"))
        return False
    print()
    print_recommendation(recommend(team, MAPS[map_name], profile, language), language)
    _pause_after_manual_result(language)
    return True


def sample_recommendation(language: str = "en"):
    team = (
        TeamSlot(t(language, "manual_player", index=1), "Jett", SelectionState.LOCKED),
        TeamSlot(t(language, "manual_player", index=2), "Reyna", SelectionState.SELECTED),
        TeamSlot(t(language, "manual_player", index=3), "Killjoy", SelectionState.LOCKED),
        TeamSlot(t(language, "manual_player", index=4), "Sova", SelectionState.LOCKED),
        TeamSlot(t(language, "manual_self"), None, SelectionState.NONE, is_self=True),
    )
    profile = UserProfile(preferred_styles=frozenset({"controller", "solo_queue"}))
    return recommend(team, MAPS["Ascent"], profile, language)


def print_recommendation(result, language: str = "en") -> None:
    print_header(language)
    print(t(language, "snapshot_map", map=result.map_info.name))
    print(t(language, "render_team"))
    for slot in result.team:
        agent = slot.agent_name or t(language, "state_none")
        state = _state_label(slot.state, language)
        role = AGENTS[slot.agent_name].role.value if slot.agent_name in AGENTS else "-"
        print(f"- {slot.player_name}: {agent} - {state} - {role}")

    print()
    if result.best_role_to_fill:
        print(t(language, "render_fill_role", role=result.best_role_to_fill.value).strip())
    print(t(language, "render_problems"))
    if result.analysis.problems:
        problems = (format_composition_problem(problem, language) for problem in result.analysis.problems[:6])
        print(indent("\n".join(f"- {problem}" for problem in problems), "  "))
    else:
        print(t(language, "render_no_problems"))

    best = result.best
    print()
    print(t(language, "render_best_pick", agent=best.agent.name, role=best.agent.role.value).strip())
    print(t(language, "render_why"))
    print(indent("\n".join(f"- {reason}" for reason in best.reasons[:6]), "  "))
    if best.warnings:
        print(t(language, "render_watch"))
        print(indent("\n".join(f"- {warning}" for warning in best.warnings[:3]), "  "))

    print()
    print(t(language, "render_alternatives_title"))
    for index, candidate in enumerate(result.alternatives, start=1):
        first_reason = candidate.reasons[0] if candidate.reasons else candidate.agent.description
        print(f"{index}. {candidate.agent.name} ({candidate.agent.role.value}) - {first_reason}")

    print()
    print(t(language, "render_score", before=result.analysis.score, after=best.team_score_after_pick).strip())
    if result.warning:
        print(t(language, "render_warning", warning=result.warning))
    print(t(language, "render_advice") + f" {result.advice}")


def _ask_map(language: str) -> str:
    while True:
        raw = input(t(language, "manual_map_prompt")).strip()
        _raise_manual_back(raw)
        match = _find_key(raw, MAPS)
        if match:
            return match
        print(t(language, "manual_unknown_map"))


def _ask_team(language: str) -> tuple[TeamSlot, ...]:
    team: list[TeamSlot] = []
    print()
    print(t(language, "manual_team_hint"))
    print(t(language, "manual_state_hint"))
    for index in range(1, 6):
        is_self = index == 5
        player = t(language, "manual_self") if is_self else t(language, "manual_player", index=index)
        agent_name = _ask_agent(player, language)
        state = SelectionState.NONE
        if agent_name:
            state = _ask_state(player, language)
        team.append(TeamSlot(player, agent_name, state, is_self=is_self))
    return tuple(team)


def _ask_agent(player: str, language: str) -> str | None:
    while True:
        raw = input(t(language, "manual_agent_prompt", player=player)).strip()
        _raise_manual_back(raw)
        if not raw:
            return None
        match = _find_key(raw, AGENTS)
        if match:
            return match
        print(t(language, "manual_unknown_agent"))


def _ask_state(player: str, language: str) -> SelectionState:
    raw = input(t(language, "manual_state_prompt", player=player)).strip().lower()
    _raise_manual_back(raw)
    if raw == "l":
        return SelectionState.LOCKED
    if raw == "s":
        return SelectionState.SELECTED
    return SelectionState.NONE


def _ask_profile(default_profile: UserProfile | None = None, language: str = "en") -> UserProfile:
    print()
    print(t(language, "manual_profile_title"))
    for key in STYLE_OPTIONS:
        print(f"{key}. {t(language, f'profile_{key}')}")
    if default_profile is not None:
        print(t(language, "manual_saved_profile", profile=_profile_label(default_profile, language)))
        print(t(language, "manual_profile_hint"))
    raw_styles = input(t(language, "manual_profile_prompt")).strip()
    _raise_manual_back(raw_styles)
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


def _raise_manual_back(raw: str) -> None:
    if raw.strip().lstrip("\ufeff").casefold() in {"0", "q", "quit", "menu"}:
        raise ManualBackToMenu


def _settings_menu(settings: AppSettings) -> AppSettings:
    language = settings.language
    clear_terminal()
    print_header(language)
    print(t(language, "settings_title"))
    print(t(language, "settings_file", path=default_settings_path()))
    print()
    print(t(language, "settings_refresh", seconds=settings.refresh_seconds))
    print(t(language, "settings_start_mode", mode=_start_mode_label(settings.default_start_mode)))
    print(t(language, "settings_profile", profile=_profile_label(settings.profile, language)))
    print(t(language, "settings_language", lang_label=_language_label(settings.language)))
    print()
    print(t(language, "settings_hint"))

    raw_refresh = input(t(language, "settings_new_refresh")).strip().replace(",", ".")
    if raw_refresh:
        try:
            settings = with_refresh(settings, float(raw_refresh))
        except ValueError:
            print(t(language, "settings_bad_refresh"))

    print()
    print(t(language, "settings_start_mode_title"))
    print("1. Live")
    print("2. Manual")
    print("3. Status")
    raw_mode = input(t(language, "settings_choice")).strip()
    mode_by_choice = {"1": "live", "2": "manual", "3": "status"}
    if raw_mode in mode_by_choice:
        settings = with_start_mode(settings, mode_by_choice[raw_mode])

    print()
    print(t(language, "settings_language_title"))
    print("1. English")
    print("2. Polski")
    raw_language = input(t(language, "settings_choice")).strip()
    if raw_language.casefold() in {"1", "en", "english"}:
        settings = with_language(settings, "en")
    elif raw_language.casefold() in {"2", "pl", "polski"}:
        settings = with_language(settings, "pl")
    language = settings.language

    profile = settings.profile
    print()
    print(t(language, "manual_profile_title"))
    for key in STYLE_OPTIONS:
        print(f"{key}. {t(language, f'profile_{key}')}")
    print(t(language, "settings_profile_current", profile=_profile_label(profile, language)))
    print(t(language, "settings_profile_hint"))

    raw_profile = input(t(language, "settings_profile_prompt")).strip()
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
        print("\n" + t(language, "settings_language_saved"))
    except OSError as exc:
        print("\n" + t(language, "settings_language_error", error=exc))
    input(t(language, "settings_return"))
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


def _language_label(language: str) -> str:
    return "Polski" if language == "pl" else "English"


def _profile_label(profile: UserProfile, language: str = "en") -> str:
    labels = [
        t(language, key)
        for key, (style, _label) in STYLE_OPTIONS.items()
        if style != "beginner" and style in profile.preferred_styles
    ]
    if profile.beginner_mode:
        labels.append(t(language, "profile_8"))
    return ", ".join(labels) if labels else t(language, "profile_none")


def _player_label(slot: TeamSlot, language: str = "en") -> str:
    if slot.is_self and slot.player_name == "You":
        return t(language, "manual_self")
    match = re.fullmatch(r"Player (\d+)", slot.player_name)
    if match:
        return t(language, "manual_player", index=int(match.group(1)))
    return slot.player_name


def _read_menu_choice(timeout_seconds: float, language: str = "en", show_prompt: bool = True) -> str | None:
    if not sys.stdin.isatty():
        try:
            return input(t(language, "menu_choice")).strip().lstrip("\ufeff")
        except EOFError:
            return None
    if os.name == "nt":
        return _read_windows_choice(timeout_seconds, language, show_prompt)
    try:
        import select

        if show_prompt:
            print(t(language, "menu_choice"), end="", flush=True)
        readable, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if readable:
            return sys.stdin.readline().strip().lstrip("\ufeff")
        if show_prompt:
            print()
        return ""
    except Exception:
        try:
            return input(t(language, "menu_choice")).strip().lstrip("\ufeff")
        except EOFError:
            return None


def _pause_after_manual_result(language: str = "en") -> None:
    try:
        input("\n" + t(language, "manual_pause"))
    except EOFError:
        return


def _read_windows_choice(timeout_seconds: float, language: str = "en", show_prompt: bool = True) -> str:
    import msvcrt

    if show_prompt:
        print(t(language, "menu_choice"), end="", flush=True)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            char = msvcrt.getwch()
            if char in {"\r", "\n"}:
                if show_prompt:
                    print()
                return ""
            if show_prompt:
                print(char)
            return char.strip().lstrip("\ufeff")
        time.sleep(0.05)
    if show_prompt:
        print()
    return ""


def _mask_id(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _state_label(state: SelectionState, language: str = "en") -> str:
    if state == SelectionState.LOCKED:
        return t(language, "state_locked")
    if state == SelectionState.SELECTED:
        return t(language, "state_selected")
    return t(language, "state_none")


def print_header(language: str = "en") -> None:
    print("=" * 58)
    print(t(language, "app_title"))
    print("=" * 58)
