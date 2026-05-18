from __future__ import annotations

import base64
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .debug_log import SafeDebugLogger
from .models import LivePregameSnapshot, LiveStatus
from .normalizer import normalize_coregame_match, normalize_pregame_match
from .recommender import recommend


LOCKFILE_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Riot Games" / "Riot Client" / "Config" / "lockfile"
SHOOTER_LOG_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "VALORANT" / "Saved" / "Logs" / "ShooterGame.log"
CLIENT_PLATFORM = "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
RIOT_USER_AGENT = "RiotClient/ValoPicker rso-auth (Windows;10;;Professional, x64)"
GLZ_URL_RE = re.compile(r"https://glz-([a-z0-9-]+)-1\.([a-z0-9-]+)\.a\.pvp\.net", re.IGNORECASE)
CI_SERVER_VERSION_RE = re.compile(r"CI server version:\s*(release-[^\s]+)", re.IGNORECASE)
PREGAME_MATCH_URL_RE = re.compile(r"/pregame/v1/matches/([0-9a-f-]{36})", re.IGNORECASE)
REGION_TO_SHARD = {
    "na": "na",
    "latam": "na",
    "br": "na",
    "eu": "eu",
    "eune": "eu",
    "euw": "eu",
    "ap": "ap",
    "kr": "kr",
}
REGION_ALIASES = {
    "eune": "eu",
    "euw": "eu",
}


@dataclass(frozen=True)
class RiotAuthBundle:
    access_token: str = field(repr=False)
    entitlement_token: str = field(repr=False)
    puuid: str


@dataclass(frozen=True)
class ValorantRegionContext:
    region: str
    shard: str

    @property
    def glz_base_url(self) -> str:
        return f"https://glz-{self.region}-1.{self.shard}.a.pvp.net"

    @classmethod
    def from_shooter_log(cls, path: Path = SHOOTER_LOG_PATH) -> "ValorantRegionContext | None":
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        matches = GLZ_URL_RE.findall(raw)
        if not matches:
            return None
        region, shard = matches[-1]
        return cls(region=region.lower(), shard=shard.lower())


def client_version_from_shooter_log(path: Path = SHOOTER_LOG_PATH) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    matches = CI_SERVER_VERSION_RE.findall(raw)
    if not matches:
        return None
    return matches[-1]


def pregame_match_id_from_shooter_log(path: Path = SHOOTER_LOG_PATH) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    matches = PREGAME_MATCH_URL_RE.findall(raw)
    if not matches:
        return None
    return matches[-1]


class ValorantApiHttpError(RuntimeError):
    def __init__(self, status_code: int, path: str):
        self.status_code = status_code
        self.path = path
        super().__init__(f"Riot API zwróciło HTTP {status_code}: {path}")


