import unittest

from valo_picker.data.agents import AGENTS
from valo_picker.data.maps import MAPS
from valo_picker.models import SelectionState
from valo_picker.normalizer import normalize_coregame_match, normalize_pregame_match, team_from_pregame_match


SELF_PUUID = "self-puuid"


def pregame_payload(**overrides):
    payload = {
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
                    "Subject": SELF_PUUID,
                    "CharacterID": "",
                    "CharacterSelectionState": "",
                },
            ]
        },
    }
    payload.update(overrides)
    return payload


class PreGameNormalizerTests(unittest.TestCase):
    def test_normalizes_valid_ascent_payload(self):
        result = normalize_pregame_match(pregame_payload(), self_puuid=SELF_PUUID)

        self.assertEqual(result.match_id, "pregame-match-1")
        self.assertEqual(result.map_id, MAPS["Ascent"].map_id)
        self.assertEqual(result.map_info, MAPS["Ascent"])
        self.assertEqual(result.errors, ())
        self.assertEqual(result.warnings, ())
        self.assertEqual(
            [(slot.player_name, slot.agent_name, slot.state, slot.is_self) for slot in result.team],
            [
                ("Gracz 1", "Jett", SelectionState.LOCKED, False),
                ("Gracz 2", "Reyna", SelectionState.SELECTED, False),
                ("Gracz 3", "Killjoy", SelectionState.LOCKED, False),
                ("Gracz 4", "Sova", SelectionState.LOCKED, False),
                ("Ty", None, SelectionState.NONE, True),
            ],
        )

    def test_existing_team_helper_uses_same_mapping(self):
        team = team_from_pregame_match(pregame_payload(), self_puuid=SELF_PUUID)

        self.assertEqual(team[0].agent_name, "Jett")
        self.assertEqual(team[1].state, SelectionState.SELECTED)
        self.assertTrue(team[4].is_self)

    def test_unknown_map_id_returns_warning(self):
        result = normalize_pregame_match(pregame_payload(MapID="/Game/Maps/Unknown/Unknown"))

        self.assertIsNone(result.map_info)
        self.assertIn("Nieznany MapID: /Game/Maps/Unknown/Unknown", result.warnings)
        self.assertEqual(result.errors, ())

    def test_missing_map_id_returns_error(self):
        payload = pregame_payload()
        payload.pop("MapID")

        result = normalize_pregame_match(payload)

        self.assertIsNone(result.map_info)
        self.assertIn("Brak MapID w danych pre-game.", result.errors)

    def test_unknown_character_id_returns_slot_without_agent_and_warning(self):
        payload = pregame_payload()
        payload["AllyTeam"]["Players"][0]["CharacterID"] = "unknown-character-id"

        result = normalize_pregame_match(payload)

        self.assertIsNone(result.team[0].agent_name)
        self.assertIn("Gracz 1: nieznany CharacterID: unknown-character-id", result.warnings)
        self.assertEqual(result.errors, ())

    def test_unknown_selection_state_returns_none_and_warning(self):
        payload = pregame_payload()
        payload["AllyTeam"]["Players"][1]["CharacterSelectionState"] = "hovered"

        result = normalize_pregame_match(payload)

        self.assertEqual(result.team[1].state, SelectionState.NONE)
        self.assertIn("Gracz 2: nieznany CharacterSelectionState: hovered", result.warnings)

    def test_missing_ally_team_players_returns_error(self):
        result = normalize_pregame_match(pregame_payload(AllyTeam={}))

        self.assertEqual(result.team, ())
        self.assertIn("Brak AllyTeam.Players w danych pre-game.", result.errors)

    def test_missing_ally_team_returns_error(self):
        payload = pregame_payload()
        payload.pop("AllyTeam")

        result = normalize_pregame_match(payload)

        self.assertEqual(result.team, ())
        self.assertIn("Brak AllyTeam w danych pre-game.", result.errors)

    def test_coregame_match_maps_ally_team_names_and_agents(self):
        payload = {
            "MatchID": "core-match-1",
            "MapID": "/Game/Maps/Infinity/Infinity",
            "Players": [
                {
                    "Subject": "ally-1",
                    "CharacterID": AGENTS["Astra"].character_id,
                    "TeamID": "Blue",
                },
                {
                    "Subject": SELF_PUUID,
                    "CharacterID": AGENTS["Jett"].character_id,
                    "TeamID": "Blue",
                },
                {
                    "Subject": "enemy-1",
                    "CharacterID": AGENTS["Sova"].character_id,
                    "TeamID": "Red",
                },
            ],
        }

        result = normalize_coregame_match(
            payload,
            self_puuid=SELF_PUUID,
            player_names={"ally-1": "Ally#EUW", SELF_PUUID: "Taczer#EUW"},
        )

        self.assertEqual(result.match_id, "core-match-1")
        self.assertEqual(result.map_info.name, "Abyss")
        self.assertEqual(
            tuple((slot.player_name, slot.agent_name) for slot in result.team),
            (("Ally#EUW", "Astra"), ("Taczer#EUW", "Jett")),
        )
        self.assertTrue(result.team[1].is_self)


if __name__ == "__main__":
    unittest.main()
