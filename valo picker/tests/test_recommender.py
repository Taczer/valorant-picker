import unittest

from valo_picker.data.maps import MAPS
from valo_picker.models import SelectionState, TeamSlot, UserProfile
from valo_picker.recommender import Reason, ReasonKind, _prioritize_reasons, advice_for_agent, recommend


class RecommendationTests(unittest.TestCase):
    def test_ascent_without_controller_recommends_controller(self):
        team = (
            TeamSlot("Gracz 1", "Jett", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Reyna", SelectionState.SELECTED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Sova", SelectionState.LOCKED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Ascent"], UserProfile(preferred_styles=frozenset({"controller"})), "pl")

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

        result = recommend(team, MAPS["Breeze"], UserProfile(), "pl")

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

        result = recommend(team, MAPS["Lotus"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role.value, "Initiator")
        self.assertIn(result.best.agent.name, {"Fade", "Gekko", "Breach", "Skye", "Tejo"})
        self.assertTrue(any("Wzmacnia obecnego duelista" in reason for reason in result.best.reasons))

    def test_aggressive_profile_does_not_force_third_duelist_without_controller(self):
        team = (
            TeamSlot("Gracz 1", "Jett", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Reyna", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Sova", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )
        profile = UserProfile(preferred_styles=frozenset({"aggressive", "solo_queue"}))

        result = recommend(team, MAPS["Ascent"], profile, "pl")

        self.assertEqual(result.best.agent.role.value, "Controller")
        self.assertNotEqual(result.best.agent.role.value, "Duelist")
        self.assertEqual(result.best.reasons[0], "Team nie ma żadnego controllera, więc smoke'i są najwyższym priorytetem.")
        self.assertIn("Brak controllera / smoke'ów.", result.analysis.problems)

    def test_missing_smokes_beats_aggressive_duelist_profile(self):
        team = (
            TeamSlot("Gracz 1", "Raze", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Fade", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Skye", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )
        profile = UserProfile(preferred_styles=frozenset({"aggressive", "solo_queue"}))

        result = recommend(team, MAPS["Bind"], profile, "pl")

        self.assertEqual(result.best.agent.role.value, "Controller")
        self.assertNotEqual(result.best.agent.role.value, "Duelist")

    def test_bind_without_initiator_prefers_clear_or_flash_support(self):
        team = (
            TeamSlot("Gracz 1", "Brimstone", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Raze", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Cypher", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Clove", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Bind"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role.value, "Initiator")
        self.assertIn(result.best.agent.name, {"Fade", "Gekko", "Breach", "Skye", "Tejo"})
        self.assertTrue({"flash", "clear", "stun", "info"} & result.best.agent.utility)

    def test_abyss_with_smokes_still_prefers_wall_controller(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Sova", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Jett", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Cypher", SelectionState.LOCKED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Abyss"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role.value, "Controller")
        self.assertIn("wall", result.best.agent.utility)
        self.assertTrue(any("ścian" in reason or "wall" in reason for reason in result.best.reasons))

    def test_split_with_core_utility_but_no_duelist_prefers_raze_clear(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Skye", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Cypher", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Gekko", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Split"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.name, "Raze")
        self.assertEqual(result.best.agent.role.value, "Duelist")
        self.assertIn("clear", result.best.agent.utility)

    def test_ascent_with_core_utility_but_no_duelist_recommends_jett(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Sova", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Clove", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Ascent"], UserProfile(), "pl")

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

        result = recommend(team, MAPS["Bind"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.name, "Raze")
        self.assertEqual(result.best.agent.role.value, "Duelist")
        self.assertEqual(result.best_role_to_fill.value, "Duelist")

    def test_agent_map_advice_contains_pro_tips(self):
        advice = advice_for_agent("Jett", MAPS["Ascent"], "pl")

        self.assertIn("Pro tipy:", advice)
        self.assertIn("dashuj za smoke", advice)
        self.assertIn("Ascent", advice)

    def test_english_agent_map_advice_does_not_use_polish_strategy_content(self):
        advice = advice_for_agent("Jett", MAPS["Ascent"], "en")

        self.assertIn("Pro tips:", advice)
        self.assertIn("Attack:", advice)
        self.assertNotIn("Pro tipy:", advice)
        self.assertNotIn("dashuj", advice)
        self.assertNotIn("Obrona:", advice)

    def test_reason_kind_priority_is_independent_from_text_language(self):
        reasons = [
            Reason(ReasonKind.PROFILE, "custom profile text"),
            Reason(ReasonKind.MAP, "custom map text"),
            Reason(ReasonKind.COMPOSITION, "custom composition text"),
        ]

        self.assertEqual(
            _prioritize_reasons(reasons),
            ("custom composition text", "custom map text", "custom profile text"),
        )


if __name__ == "__main__":
    unittest.main()
