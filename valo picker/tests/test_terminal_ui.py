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
from valo_picker.i18n import t


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


def sample_polish_recommendation():
    team = (
        TeamSlot("Gracz 1", "Jett", SelectionState.LOCKED),
        TeamSlot("Gracz 2", "Reyna", SelectionState.SELECTED),
        TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
        TeamSlot("Gracz 4", "Sova", SelectionState.LOCKED),
        TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
    )
    profile = UserProfile(preferred_styles=frozenset({"controller", "solo_queue"}))
    return recommend(team, MAPS["Ascent"], profile, "pl")


class TerminalUiTests(unittest.TestCase):
    def test_sample_recommendation_renders_cmd_style_screen(self):
        output = render_recommendation(sample_recommendation())

        self.assertIn("PRE-GAME (AGENT SELECT)", output)
        self.assertIn("Map: Ascent", output)
        self.assertIn("Your Team:", output)
        self.assertIn("[Jett", output)
        self.assertIn("Best Pick: Omen", output)
        self.assertIn("---- Menu ----", output)

    def test_polish_recommendation_renders_polish_labels(self):
        output = render_recommendation(sample_polish_recommendation(), "pl")

        self.assertIn("Rekomendacja:", output)
        self.assertIn("Najlepszy pick: Omen", output)
        self.assertIn("Problemy:", output)
        self.assertIn("zablokowany/poziom ?", output)
        self.assertIn("zaznaczony/poziom ?", output)
        self.assertNotIn("locked/Lvl ?", output)
        self.assertNotIn("selected/Lvl ?", output)

    def test_polish_live_snapshot_localizes_generated_player_labels(self):
        normalized = PreGameNormalizationResult(
            map_info=MAPS["Ascent"],
            team=(
                TeamSlot("Player 1", "Jett", SelectionState.LOCKED),
                TeamSlot("You", None, SelectionState.NONE, is_self=True),
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

        output = render_live_snapshot(snapshot, "pl")

        self.assertIn("Gracz 1", output)
        self.assertIn("Ty", output)
        self.assertNotIn("Player 1", output)
        self.assertNotIn("You", output)

    def test_english_recommendation_does_not_mix_common_polish_labels(self):
        output = render_recommendation(sample_recommendation())

        self.assertNotIn("Brak controllera", output)
        self.assertNotIn("Dlaczego:", output)
        self.assertNotIn("Porada:", output)

    def test_polish_no_client_snapshot_does_not_use_english_live_labels(self):
        snapshot = LivePregameSnapshot(
            status=LiveStatus.NO_CLIENT,
            message=t("pl", "local_valorant_missing"),
            valorant_running=False,
            lockfile_found=True,
        )

        output = render_live_snapshot(snapshot, "pl")

        self.assertIn("Nie wykryto procesu Valoranta", output)
        self.assertIn("Mapa: Nieznana", output)
        self.assertIn("1. Odswiez teraz", output)
        self.assertIn("2. Lista agentow", output)
        self.assertIn("3. Tryb reczny", output)
        self.assertIn("4. Ustawienia", output)
        self.assertIn("0. Wyjscie", output)
        self.assertNotIn("Valorant process not detected", output)
        self.assertNotIn("Map: Unknown", output)
        self.assertNotIn("Refresh Now", output)
        self.assertNotIn("List all agents", output)
        self.assertNotIn("Manual Mode", output)
        self.assertNotIn("Settings", output)

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
        self.assertIn("[no pick", output)

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

        output = render_live_snapshot(snapshot, "pl")

        self.assertIn("AKTYWNA GRA", output)
        self.assertIn("Mapa: Ascent", output)
        self.assertIn("Stan: IN_PROGRESS", output)
        self.assertIn("Taczer#EUW (Omen)", output)
        self.assertIn("Current game detected.", output)
        self.assertIn("Porada dla Twojego agenta:", output)
        self.assertIn("Pro tipy:", output)
        self.assertIn("Graj blisko teamu", output)


if __name__ == "__main__":
    unittest.main()
