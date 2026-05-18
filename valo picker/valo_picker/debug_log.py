from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from .models import LivePregameSnapshot


DEFAULT_DEBUG_LOG_PATH = Path("logs") / "valo_picker_debug.log"
UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


@dataclass
class SafeDebugLogger:
    path: Path = DEFAULT_DEBUG_LOG_PATH
    events: list[dict[str, Any]] = field(default_factory=list)

    def log(self, event: str, **fields: Any) -> None:
        safe_fields = {key: _safe_value(value) for key, value in fields.items()}
        safe_fields["event"] = event
        safe_fields["time"] = datetime.now().isoformat(timespec="seconds")
        self.events.append(safe_fields)
        self._write_line(safe_fields)

    def log_snapshot(self, snapshot: LivePregameSnapshot) -> None:
        warnings: tuple[str, ...] = ()
        errors: tuple[str, ...] = ()
        map_name = snapshot.map_name
        team_size = 0
        if snapshot.normalized_match is not None:
            warnings = snapshot.normalized_match.warnings
            errors = snapshot.normalized_match.errors
            team_size = len(snapshot.normalized_match.team)
            if snapshot.normalized_match.map_info is not None:
                map_name = snapshot.normalized_match.map_info.name
        self.log(
            "snapshot",
            status=snapshot.status.value,
            match_id=_short_id(snapshot.match_id),
            party_id=_short_id(snapshot.party_id),
            map=map_name,
            team_size=team_size,
            warnings=list(warnings),
            errors=list(errors),
            message=snapshot.message,
        )

    def _write_line(self, fields: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = " ".join(f"{key}={_format_value(value)}" for key, value in fields.items())
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _short_id(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 14:
        return value
    return f"{value[:8]}...{value[-4:]}"


def _safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return UUID_RE.sub(lambda match: _short_id(match.group(0)) or "", value)
    if isinstance(value, dict):
        return {key: _safe_value(item) for key, item in value.items() if not _unsafe_key(key)}
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    return value


def _unsafe_key(key: Any) -> bool:
    lowered = str(key).lower()
    return any(secret_word in lowered for secret_word in ("token", "authorization", "password", "secret"))


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, list | tuple):
        return "[" + ",".join(str(item).replace(" ", "_") for item in value) + "]"
    return str(value).replace("\n", " ").replace("\r", " ")
