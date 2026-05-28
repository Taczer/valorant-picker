import base64
import json
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch

from valo_picker.data.agents import AGENTS
from valo_picker.data.maps import MAPS
from valo_picker.debug_log import SafeDebugLogger
from valo_picker.models import LiveStatus, NormalizationIssueKind, Role, UserProfile
from valo_picker.valorant_api import (
    CLIENT_PLATFORM,
    LocalClientAuth,
    RIOT_USER_AGENT,
    RiotAuthBundle,
    ValorantApiHttpError,
    ValorantApiService,
    ValorantRegionContext,
    client_version_from_shooter_log,
    pregame_match_id_from_shooter_log,
)


def pregame_payload():
    return {
        "ID": "pregame-match-1",
        "MapID": MAPS["Ascent"].map_id,
        "AllyTeam": {
            "Players": [
                {
                    "Subject": "player-1",
                    "CharacterID": AGENTS["Jett"].character_id,
                    "CharacterSelectionState": "locked",
                },
                {
                    "Subject": "player-2",
                    "CharacterID": AGENTS["Reyna"].character_id,
                    "CharacterSelectionState": "selected",
                },
                {
                    "Subject": "player-3",
                    "CharacterID": AGENTS["Killjoy"].character_id,
                    "CharacterSelectionState": "locked",
                },
                {
                    "Subject": "player-4",
                    "CharacterID": AGENTS["Sova"].character_id,
                    "CharacterSelectionState": "locked",
                },
                {
                    "Subject": "self-puuid",
                    "CharacterID": "",
                    "CharacterSelectionState": "",
                },
            ]
        },
    }


