import unittest

from valo_picker.analyzer import analyze_team
from valo_picker.data.maps import MAPS
from valo_picker.models import CompositionProblemKind, Role, SelectionState, TeamSlot


def slot(agent_name: str | None, state: SelectionState = SelectionState.LOCKED) -> TeamSlot:
    return TeamSlot("Player", agent_name, state)


def problem_count(analysis, kind: CompositionProblemKind, **params) -> int:
    return sum(
        problem.kind == kind and all(problem.params.get(key) == value for key, value in params.items())
        for problem in analysis.problems
    )


class AnalyzerTests(unittest.TestCase):
    def test_two_duelists_no_controller_detected_without_duplicate_controller_problem(self):
        team = (
            slot("Jett"),
            slot("Reyna"),
            slot("Killjoy"),
            slot("Sova"),
            slot(None, SelectionState.NONE),
        )

        analysis = analyze_team(team, MAPS["Ascent"])

        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_CONTROLLER), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.TWO_DUELISTS_NO_CONTROLLER), 1)
        self.assertEqual(analysis.role_counts[Role.DUELIST], 2)

    def test_too_many_duelists_detected(self):
        team = (
            slot("Jett"),
            slot("Reyna"),
            slot("Phoenix"),
            slot("Omen"),
            slot("Sova"),
        )

        analysis = analyze_team(team, MAPS["Ascent"])

        self.assertEqual(problem_count(analysis, CompositionProblemKind.TOO_MANY_DUELISTS), 1)
        self.assertEqual(analysis.role_counts[Role.DUELIST], 3)

    def test_missing_utility_is_detected_once_with_params(self):
        team = (
            slot("Jett"),
            slot("Reyna"),
            slot("Killjoy"),
            slot("Sova"),
            slot(None, SelectionState.NONE),
        )

        analysis = analyze_team(team, MAPS["Ascent"])

        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_UTILITY, utility="smokes"), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_UTILITY, utility="flash"), 1)

    def test_deduplication_keeps_distinct_missing_utility_params(self):
        team = (
            slot("Jett"),
            slot("Reyna"),
            slot("Killjoy"),
            slot(None, SelectionState.NONE),
        )

        analysis = analyze_team(team, MAPS["Ascent"])
        utilities = {
            problem.params.get("utility")
            for problem in analysis.problems
            if problem.kind == CompositionProblemKind.MISSING_UTILITY
        }

        self.assertIn("smokes", utilities)
        self.assertIn("flash", utilities)
        self.assertEqual(utilities, {"smokes", "flash"})

    def test_deduplication_removes_identical_problems(self):
        team = (
            slot("Jett"),
            slot(None, SelectionState.NONE),
            slot(None, SelectionState.NONE),
            slot(None, SelectionState.NONE),
        )

        analysis = analyze_team(team, MAPS["Ascent"])

        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_CONTROLLER), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_INITIATOR), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_SENTINEL), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_UTILITY, utility="smokes"), 1)

    def test_complete_ascent_core_has_no_major_problems(self):
        team = (
            slot("Jett"),
            slot("Omen"),
            slot("Sova"),
            slot("Killjoy"),
            slot(None, SelectionState.NONE),
        )

        analysis = analyze_team(team, MAPS["Ascent"])

        self.assertEqual(analysis.problems, ())
        self.assertEqual(analysis.missing_roles, ())
        self.assertEqual(analysis.missing_utility, ())

    def test_unknown_agents_do_not_count_toward_roles_or_problems(self):
        team = (
            slot("UnknownAgent"),
            slot(None, SelectionState.NONE),
        )

        analysis = analyze_team(team, MAPS["Ascent"])

        self.assertEqual(analysis.locked_agents, ())
        self.assertEqual(analysis.role_counts[Role.CONTROLLER], 0)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_CONTROLLER), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_INITIATOR), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_SENTINEL), 1)
        self.assertEqual(problem_count(analysis, CompositionProblemKind.MISSING_DUELIST), 1)


if __name__ == "__main__":
    unittest.main()
