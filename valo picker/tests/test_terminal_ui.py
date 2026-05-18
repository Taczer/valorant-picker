import unittest

from valo_picker.data.agents import AGENTS
from valo_picker.data.maps import MAPS
from valo_picker.models import (
    LivePregameSnapshot,
    LiveStatus,
    PreGameNormalizationResult,
    SelectionState,
    TeamSlot,
    UserProfile,
)
from valo_picker.recommender import recommend
from valo_picker.terminal_ui import render_agent_list, render_live_snapshot, render_recommendation


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


class TerminalUiTests(unittest.TestCase):
    def test_sample_recommendation_renders_cmd_style_screen(self):
        output = render_recommendation(sample_recommendation())

        self.assertIn("PRE-GAME (AGENT SELECT)", output)
        self.assertIn("Map: Ascent", output)
        self.assertIn("Your Team:", output)
        self.assertIn("[Jett", output)
        self.assertIn("Best Pick: Omen", output)
        self.assertIn("---- Menu ----", output)

    def test_empty_and_unknown_agent_labels_are_distinct(self):
        normalized = PreGameNormalizationResult(
            map_info=MAPS["Ascent"],
            team=(
                TeamSlot("Gracz 1", None, SelectionState.SELECTED),
                TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
            ),
            warnings=(),
            errors=(),
            match_id="match-1",
            map_id=MAPS["Ascent"].map_id,
        )
        snapshot = LivePregameSnapshot(
            status=LiveStatus.AGENT_SELECT,
            message="Agent Select lobby detected.",
            normalized_match=normalized,
        )

        output = render_live_snapshot(snapshot)

        self.assertIn("[Unknown", output)
        self.assertIn("[brak wyboru", output)

    def test_menu_does_not_offer_agent_selection_or_locking(self):
        output = render_recommendation(sample_recommendation())

        self.assertNotIn("Select Agent without locking", output)
        self.assertNotIn("Lock Character", output)
        self.assertNotIn("lock agent", output.casefold())

    def test_agent_list_renders_known_agents(self):
        output = render_agent_list()

        self.assertIn("ALL AGENTS", output)
        self.assertIn(f"[{'Omen':<12}]", output)
        self.assertIn(AGENTS["Omen"].role.value, output)

    def test_in_game_snapshot_renders_current_game_status(self):
        snapshot = LivePregameSnapshot(
            status=LiveStatus.IN_GAME,
            message="Current game detected.",
            map_name="Ascent",
            mode="Bomb/BombGameMode.BombGameMode_C",
            game_state="IN_PROGRESS",
            match_id="core-match-1",
            normalized_match=PreGameNormalizationResult(
                map_info=MAPS["Ascent"],
                team=(TeamSlot("Taczer#EUW", "Omen", SelectionState.LOCKED, is_self=True),),
                warnings=(),
                errors=(),
                match_id="core-match-1",
                map_id=MAPS["Ascent"].map_id,
            ),
        )

        output = render_live_snapshot(snapshot)

        self.assertIn("CURRENT GAME", output)
        self.assertIn("Map: Ascent", output)
        self.assertIn("State: IN_PROGRESS", output)
        self.assertIn("Taczer#EUW (Omen)", output)
        self.assertIn("Current game detected.", output)
        self.assertIn("Your Agent Advice:", output)
        self.assertIn("Pro tipy:", output)
        self.assertIn("Graj blisko teamu", output)


if __name__ == "__main__":
    unittest.main()
