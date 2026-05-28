import unittest

from valo_picker.analyzer import format_composition_problem
from valo_picker.data.maps import MAPS
from valo_picker.i18n import t
from valo_picker.models import CompositionProblem, CompositionProblemKind, Role, SelectionState, TeamSlot, UserProfile
from valo_picker.recommender import Reason, ReasonKind, ScoringContext, _prioritize_reasons, advice_for_agent, recommend


POLISH_MARKERS = (
    "brak ",
    "pro tipy",
    "wejscie",
    "flanke",
    "kontrolera",
    "inicjatora",
    "smoke'ow",
)
POLISH_DIACRITICS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def has_problem(result, kind: CompositionProblemKind, **params) -> bool:
    return any(
        problem.kind == kind and all(problem.params.get(key) == value for key, value in params.items())
        for problem in result.analysis.problems
    )


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

        self.assertEqual(result.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", result.best.agent.utility)
        self.assertGreater(result.best.team_score_after_pick, result.analysis.score)
        self.assertTrue(has_problem(result, CompositionProblemKind.MISSING_CONTROLLER))

    def test_breeze_with_smokes_still_values_wall_controller(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Sova", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Jett", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Cypher", SelectionState.LOCKED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Breeze"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role, Role.CONTROLLER)
        self.assertIn("wall", result.best.agent.utility)
        self.assertTrue(any("drugiego controllera ze sciana" in reason for reason in result.best.reasons))

    def test_lotus_without_initiator_prefers_execute_support(self):
        team = (
            TeamSlot("Gracz 1", "Raze", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Clove", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Lotus"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role, Role.INITIATOR)
        self.assertTrue({"flash", "clear", "stun", "info"} & result.best.agent.utility)
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

        self.assertEqual(result.best.agent.role, Role.CONTROLLER)
        self.assertNotEqual(result.best.agent.role, Role.DUELIST)
        self.assertEqual(result.best.reasons[0], "Team nie ma zadnego controllera, wiec smoke'i sa najwyzszym priorytetem.")
        self.assertTrue(has_problem(result, CompositionProblemKind.MISSING_CONTROLLER))

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

        self.assertEqual(result.best.agent.role, Role.CONTROLLER)
        self.assertIn("smokes", result.best.agent.utility)
        self.assertNotEqual(result.best.agent.role, Role.DUELIST)

    def test_bind_without_initiator_prefers_clear_or_flash_support(self):
        team = (
            TeamSlot("Gracz 1", "Brimstone", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Raze", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Cypher", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Clove", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Bind"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role, Role.INITIATOR)
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

        self.assertEqual(result.best.agent.role, Role.CONTROLLER)
        self.assertIn("wall", result.best.agent.utility)
        self.assertTrue(any("scian" in reason or "wall" in reason for reason in result.best.reasons))

    def test_split_with_core_utility_but_no_duelist_prefers_raze_clear(self):
        team = (
            TeamSlot("Gracz 1", "Omen", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Skye", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Cypher", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Gekko", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Split"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role, Role.DUELIST)
        self.assertIn("entry", result.best.agent.utility)
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

        self.assertEqual(result.best.agent.role, Role.DUELIST)
        self.assertIn("entry", result.best.agent.utility)
        self.assertEqual(result.best_role_to_fill, Role.DUELIST)
        self.assertTrue(has_problem(result, CompositionProblemKind.MISSING_DUELIST))

    def test_bind_with_core_utility_but_no_duelist_recommends_raze(self):
        team = (
            TeamSlot("Gracz 1", "Brimstone", SelectionState.LOCKED),
            TeamSlot("Gracz 2", "Skye", SelectionState.LOCKED),
            TeamSlot("Gracz 3", "Cypher", SelectionState.LOCKED),
            TeamSlot("Gracz 4", "Gekko", SelectionState.SELECTED),
            TeamSlot("Ty", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Bind"], UserProfile(), "pl")

        self.assertEqual(result.best.agent.role, Role.DUELIST)
        self.assertIn("entry", result.best.agent.utility)
        self.assertIn("clear", result.best.agent.utility)
        self.assertEqual(result.best_role_to_fill, Role.DUELIST)

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

    def test_map_role_advice_takes_priority_over_generic_role_fallback(self):
        advice = advice_for_agent("Omen", MAPS["Ascent"], "en")

        self.assertIn("smoke Heaven, Tree, Market and entries", advice)
        self.assertNotEqual(advice, t("en", "advice_controller"))

    def test_map_without_role_advice_uses_generic_role_fallback(self):
        advice = advice_for_agent("Omen", MAPS["Bind"], "en")

        self.assertTrue(advice)
        self.assertTrue(advice.endswith(t("en", "advice_controller")))
        self.assertNotIn("smoke Heaven, Tree, Market and entries", advice)

    def test_agent_without_map_entries_gets_generic_role_advice(self):
        advice = advice_for_agent("Neon", MAPS["Ascent"], "en")

        self.assertEqual(advice, t("en", "advice_duelist"))

    def test_english_recommendation_has_no_polish_strategy_or_problem_text(self):
        team = (
            TeamSlot("Player 1", "Jett", SelectionState.LOCKED),
            TeamSlot("Player 2", "Reyna", SelectionState.SELECTED),
            TeamSlot("Player 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Player 4", "Sova", SelectionState.LOCKED),
            TeamSlot("You", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Ascent"], UserProfile(preferred_styles=frozenset({"controller"})), "en")
        texts = [result.advice]
        for candidate in (result.best, *result.alternatives):
            texts.extend(candidate.reasons)
            texts.extend(candidate.warnings)
        texts.extend(format_composition_problem(problem, "en") for problem in result.analysis.problems)

        for text in texts:
            lower = text.lower()
            with self.subTest(text=text):
                self.assertFalse(POLISH_DIACRITICS & set(text), f"Polish characters in EN text: {text}")
                for marker in POLISH_MARKERS:
                    self.assertNotIn(marker, lower, f"Polish marker '{marker}' in EN text: {text}")

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

    def test_scoring_context_build_classifies_slots_and_counters(self):
        team = (
            TeamSlot("P1", "Jett", SelectionState.LOCKED),
            TeamSlot("P2", "Reyna", SelectionState.SELECTED),
            TeamSlot("P3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("P4", None, SelectionState.NONE),
            TeamSlot("P5", "UnknownAgent", SelectionState.LOCKED),
        )
        analysis = recommend(team, MAPS["Ascent"], UserProfile(), "en").analysis

        ctx = ScoringContext.build(team, MAPS["Ascent"], UserProfile(), analysis, "en")

        self.assertEqual(ctx.picked_names, frozenset({"Jett", "Reyna", "Killjoy", "UnknownAgent"}))
        self.assertEqual(ctx.selected_names, frozenset({"Reyna"}))
        self.assertEqual(ctx.locked_names, frozenset({"Jett", "Killjoy", "UnknownAgent"}))
        self.assertNotIn(None, ctx.picked_names)
        self.assertEqual(ctx.base_role_counts[Role.DUELIST], 2)
        self.assertEqual(ctx.base_role_counts[Role.SENTINEL], 1)
        self.assertEqual(ctx.base_role_counts[Role.CONTROLLER], 0)
        self.assertGreater(ctx.base_utility_counts["entry"], 0)
        self.assertGreater(ctx.base_utility_counts["flank_watch"], 0)

    def test_composition_problem_formatting_supports_en_and_pl(self):
        team = (
            TeamSlot("Player 1", "Jett", SelectionState.LOCKED),
            TeamSlot("Player 2", "Reyna", SelectionState.SELECTED),
            TeamSlot("Player 3", "Killjoy", SelectionState.LOCKED),
            TeamSlot("Player 4", "Sova", SelectionState.LOCKED),
            TeamSlot("You", None, SelectionState.NONE, is_self=True),
        )

        result = recommend(team, MAPS["Ascent"], UserProfile(), "en")
        problem = next(problem for problem in result.analysis.problems if problem.kind == CompositionProblemKind.MISSING_CONTROLLER)

        self.assertEqual(format_composition_problem(problem, "en"), "No controller / smokes.")
        self.assertEqual(format_composition_problem(problem, "pl"), "Brak controllera / smoke'ow.")

    def test_all_composition_problem_kinds_are_formatted(self):
        sample_params = {
            CompositionProblemKind.MISSING_UTILITY: {"utility": "smokes"},
        }

        for kind in CompositionProblemKind:
            with self.subTest(kind=kind):
                problem = CompositionProblem(kind, sample_params.get(kind, {}))
                formatted = format_composition_problem(problem, "en")
                self.assertIsInstance(formatted, str)
                self.assertTrue(formatted.strip())
                self.assertFalse(formatted.startswith("analysis_"))

    def test_missing_utility_composition_problem_formats_known_utilities(self):
        utilities = (
            "smokes",
            "info",
            "flash",
            "flank_watch",
            "postplant",
            "wall",
            "clear",
            "stall",
            "new_unknown_utility",
        )

        for utility in utilities:
            with self.subTest(utility=utility):
                problem = CompositionProblem(CompositionProblemKind.MISSING_UTILITY, {"utility": utility})
                english = format_composition_problem(problem, "en")
                polish = format_composition_problem(problem, "pl")

                self.assertTrue(english.strip())
                self.assertTrue(polish.strip())
                self.assertFalse(english.startswith("analysis_"))
                self.assertFalse(polish.startswith("analysis_"))


if __name__ == "__main__":
    unittest.main()
