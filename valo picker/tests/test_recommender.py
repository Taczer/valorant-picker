import unittest

from valo_picker.data.maps import MAPS
from valo_picker.models import SelectionState, TeamSlot, UserProfile
from valo_picker.recommender import advice_for_agent, recommend


class RecommendationTests(unittest.TestCase):
    def test_ascent_without_controller_recommends_controller(self):
        team = (
            TeamSlot("Gracz 1", "Jett", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Reyna", SelectionState.SELECTED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Sova", SelectionState.LOCKED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Ascent"], UserProfile(preferred_styles=frozenset({"controller"})))

        self.assertEqual(result.best.agent.name, "Omen")
        self.assertEqual(result.best.agent.role.value, "Controller")
        self.assertGreater(result.best.team_score_after_pick, result.analysis.score)
        self.assertIn("Brak controllera / smoke'ów.", result.analysis.problems)

    def test_breeze_with_smokes_still_values_wall_controller(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Sova", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Jett", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Cypher", SelectionState.LOCKED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Breeze"], UserProfile())

        self.assertEqual(result.best.agent.name, "Viper")
        self.assertIn("wall", result.best.agent.utility)
        self.assertTrue(any("drugiego controllera ze ścianą" in reason for reason in result.best.reasons))

    def test_lotus_without_initiator_prefers_execute_support(self):
        team = (
            TeamSlot("Gracz 1", "Raze", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Clove", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Lotus"], UserProfile())

        self.assertEqual(result.best.agent.role.value, "Initiator")
        self.assertIn(result.best.agent.name, {"Fade", "Gekko", "Breach", "Skye", "Tejo"})
        self.assertTrue(any("Wzmacnia obecnego duelista" in reason for reason in result.best.reasons))

    def test_ascent_with_core_utility_but_no_duelist_recommends_jett(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Sova", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Clove", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Ascent"], UserProfile())

        self.assertEqual(result.best.agent.name, "Jett")
        self.assertEqual(result.best.agent.role.value, "Duelist")
        self.assertEqual(result.best_role_to_fill.value, "Duelist")
        self.assertIn("Brak duelista/entry do otwierania site'u.", result.analysis.problems)

    def test_bind_with_core_utility_but_no_duelist_recommends_raze(self):
        team = (
            TeamSlot("Gracz 1", "Brimstone", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Skye", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Cypher", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Gekko", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Bind"], UserProfile())

        self.assertEqual(result.best.agent.name, "Raze")
        self.assertEqual(result.best.agent.role.value, "Duelist")
        self.assertEqual(result.best_role_to_fill.value, "Duelist")

    def test_agent_map_advice_contains_pro_tips(self):
        advice = advice_for_agent("Jett", MAPS["Ascent"])

        self.assertIn("Pro tipy:", advice)
        self.assertIn("dashuj za smoke", advice)
        self.assertIn("Ascent", advice)


if __name__ == "__main__":
    unittest.main()
