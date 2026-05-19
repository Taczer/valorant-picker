from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_REFRESH_SECONDS = 5.0
DEFAULT_START_MODE = "live"
START_MODES = frozenset({"live", "manual", "status"})


@dataclass(frozen=True)
class AppSettings:
    refresh_seconds: float = DEFAULT_REFRESH_SECONDS
    default_start_mode: str = DEFAULT_START_MODE


def default_settings_path() -> Path:
    if os.name == "nt":
        root = os.environ.get("APPDATA")
        if root:
            return Path(root) / "ValoPicker" / "settings.json"
    return Path.home() / ".valo_picker" / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    path = path or default_settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppSettings()
    if not isinstance(raw, dict):
        return AppSettings()
    return settings_from_dict(raw)


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    path = path or default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "refresh_seconds": settings.refresh_seconds,
        "default_start_mode": settings.default_start_mode,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def settings_from_dict(raw: dict[str, Any]) -> AppSettings:
    refresh = _coerce_refresh(raw.get("refresh_seconds", DEFAULT_REFRESH_SECONDS))
    start_mode = raw.get("default_start_mode", DEFAULT_START_MODE)
    if not isinstance(start_mode, str) or start_mode not in START_MODES:
        start_mode = DEFAULT_START_MODE
    return AppSettings(refresh_seconds=refresh, default_start_mode=start_mode)


def with_refresh(settings: AppSettings, refresh_seconds: float) -> AppSettings:
    return AppSettings(
        refresh_seconds=_coerce_refresh(refresh_seconds),
        default_start_mode=settings.default_start_mode,
    )


def with_start_mode(settings: AppSettings, start_mode: str) -> AppSettings:
    if start_mode not in START_MODES:
        start_mode = DEFAULT_START_MODE
    return AppSettings(refresh_seconds=settings.refresh_seconds, default_start_mode=start_mode)


def _coerce_refresh(value: Any) -> float:
    try:
        return max(2.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return DEFAULT_REFRESH_SECONDS