@dataclass(frozen=True)
class LocalClientAuth:
    name: str
    pid: str
    port: str
    password: str
    protocol: str

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://127.0.0.1:{self.port}"

    @property
    def basic_auth_header(self) -> str:
        token = base64.b64encode(f"riot:{self.password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    @classmethod
    def from_lockfile(cls, path: Path = LOCKFILE_PATH) -> "LocalClientAuth":
        raw = path.read_text(encoding="utf-8").strip()
        parts = raw.split(":")
        if len(parts) != 5:
            raise RuntimeError("Lockfile ma nieoczekiwany format.")
        return cls(*parts)


class ValorantApiService:
    """Read-only Riot/Valorant API client skeleton.

    This class intentionally contains no select/lock endpoints.
    """

    def __init__(self, auth: LocalClientAuth, debug_logger: SafeDebugLogger | None = None):
        self.auth = auth
        self.debug_logger = debug_logger
        self._ssl_context = ssl._create_unverified_context()

    @staticmethod
    def is_valorant_running() -> bool:
        try:
            import subprocess

            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-Process VALORANT-Win64-Shipping -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            return bool(output.strip())
        except Exception:
            return False

    @staticmethod
    def try_load_local_auth() -> LocalClientAuth | None:
        try:
            return LocalClientAuth.from_lockfile()
        except OSError:
            return None
        except RuntimeError:
            return None

    @staticmethod
    def shard_for_region(region: str | None) -> str | None:
        canonical = _canonical_region(region)
        if not canonical:
            return None
        return REGION_TO_SHARD.get(canonical)

    @classmethod
    def read_live_snapshot(cls, debug_logger: SafeDebugLogger | None = None) -> LivePregameSnapshot:
        valorant_running = cls.is_valorant_running()
        auth = cls.try_load_local_auth()
        if auth is None:
            snapshot = LivePregameSnapshot(
                status=LiveStatus.NO_CLIENT,
                message="Riot Client lockfile not found. Start Riot Client/Valorant or use Manual Mode.",
                valorant_running=valorant_running,
                lockfile_found=False,
            )
            if debug_logger:
                debug_logger.log("local_status", valorant_running=valorant_running, lockfile_found=False)
                debug_logger.log_snapshot(snapshot)
            return snapshot

        if not valorant_running:
            snapshot = LivePregameSnapshot(
                status=LiveStatus.NO_CLIENT,
                message="Valorant process not detected. Start Valorant or use Manual Mode.",
                valorant_running=False,
                lockfile_found=True,
            )
            if debug_logger:
                debug_logger.log("local_status", valorant_running=False, lockfile_found=True)
                debug_logger.log_snapshot(snapshot)
            return snapshot

        if debug_logger:
            debug_logger.log("local_status", valorant_running=True, lockfile_found=True, endpoint=auth.base_url)
        service = cls(auth, debug_logger)
        try:
            region_context = service.get_region_context()
            auth_bundle = service.get_auth_bundle()
            client_version = service.get_client_version()
            if not client_version:
                snapshot = LivePregameSnapshot(
                    status=LiveStatus.WAITING_FOR_AGENT_SELECT,
                    message="Valorant session found, but client version is not available yet.",
                    valorant_running=True,
                    lockfile_found=True,
                    puuid=auth_bundle.puuid,
                    region=region_context.region,
                    shard=region_context.shard,
                )
                if debug_logger:
                    debug_logger.log_snapshot(snapshot)
                return snapshot
            snapshot = service._read_remote_snapshot(region_context, client_version, auth_bundle)
            if debug_logger:
                debug_logger.log_snapshot(snapshot)
            return snapshot
        except RuntimeError as exc:
            snapshot = LivePregameSnapshot(
                status=LiveStatus.ERROR,
                message=str(exc),
                valorant_running=valorant_running,
                lockfile_found=True,
            )
            if debug_logger:
                debug_logger.log("runtime_error", error=str(exc))
                debug_logger.log_snapshot(snapshot)
            return snapshot

    @classmethod
    def snapshot_from_pregame_payload(
        cls,
        payload: dict[str, Any],
        self_puuid: str | None = None,
        party_id: str | None = None,
        region: str | None = None,
        shard: str | None = None,
        client_version: str | None = None,
    ) -> LivePregameSnapshot:
        normalized = normalize_pregame_match(payload, self_puuid)
        recommendation = None
        status = LiveStatus.WAITING_FOR_AGENT_SELECT
        message = "Pre-game data received, but recommendation cannot be built yet."
        if normalized.map_info is not None and normalized.team:
            recommendation = recommend(normalized.team, normalized.map_info)
            status = LiveStatus.AGENT_SELECT
            message = "Agent Select lobby detected."
        elif normalized.errors:
            status = LiveStatus.ERROR
            message = "; ".join(normalized.errors)

        return LivePregameSnapshot(
            status=status,
            message=message,
            valorant_running=True,
            lockfile_found=True,
            puuid=self_puuid,
            party_id=party_id,
            match_id=normalized.match_id,
            region=region,
            shard=shard,
            client_version=client_version,
            normalized_match=normalized,
            recommendation=recommendation,
        )

    def local_get(self, path: str) -> dict[str, Any]:
        self._debug("request", service="local", method="GET", endpoint=path)
        request = urllib.request.Request(
            self.auth.base_url + path,
            headers={"Authorization": self.auth.basic_auth_header},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, context=self._ssl_context, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self._debug("response", service="local", method="GET", endpoint=path, http_status=getattr(response, "status", 200))
                return payload
        except urllib.error.HTTPError as exc:
            self._debug("response", service="local", method="GET", endpoint=path, http_status=exc.code)
            raise RuntimeError(f"Lokalne API zwróciło HTTP {exc.code}: {path}") from exc
        except urllib.error.URLError as exc:
            self._debug("response", service="local", method="GET", endpoint=path, http_status="url_error")
            raise RuntimeError(f"Nie można połączyć z lokalnym klientem: {exc}") from exc

    def glz_get(
        self,
        path: str,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, Any]:
        self._debug("request", service="glz", method="GET", endpoint=path)
        request = urllib.request.Request(
            region_context.glz_base_url + path,
            headers={
                "Authorization": f"Bearer {auth_bundle.access_token}",
                "X-Riot-Entitlements-JWT": auth_bundle.entitlement_token,
                "X-Riot-ClientPlatform": CLIENT_PLATFORM,
                "X-Riot-ClientVersion": client_version,
                "User-Agent": RIOT_USER_AGENT,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, context=self._ssl_context, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self._debug("response", service="glz", method="GET", endpoint=path, http_status=getattr(response, "status", 200))
                return payload
        except urllib.error.HTTPError as exc:
            self._debug("response", service="glz", method="GET", endpoint=path, http_status=exc.code)
            raise ValorantApiHttpError(exc.code, path) from exc
        except urllib.error.URLError as exc:
            self._debug("response", service="glz", method="GET", endpoint=path, http_status="url_error")
            raise RuntimeError(f"Nie można połączyć z Riot GLZ API: {exc}") from exc

    def pd_put(
        self,
        path: str,
        body: Any,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> Any:
        self._debug("request", service="pd", method="PUT", endpoint=path)
        request = urllib.request.Request(
            f"https://pd.{region_context.shard}.a.pvp.net{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {auth_bundle.access_token}",
                "X-Riot-Entitlements-JWT": auth_bundle.entitlement_token,
                "X-Riot-ClientPlatform": CLIENT_PLATFORM,
                "X-Riot-ClientVersion": client_version,
                "User-Agent": RIOT_USER_AGENT,
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(request, context=self._ssl_context, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self._debug("response", service="pd", method="PUT", endpoint=path, http_status=getattr(response, "status", 200))
                return payload
        except urllib.error.HTTPError as exc:
            self._debug("response", service="pd", method="PUT", endpoint=path, http_status=exc.code)
            raise ValorantApiHttpError(exc.code, path) from exc
        except urllib.error.URLError as exc:
            self._debug("response", service="pd", method="PUT", endpoint=path, http_status="url_error")
            raise RuntimeError(f"Nie można połączyć z Riot PD API: {exc}") from exc

    def get_region_locale(self) -> dict[str, Any]:
        return self.local_get("/riotclient/region-locale")

    def get_region_context(self) -> ValorantRegionContext:
        log_context = ValorantRegionContext.from_shooter_log()
        if log_context is not None:
            return log_context
        payload = self.get_region_locale()
        region = _canonical_region(_extract_region(payload))
        shard = self.shard_for_region(region)
        if not region or not shard:
            raise RuntimeError("Nie można ustalić regionu/shardu gracza.")
        return ValorantRegionContext(region=region, shard=shard)

    def get_entitlements_token(self) -> dict[str, Any]:
        return self.local_get("/entitlements/v1/token")

    def get_auth_bundle(self) -> RiotAuthBundle:
        payload = self.get_entitlements_token()
        access_token = payload.get("accessToken")
        entitlement_token = payload.get("token")
        puuid = payload.get("subject")
        if not isinstance(puuid, str) or not puuid:
            user_info = self.get_rso_user_info()
            puuid = _extract_puuid(user_info)
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("Brak accessToken w lokalnym endpointcie entitlements.")
        if not isinstance(entitlement_token, str) or not entitlement_token:
            raise RuntimeError("Brak entitlement token w lokalnym endpointcie entitlements.")
        if not isinstance(puuid, str) or not puuid:
            raise RuntimeError("Nie można ustalić PUUID gracza.")
        return RiotAuthBundle(access_token=access_token, entitlement_token=entitlement_token, puuid=puuid)

    def get_rso_user_info(self) -> dict[str, Any]:
        return self.local_get("/rso-auth/v1/userinfo")

    def get_account_alias(self) -> dict[str, Any]:
        return self.local_get("/player-account/aliases/v1/active")

    def get_external_sessions(self) -> dict[str, Any]:
        return self.local_get("/product-session/v1/external-sessions")

    def get_client_version(self) -> str | None:
        log_version = client_version_from_shooter_log()
        if log_version:
            return log_version

        sessions = self.get_external_sessions()
        if not isinstance(sessions, dict):
            return None
        for session in sessions.values():
            if not isinstance(session, dict):
                continue
            product_id = session.get("productId")
            version = session.get("version")
            if isinstance(product_id, str) and product_id.lower() == "valorant" and isinstance(version, str) and version and version != "0":
                return version
        for session in sessions.values():
            if not isinstance(session, dict):
                continue
            launch_config = session.get("launchConfiguration")
            if isinstance(launch_config, dict):
                arguments = launch_config.get("arguments")
                version = _client_version_from_arguments(arguments)
                if version:
                    return version
        return None

    def get_party_player(
        self,
        puuid: str,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, Any]:
        return self.glz_get(f"/parties/v1/players/{puuid}", auth_bundle, region_context, client_version)

    def get_pregame_player(
        self,
        puuid: str,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, Any]:
        return self.glz_get(f"/pregame/v1/players/{puuid}", auth_bundle, region_context, client_version)

    def get_pregame_match(
        self,
        match_id: str,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, Any]:
        return self.glz_get(f"/pregame/v1/matches/{match_id}", auth_bundle, region_context, client_version)

    def get_coregame_player(
        self,
        puuid: str,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, Any]:
        return self.glz_get(f"/core-game/v1/players/{puuid}", auth_bundle, region_context, client_version)

    def get_coregame_match(
        self,
        match_id: str,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, Any]:
        return self.glz_get(f"/core-game/v1/matches/{match_id}", auth_bundle, region_context, client_version)

    def get_player_names(
        self,
        puuids: tuple[str, ...],
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> dict[str, str]:
        if not puuids:
            return {}
        payload = self.pd_put("/name-service/v2/players", list(dict.fromkeys(puuids)), auth_bundle, region_context, client_version)
        if not isinstance(payload, list):
            return {}
        names: dict[str, str] = {}
        for player in payload:
            if not isinstance(player, dict):
                continue
            subject = _optional_str(player.get("Subject"))
            game_name = _optional_str(player.get("GameName"))
            tag_line = _optional_str(player.get("TagLine"))
            display_name = _optional_str(player.get("DisplayName"))
            if not subject:
                continue
            if game_name and tag_line:
                names[subject] = f"{game_name}#{tag_line}"
            elif display_name:
                names[subject] = display_name
        return names

    def _read_remote_snapshot(
        self,
        region_context: ValorantRegionContext,
        client_version: str,
        auth_bundle: RiotAuthBundle | None = None,
    ) -> LivePregameSnapshot:
        try:
            return self._read_remote_snapshot_with_auth(auth_bundle or self.get_auth_bundle(), region_context, client_version)
        except ValorantApiHttpError as exc:
            if exc.status_code not in {401, 403}:
                raise
            return self._read_remote_snapshot_with_auth(self.get_auth_bundle(), region_context, client_version)

    def _read_remote_snapshot_with_auth(
        self,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
    ) -> LivePregameSnapshot:
        party_id = None
        party_warning = None
        try:
            party_payload = self.get_party_player(auth_bundle.puuid, auth_bundle, region_context, client_version)
            party_id = _optional_str(party_payload.get("CurrentPartyID"))
        except ValorantApiHttpError as exc:
            if exc.status_code not in {403, 404}:
                raise
            party_warning = f"Party Player unavailable (HTTP {exc.status_code}); continuing with Pre-Game Player."

        try:
            pregame_player = self.get_pregame_player(auth_bundle.puuid, auth_bundle, region_context, client_version)
        except ValorantApiHttpError as exc:
            if exc.status_code == 403:
                fallback_match_id = pregame_match_id_from_shooter_log()
                if fallback_match_id:
                    try:
                        match_payload = self.get_pregame_match(
                            fallback_match_id,
                            auth_bundle,
                            region_context,
                            client_version,
                        )
                        return self.snapshot_from_pregame_payload(
                            match_payload,
                            self_puuid=auth_bundle.puuid,
                            party_id=party_id,
                            region=region_context.region,
                            shard=region_context.shard,
                            client_version=client_version,
                        )
                    except ValorantApiHttpError:
                        pass
                core_snapshot = self._try_coregame_snapshot(
                    auth_bundle,
                    region_context,
                    client_version,
                    party_id,
                    party_warning,
                )
                if core_snapshot is not None:
                    return core_snapshot
                message = "Pre-Game Player unavailable (HTTP 403). Waiting for pre-game lobby."
                if party_warning:
                    message = f"{message} {party_warning}"
                return LivePregameSnapshot(
                    status=LiveStatus.WAITING_FOR_AGENT_SELECT,
                    message=message,
                    valorant_running=True,
                    lockfile_found=True,
                    puuid=auth_bundle.puuid,
                    party_id=party_id,
                    region=region_context.region,
                    shard=region_context.shard,
                    client_version=client_version,
                )
            if exc.status_code == 404:
                core_snapshot = self._try_coregame_snapshot(
                    auth_bundle,
                    region_context,
                    client_version,
                    party_id,
                    party_warning,
                )
                if core_snapshot is not None:
                    return core_snapshot
                message = f"Not in Agent Select or Pre-Game Player unavailable (HTTP {exc.status_code}). Waiting for pre-game lobby."
                if party_warning:
                    message = f"{message} {party_warning}"
                return LivePregameSnapshot(
                    status=LiveStatus.WAITING_FOR_AGENT_SELECT,
                    message=message,
                    valorant_running=True,
                    lockfile_found=True,
                    puuid=auth_bundle.puuid,
                    party_id=party_id,
                    region=region_context.region,
                    shard=region_context.shard,
                    client_version=client_version,
                )
            raise

        match_id = _optional_str(pregame_player.get("MatchID"))
        if not match_id:
            core_snapshot = self._try_coregame_snapshot(
                auth_bundle,
                region_context,
                client_version,
                party_id,
                party_warning,
            )
            if core_snapshot is not None:
                return core_snapshot
            message = "Pre-Game Player response did not include MatchID."
            if party_warning:
                message = f"{message} {party_warning}"
            return LivePregameSnapshot(
                status=LiveStatus.WAITING_FOR_AGENT_SELECT,
                message=message,
                valorant_running=True,
                lockfile_found=True,
                puuid=auth_bundle.puuid,
                party_id=party_id,
                region=region_context.region,
                shard=region_context.shard,
                client_version=client_version,
            )

        match_payload = self.get_pregame_match(match_id, auth_bundle, region_context, client_version)
        snapshot = self.snapshot_from_pregame_payload(
            match_payload,
            self_puuid=auth_bundle.puuid,
            party_id=party_id,
            region=region_context.region,
            shard=region_context.shard,
            client_version=client_version,
        )
        if party_warning and snapshot.normalized_match is None:
            return snapshot
        if party_warning and snapshot.status != LiveStatus.AGENT_SELECT:
            return LivePregameSnapshot(
                status=snapshot.status,
                message=f"{snapshot.message} {party_warning}",
                valorant_running=snapshot.valorant_running,
                lockfile_found=snapshot.lockfile_found,
                puuid=snapshot.puuid,
                party_id=snapshot.party_id,
                match_id=snapshot.match_id,
                region=snapshot.region,
                shard=snapshot.shard,
                client_version=snapshot.client_version,
                normalized_match=snapshot.normalized_match,
                recommendation=snapshot.recommendation,
            )
        return snapshot

    def _try_coregame_snapshot(
        self,
        auth_bundle: RiotAuthBundle,
        region_context: ValorantRegionContext,
        client_version: str,
        party_id: str | None,
        party_warning: str | None,
    ) -> LivePregameSnapshot | None:
        try:
            coregame_player = self.get_coregame_player(auth_bundle.puuid, auth_bundle, region_context, client_version)
        except ValorantApiHttpError as exc:
            if exc.status_code in {403, 404}:
                return None
            raise

        match_id = _optional_str(coregame_player.get("MatchID"))
        if not match_id:
            return None

        match_payload = None
        try:
            match_payload = self.get_coregame_match(match_id, auth_bundle, region_context, client_version)
        except ValorantApiHttpError as exc:
            if exc.status_code not in {403, 404}:
                raise

        map_name = None
        mode = "current-game"
        game_state = "IN_GAME"
        normalized_match = None
        if isinstance(match_payload, dict):
            player_puuids = _player_puuids_from_coregame_match(match_payload)
            player_names = {}
            try:
                player_names = self.get_player_names(player_puuids, auth_bundle, region_context, client_version)
            except ValorantApiHttpError as exc:
                if exc.status_code not in {403, 404}:
                    raise
            normalized_match = normalize_coregame_match(match_payload, auth_bundle.puuid, player_names)
            if normalized_match.map_info is not None:
                map_name = normalized_match.map_info.name
            mode = _optional_str(match_payload.get("ModeID")) or _optional_str(match_payload.get("QueueID")) or mode
            game_state = _optional_str(match_payload.get("State")) or game_state

        message = "Current game detected. Recommendations are available during Agent Select."
        if party_warning:
            message = f"{message} {party_warning}"
        return LivePregameSnapshot(
            status=LiveStatus.IN_GAME,
            message=message,
            valorant_running=True,
            lockfile_found=True,
            map_name=map_name,
            mode=mode,
            game_state=game_state,
            puuid=auth_bundle.puuid,
            party_id=party_id,
            match_id=match_id,
            region=region_context.region,
            shard=region_context.shard,
            client_version=client_version,
            normalized_match=normalized_match,
        )

    def _debug(self, event: str, **fields: Any) -> None:
        if self.debug_logger is not None:
            self.debug_logger.log(event, **fields)


def _extract_region(payload: dict[str, Any]) -> str | None:
    for key in ("region", "Region", "webRegion", "WebRegion"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value.lower()
    return None


def _canonical_region(region: str | None) -> str | None:
    if not region:
        return None
    normalized = region.lower()
    return REGION_ALIASES.get(normalized, normalized)


def _extract_puuid(payload: dict[str, Any]) -> str | None:
    for key in ("sub", "subject", "puuid", "user_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _client_version_from_arguments(arguments: Any) -> str | None:
    if isinstance(arguments, str):
        parts = arguments.split()
    elif isinstance(arguments, list):
        parts = [str(part) for part in arguments]
    else:
        return None
    for index, part in enumerate(parts):
        if part in {"--client-version", "-client-version"} and index + 1 < len(parts):
            return parts[index + 1]
        for prefix in ("--client-version=", "-client-version="):
            if part.startswith(prefix):
                return part.split("=", 1)[1]
    return None


def _player_puuids_from_coregame_match(payload: dict[str, Any]) -> tuple[str, ...]:
    players = payload.get("Players")
    if not isinstance(players, list):
        return ()
    puuids = [
        subject
        for player in players
        if isinstance(player, dict)
        for subject in [_optional_str(player.get("Subject"))]
        if subject
    ]
    return tuple(dict.fromkeys(puuids))