class LiveSnapshotTests(unittest.TestCase):
    def test_missing_lockfile_gives_no_client_status(self):
        with (
            patch.object(ValorantApiService, "is_valorant_running", return_value=False),
            patch.object(ValorantApiService, "try_load_local_auth", return_value=None),
        ):
            snapshot = ValorantApiService.read_live_snapshot()

        self.assertEqual(snapshot.status, LiveStatus.NO_CLIENT)
        self.assertFalse(snapshot.lockfile_found)

    def test_lockfile_without_pregame_data_waits_for_agent_select(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        with (
            patch.object(ValorantApiService, "is_valorant_running", return_value=True),
            patch.object(ValorantApiService, "try_load_local_auth", return_value=auth),
            patch.object(ValorantRegionContext, "from_shooter_log", return_value=None),
            patch.object(ValorantApiService, "get_region_locale", return_value={"region": "eu"}),
            patch.object(ValorantApiService, "get_client_version", return_value="release-test"),
            patch.object(
                ValorantApiService,
                "get_auth_bundle",
                return_value=RiotAuthBundle("access", "entitlement", "self-puuid"),
            ),
            patch.object(
                ValorantApiService,
                "get_party_player",
                return_value={"CurrentPartyID": "party-1"},
            ),
            patch.object(
                ValorantApiService,
                "get_pregame_player",
                side_effect=ValorantApiHttpError(404, "/pregame/v1/players/self-puuid"),
            ),
            patch.object(
                ValorantApiService,
                "get_coregame_player",
                side_effect=ValorantApiHttpError(404, "/core-game/v1/players/self-puuid"),
            ),
        ):
            snapshot = ValorantApiService.read_live_snapshot()

        self.assertEqual(snapshot.status, LiveStatus.WAITING_FOR_AGENT_SELECT)
        self.assertTrue(snapshot.valorant_running)
        self.assertTrue(snapshot.lockfile_found)
        self.assertEqual(snapshot.region, "eu")
        self.assertEqual(snapshot.shard, "eu")
        self.assertEqual(snapshot.party_id, "party-1")

    def test_pregame_payload_builds_agent_select_snapshot(self):
        snapshot = ValorantApiService.snapshot_from_pregame_payload(
            pregame_payload(),
            self_puuid="self-puuid",
            party_id="party-1",
            region="eu",
            shard="eu",
            client_version="release-test",
        )

        self.assertEqual(snapshot.status, LiveStatus.AGENT_SELECT)
        self.assertEqual(snapshot.puuid, "self-puuid")
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertEqual(snapshot.match_id, "pregame-match-1")
        self.assertEqual(snapshot.client_version, "release-test")
        self.assertIsNotNone(snapshot.recommendation)
        self.assertEqual(snapshot.recommendation.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", snapshot.recommendation.best.agent.utility)

    def test_pregame_payload_passes_profile_to_recommender(self):
        profile = UserProfile(preferred_styles=frozenset({"support"}), beginner_mode=True)
        recommendation = object()

        with patch("valo_picker.valorant_api.recommend", return_value=recommendation) as recommend_mock:
            snapshot = ValorantApiService.snapshot_from_pregame_payload(
                pregame_payload(),
                self_puuid="self-puuid",
                profile=profile,
            )

        self.assertEqual(snapshot.recommendation, recommendation)
        self.assertEqual(recommend_mock.call_args.args[2], profile)
        self.assertEqual(recommend_mock.call_args.args[3], "en")

    def test_bad_pregame_payload_builds_error_snapshot_without_exception(self):
        snapshot = ValorantApiService.snapshot_from_pregame_payload([], self_puuid="self-puuid")

        self.assertEqual(snapshot.status, LiveStatus.ERROR)
        self.assertIsNotNone(snapshot.normalized_match)
        self.assertEqual(snapshot.normalized_match.team, ())
        self.assertEqual(
            tuple(issue.kind for issue in snapshot.normalized_match.errors),
            (NormalizationIssueKind.BAD_PREGAME_PAYLOAD,),
        )
        self.assertIsNone(snapshot.recommendation)

    def test_shard_lookup(self):
        self.assertEqual(ValorantApiService.shard_for_region("eu"), "eu")
        self.assertEqual(ValorantApiService.shard_for_region("eune"), "eu")
        self.assertEqual(ValorantApiService.shard_for_region("euw"), "eu")
        self.assertEqual(ValorantApiService.shard_for_region("na"), "na")
        self.assertEqual(ValorantApiService.shard_for_region("br"), "na")
        self.assertEqual(ValorantApiService.shard_for_region("latam"), "na")
        self.assertEqual(ValorantApiService.shard_for_region("ap"), "ap")
        self.assertEqual(ValorantApiService.shard_for_region("kr"), "kr")

    def test_client_platform_header_decodes_to_expected_json(self):
        platform = json.loads(base64.b64decode(CLIENT_PLATFORM).decode("utf-8"))

        self.assertEqual(platform["platformType"], "PC")
        self.assertEqual(platform["platformOS"], "Windows")
        self.assertIn("platformOSVersion", platform)
        self.assertEqual(platform["platformChipset"], "Unknown")

    def test_region_context_canonicalizes_eune_to_eu(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        with (
            patch.object(ValorantRegionContext, "from_shooter_log", return_value=None),
            patch.object(service, "get_region_locale", return_value={"region": "eune"}),
        ):
            context = service.get_region_context()

        self.assertEqual(context.region, "eu")
        self.assertEqual(context.shard, "eu")
        self.assertEqual(context.glz_base_url, "https://glz-eu-1.eu.a.pvp.net")

    def test_region_context_can_be_read_from_shooter_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "ShooterGame.log"
            log_path.write_text(
                "first https://glz-na-1.na.a.pvp.net\n"
                "latest https://glz-eu-1.eu.a.pvp.net\n",
                encoding="utf-8",
            )

            context = ValorantRegionContext.from_shooter_log(log_path)

        self.assertEqual(context.region, "eu")
        self.assertEqual(context.shard, "eu")
        self.assertEqual(context.glz_base_url, "https://glz-eu-1.eu.a.pvp.net")

    def test_client_version_can_be_read_from_shooter_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "ShooterGame.log"
            log_path.write_text(
                "LogShooter: Display: CI server version: release-12.08-shipping-1-1111111\n"
                "LogShooter: Display: CI server version: release-12.09-shipping-25-4697179\n",
                encoding="utf-8",
            )

            version = client_version_from_shooter_log(log_path)

        self.assertEqual(version, "release-12.09-shipping-25-4697179")

    def test_pregame_match_id_can_be_read_from_shooter_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "ShooterGame.log"
            log_path.write_text(
                "GET https://glz-eu-1.eu.a.pvp.net/pregame/v1/matches/11111111-1111-1111-1111-111111111111\n"
                "GET https://glz-eu-1.eu.a.pvp.net/pregame/v1/matches/22222222-2222-2222-2222-222222222222\n",
                encoding="utf-8",
            )

            match_id = pregame_match_id_from_shooter_log(log_path)

        self.assertEqual(match_id, "22222222-2222-2222-2222-222222222222")

    def test_auth_bundle_extracts_tokens_and_puuid_without_printing_tokens(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        with patch.object(
            service,
            "get_entitlements_token",
            return_value={"accessToken": "access-secret", "token": "entitlement-secret", "subject": "self-puuid"},
        ):
            bundle = service.get_auth_bundle()

        self.assertEqual(bundle.puuid, "self-puuid")
        self.assertNotIn("access-secret", repr(bundle))
        self.assertNotIn("entitlement-secret", repr(bundle))

    def test_local_client_auth_parses_lockfile_content(self):
        auth = LocalClientAuth.from_lockfile_content("RiotClient:12345:54321:secret:https")

        self.assertEqual(auth.name, "RiotClient")
        self.assertEqual(auth.pid, "12345")
        self.assertEqual(auth.port, "54321")
        self.assertEqual(auth.password, "secret")
        self.assertEqual(auth.protocol, "https")
        self.assertEqual(auth.base_url, "https://127.0.0.1:54321")

    def test_local_client_auth_rejects_wrong_lockfile_field_count(self):
        with self.assertRaises(RuntimeError):
            LocalClientAuth.from_lockfile_content("RiotClient:12345")

    def test_local_client_auth_rejects_empty_lockfile_fields(self):
        with self.assertRaises(RuntimeError):
            LocalClientAuth.from_lockfile_content("RiotClient:12345::secret:https")

    def test_local_client_auth_reads_lockfile_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "lockfile"
            path.write_text("RiotClient:12345:54321:secret:https", encoding="utf-8")

            auth = LocalClientAuth.from_lockfile(path)

        self.assertEqual(auth.port, "54321")
        self.assertEqual(auth.password, "secret")

    def test_client_version_comes_from_valorant_external_session(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        with (
            patch("valo_picker.valorant_api.client_version_from_shooter_log", return_value=None),
            patch.object(
                service,
                "get_external_sessions",
                return_value={
                    "riot": {"productId": "riot_client", "version": "0"},
                    "valorant": {"productId": "valorant", "version": "release-10.00-shipping-1-123"},
                },
            ),
        ):
            version = service.get_client_version()

        self.assertEqual(version, "release-10.00-shipping-1-123")

    def test_client_version_can_fallback_to_launch_arguments(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        with (
            patch("valo_picker.valorant_api.client_version_from_shooter_log", return_value=None),
            patch.object(
                service,
                "get_external_sessions",
                return_value={
                    "valorant": {
                        "productId": "VALORANT",
                        "version": "0",
                        "launchConfiguration": {
                            "arguments": ["--client-version", "release-10.01-shipping-2-456"],
                        },
                    },
                },
            ),
        ):
            version = service.get_client_version()

        self.assertEqual(version, "release-10.01-shipping-2-456")

    def test_glz_get_builds_read_only_request_headers(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access-secret", "entitlement-secret", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok": true}'

        def fake_urlopen(request, context=None, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            payload = service.glz_get("/pregame/v1/players/self-puuid", bundle, context, "release-test")

        request = captured["request"]
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, "https://glz-eu-1.eu.a.pvp.net/pregame/v1/players/self-puuid")
        self.assertEqual(request.get_header("Authorization"), "Bearer access-secret")
        self.assertEqual(request.get_header("X-riot-entitlements-jwt"), "entitlement-secret")
        self.assertEqual(request.get_header("X-riot-clientversion"), "release-test")
        self.assertIsNotNone(request.get_header("X-riot-clientplatform"))
        self.assertEqual(request.get_header("User-agent"), RIOT_USER_AGENT)
        self.assertEqual(captured["timeout"], 5)

    def test_local_get_wraps_invalid_json_with_endpoint_context(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"<html>not json</html>"

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaises(RuntimeError) as raised:
                service.local_get("/riotclient/region-locale")

        self.assertIn("invalid JSON", str(raised.exception))
        self.assertIn("/riotclient/region-locale", str(raised.exception))

    def test_local_get_wraps_http_error_with_endpoint_context(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        error = urllib.error.HTTPError(
            url=auth.base_url + "/riotclient/region-locale",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )

        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                service.local_get("/riotclient/region-locale")

        self.assertIn("HTTP 503", str(raised.exception))
        self.assertIn("/riotclient/region-locale", str(raised.exception))

    def test_local_get_wraps_url_error_with_connection_context(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            with self.assertRaises(RuntimeError) as raised:
                service.local_get("/riotclient/region-locale")

        self.assertIn("Cannot connect to local client", str(raised.exception))
        self.assertIn("connection refused", str(raised.exception))

    def test_glz_get_wraps_invalid_json_with_endpoint_context(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access-secret", "entitlement-secret", "self-puuid")
        context = ValorantRegionContext("eu", "eu")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"<html>not json</html>"

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaises(RuntimeError) as raised:
                service.glz_get("/pregame/v1/players/self-puuid", bundle, context, "release-test")

        self.assertIn("invalid JSON", str(raised.exception))
        self.assertIn("GLZ", str(raised.exception))
        self.assertIn("/pregame/v1/players/self-puuid", str(raised.exception))

    def test_pd_put_wraps_invalid_json_with_endpoint_context(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access-secret", "entitlement-secret", "self-puuid")
        context = ValorantRegionContext("eu", "eu")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"<html>not json</html>"

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaises(RuntimeError) as raised:
                service.pd_put("/name-service/v2/players", ["self-puuid"], bundle, context, "release-test")

        self.assertIn("invalid JSON", str(raised.exception))
        self.assertIn("PD", str(raised.exception))
        self.assertIn("/name-service/v2/players", str(raised.exception))

    def test_pd_put_wraps_http_error_with_endpoint_context(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access-secret", "entitlement-secret", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        path = "/name-service/v2/players"
        error = urllib.error.HTTPError(
            url=f"https://pd.eu.a.pvp.net{path}",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )

        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ValorantApiHttpError) as raised:
                service.pd_put(path, ["self-puuid"], bundle, context, "release-test")

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.path, path)
        self.assertIn("HTTP 403", str(raised.exception))
        self.assertIn(path, str(raised.exception))

    def test_debug_log_records_endpoint_and_status_without_tokens(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "debug.log"
            logger = SafeDebugLogger(log_path)
            auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
            service = ValorantApiService(auth, logger)
            bundle = RiotAuthBundle("access-secret", "entitlement-secret", "self-puuid")
            context = ValorantRegionContext("eu", "eu")

            class FakeResponse:
                status = 200

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return b'{"ok": true}'

            with patch("urllib.request.urlopen", return_value=FakeResponse()):
                service.glz_get("/pregame/v1/players/self-puuid", bundle, context, "release-test")

            log_text = log_path.read_text(encoding="utf-8")

        self.assertIn("endpoint=/pregame/v1/players/self-puuid", log_text)
        self.assertIn("http_status=200", log_text)
        self.assertNotIn("access-secret", log_text)
        self.assertNotIn("entitlement-secret", log_text)
        self.assertNotIn("Authorization", log_text)

    def test_debug_log_masks_uuid_values_in_endpoints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "debug.log"
            logger = SafeDebugLogger(log_path)
            logger.log("request", endpoint="/core-game/v1/matches/11111111-2222-3333-4444-555555555555")
            log_text = log_path.read_text(encoding="utf-8")

        self.assertIn("11111111...5555", log_text)
        self.assertNotIn("11111111-2222-3333-4444-555555555555", log_text)

    def test_remote_snapshot_reads_party_pregame_player_and_match(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(service, "get_pregame_player", return_value={"MatchID": "pregame-match-1"}),
            patch.object(service, "get_pregame_match", return_value=pregame_payload()),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.AGENT_SELECT)
        self.assertEqual(snapshot.puuid, "self-puuid")
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertEqual(snapshot.match_id, "pregame-match-1")
        self.assertEqual(snapshot.client_version, "release-test")
        self.assertEqual(snapshot.recommendation.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", snapshot.recommendation.best.agent.utility)

    def test_remote_snapshot_waits_when_pregame_player_404s(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(
                service,
                "get_pregame_player",
                side_effect=ValorantApiHttpError(404, "/pregame/v1/players/self-puuid"),
            ),
            patch.object(
                service,
                "get_coregame_player",
                side_effect=ValorantApiHttpError(404, "/core-game/v1/players/self-puuid"),
            ),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.WAITING_FOR_AGENT_SELECT)
        self.assertEqual(snapshot.puuid, "self-puuid")
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertEqual(snapshot.client_version, "release-test")
        self.assertIsNone(snapshot.match_id)

    def test_remote_snapshot_waits_when_pregame_player_payload_is_not_object(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(service, "get_pregame_player", return_value=[]),
            patch.object(
                service,
                "get_coregame_player",
                side_effect=ValorantApiHttpError(404, "/core-game/v1/players/self-puuid"),
            ),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.WAITING_FOR_AGENT_SELECT)
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertIsNone(snapshot.match_id)

    def test_remote_snapshot_detects_in_game_after_pregame_404(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(
                service,
                "get_pregame_player",
                side_effect=ValorantApiHttpError(404, "/pregame/v1/players/self-puuid"),
            ),
            patch.object(service, "get_coregame_player", return_value={"MatchID": "core-match-1"}),
            patch.object(
                service,
                "get_player_names",
                return_value={
                    "player-1": "AstraPlayer#EUW",
                    "self-puuid": "Taczer#EUW",
                },
            ),
            patch.object(
                service,
                "get_coregame_match",
                return_value={
                    "MatchID": "core-match-1",
                    "MapID": MAPS["Ascent"].map_id,
                    "ModeID": "Bomb/BombGameMode.BombGameMode_C",
                    "State": "IN_PROGRESS",
                    "Players": [
                        {
                            "Subject": "player-1",
                            "CharacterID": AGENTS["Astra"].character_id,
                            "TeamID": "Blue",
                        },
                        {
                            "Subject": "self-puuid",
                            "CharacterID": AGENTS["Jett"].character_id,
                            "TeamID": "Blue",
                        },
                        {
                            "Subject": "enemy-1",
                            "CharacterID": AGENTS["Sova"].character_id,
                            "TeamID": "Red",
                        },
                    ],
                },
            ),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.IN_GAME)
        self.assertEqual(snapshot.match_id, "core-match-1")
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertEqual(snapshot.map_name, "Ascent")
        self.assertEqual(snapshot.mode, "Bomb/BombGameMode.BombGameMode_C")
        self.assertEqual(snapshot.game_state, "IN_PROGRESS")
        self.assertIsNotNone(snapshot.normalized_match)
        self.assertEqual(
            tuple((slot.player_name, slot.agent_name) for slot in snapshot.normalized_match.team),
            (("AstraPlayer#EUW", "Astra"), ("Taczer#EUW", "Jett")),
        )

    def test_remote_snapshot_waits_when_coregame_player_payload_is_not_object(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(
                service,
                "get_pregame_player",
                side_effect=ValorantApiHttpError(404, "/pregame/v1/players/self-puuid"),
            ),
            patch.object(service, "get_coregame_player", return_value=[]),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.WAITING_FOR_AGENT_SELECT)
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertIsNone(snapshot.match_id)

    def test_remote_snapshot_waits_when_pregame_player_403s(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(
                service,
                "get_pregame_player",
                side_effect=ValorantApiHttpError(403, "/pregame/v1/players/self-puuid"),
            ),
            patch("valo_picker.valorant_api.pregame_match_id_from_shooter_log", return_value=None),
            patch.object(
                service,
                "get_coregame_player",
                side_effect=ValorantApiHttpError(404, "/core-game/v1/players/self-puuid"),
            ),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.WAITING_FOR_AGENT_SELECT)
        self.assertIn("HTTP 403", snapshot.message)
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertIsNone(snapshot.match_id)

    def test_remote_snapshot_falls_back_to_match_id_from_log_after_pregame_player_403(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value={"CurrentPartyID": "party-1"}),
            patch.object(
                service,
                "get_pregame_player",
                side_effect=ValorantApiHttpError(403, "/pregame/v1/players/self-puuid"),
            ),
            patch(
                "valo_picker.valorant_api.pregame_match_id_from_shooter_log",
                return_value="pregame-match-1",
            ),
            patch.object(service, "get_pregame_match", return_value=pregame_payload()),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.AGENT_SELECT)
        self.assertEqual(snapshot.party_id, "party-1")
        self.assertEqual(snapshot.match_id, "pregame-match-1")
        self.assertEqual(snapshot.recommendation.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", snapshot.recommendation.best.agent.utility)

    def test_remote_snapshot_continues_when_party_player_403s(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(
                service,
                "get_party_player",
                side_effect=ValorantApiHttpError(403, "/parties/v1/players/self-puuid"),
            ),
            patch.object(service, "get_pregame_player", return_value={"MatchID": "pregame-match-1"}),
            patch.object(service, "get_pregame_match", return_value=pregame_payload()),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.AGENT_SELECT)
        self.assertIsNone(snapshot.party_id)
        self.assertEqual(snapshot.match_id, "pregame-match-1")
        self.assertEqual(snapshot.recommendation.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", snapshot.recommendation.best.agent.utility)

    def test_remote_snapshot_continues_when_party_player_payload_is_not_object(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        bundle = RiotAuthBundle("access", "entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        with (
            patch.object(service, "get_auth_bundle", return_value=bundle),
            patch.object(service, "get_party_player", return_value=[]),
            patch.object(service, "get_pregame_player", return_value={"MatchID": "pregame-match-1"}),
            patch.object(service, "get_pregame_match", return_value=pregame_payload()),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.AGENT_SELECT)
        self.assertIsNone(snapshot.party_id)
        self.assertEqual(snapshot.match_id, "pregame-match-1")
        self.assertEqual(snapshot.recommendation.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", snapshot.recommendation.best.agent.utility)

    def test_remote_snapshot_refreshes_auth_once_after_401(self):
        auth = LocalClientAuth("RiotClient", "123", "4567", "secret", "https")
        service = ValorantApiService(auth)
        old_bundle = RiotAuthBundle("old-access", "old-entitlement", "self-puuid")
        new_bundle = RiotAuthBundle("new-access", "new-entitlement", "self-puuid")
        context = ValorantRegionContext("eu", "eu")
        calls = {"party": 0}

        def fake_party_player(puuid, bundle, region_context, client_version):
            calls["party"] += 1
            if calls["party"] == 1:
                raise ValorantApiHttpError(401, "/parties/v1/players/self-puuid")
            self.assertEqual(bundle.access_token, "new-access")
            return {"CurrentPartyID": "party-1"}

        with (
            patch.object(service, "get_auth_bundle", side_effect=[old_bundle, new_bundle]),
            patch.object(service, "get_party_player", side_effect=fake_party_player),
            patch.object(service, "get_pregame_player", return_value={"MatchID": "pregame-match-1"}),
            patch.object(service, "get_pregame_match", return_value=pregame_payload()),
        ):
            snapshot = service._read_remote_snapshot(context, "release-test")

        self.assertEqual(snapshot.status, LiveStatus.AGENT_SELECT)
        self.assertEqual(calls["party"], 2)


if __name__ == "__main__":
    unittest.main()
