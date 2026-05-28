import unittest

from valo_picker.analyzer import format_composition_problem
from valo_picker.data.agents import AGENTS
from valo_picker.data.maps import MAPS
from valo_picker.models import (
    CandidateScore,
    CompositionProblem,
    CompositionProblemKind,
    LivePregameSnapshot,
    LiveStatus,
    NormalizationIssue,
    NormalizationIssueKind,
    PreGameNormalizationResult,
    Recommendation,
    Role,
    SelectionState,
    TeamAnalysis,
    TeamSlot,
    UserProfile,
)
from valo_picker.recommender import recommend
from valo_picker.terminal_ui import (
    MAX_ALTERNATIVES,
    MAX_NORMALIZATION_ERRORS,
    MAX_NORMALIZATION_WARNINGS,
    MAX_PROBLEMS,
    MAX_REASONS,
    MAX_WARNINGS,
    render_agent_list,
    render_live_snapshot,
    render_recommendation,
)
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
        recommendation = sample_recommendation()
        output = render_recommendation(recommendation)

        self.assertIn(t("en", "snapshot_title_agent_select"), output)
        self.assertIn(t("en", "snapshot_map", map="Ascent"), output)
        self.assertIn(t("en", "render_team"), output)
        self.assertIn("[Jett", output)
        self.assertIn(
            t("en", "render_best_pick", agent=recommendation.best.agent.name, role=recommendation.best.agent.role.value),
            output,
        )
        self.assertIn(t("en", "menu_title"), output)

    def test_polish_recommendation_renders_polish_labels(self):
        recommendation = sample_polish_recommendation()
        output = render_recommendation(recommendation, "pl")

        self.assertIn(t("pl", "render_recommendation"), output)
        self.assertIn(
            t("pl", "render_best_pick", agent=recommendation.best.agent.name, role=recommendation.best.agent.role.value),
            output,
        )
        self.assertIn(t("pl", "render_problems"), output)
        self.assertIn(f"{t('pl', 'state_locked')}/{t('pl', 'render_level_unknown')}", output)
        self.assertIn(f"{t('pl', 'state_selected')}/{t('pl', 'render_level_unknown')}", output)
        self.assertNotIn(f"{t('en', 'state_locked')}/{t('en', 'render_level_unknown')}", output)
        self.assertNotIn(f"{t('en', 'state_selected')}/{t('en', 'render_level_unknown')}", output)

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

        self.assertIn(t("pl", "manual_player", index=1), output)
        self.assertIn(t("pl", "manual_self"), output)
        self.assertNotIn(t("en", "manual_player", index=1), output)
        self.assertNotIn(t("en", "manual_self"), output)

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

        self.assertIn(t("pl", "local_valorant_missing"), output)
        self.assertIn(t("pl", "snapshot_map", map=t("pl", "unknown_map")), output)
        self.assertIn(t("pl", "menu_refresh"), output)
        self.assertIn(t("pl", "menu_agents"), output)
        self.assertIn(t("pl", "menu_manual"), output)
        self.assertIn(t("pl", "menu_settings"), output)
        self.assertIn(t("pl", "menu_exit"), output)
        self.assertNotIn(t("en", "local_valorant_missing"), output)
        self.assertNotIn(t("en", "snapshot_map", map=t("en", "unknown_map")), output)
        self.assertNotIn(t("en", "menu_refresh"), output)
        self.assertNotIn(t("en", "menu_agents"), output)
        self.assertNotIn(t("en", "menu_manual"), output)
        self.assertNotIn(t("en", "menu_settings"), output)

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

        self.assertIn(f"[{t('en', 'unknown_agent')}", output)
        self.assertIn(f"[{t('en', 'state_none')}", output)

    def test_menu_does_not_offer_agent_selection_or_locking(self):
        output = render_recommendation(sample_recommendation())

        self.assertNotIn("Select Agent without locking", output)
        self.assertNotIn("Lock Character", output)
        self.assertNotIn("lock agent", output.casefold())

    def test_agent_list_renders_known_agents(self):
        output = render_agent_list()

        self.assertIn(t("en", "render_all_agents"), output)
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

        self.assertIn(t("pl", "snapshot_title_current_game"), output)
        self.assertIn(t("pl", "snapshot_map", map="Ascent"), output)
        self.assertIn(t("pl", "snapshot_state", state="IN_PROGRESS"), output)
        self.assertIn("Taczer#EUW (Omen)", output)
        self.assertIn("Current game detected.", output)
        self.assertIn(t("pl", "render_agent_advice"), output)
        self.assertIn(t("pl", "advice_pro_tips", tips=""), output)
        self.assertIn("Graj blisko teamu", output)

    def test_recommendation_render_respects_output_limits(self):
        best = CandidateScore(
            AGENTS["Omen"],
            100.0,
            tuple(f"reason-{index}" for index in range(MAX_REASONS + 2)),
            tuple(f"warning-{index}" for index in range(MAX_WARNINGS + 2)),
            9.0,
        )
        alternatives = tuple(
            CandidateScore(
                agent,
                90.0 - index,
                (f"alt-reason-{index}",),
                (),
                8.0,
            )
            for index, agent in enumerate(
                (
                    AGENTS["Astra"],
                    AGENTS["Brimstone"],
                    AGENTS["Clove"],
                    AGENTS["Miks"],
                    AGENTS["Viper"],
                    AGENTS["Harbor"],
                )
            )
        )
        analysis = TeamAnalysis(
            role_counts={role: 0 for role in Role},
            utility_counts={},
            selected_agents=(),
            locked_agents=(),
            problems=tuple(
                CompositionProblem(CompositionProblemKind.MISSING_UTILITY, {"utility": utility})
                for utility in ("smokes", "flash", "info", "clear", "wall")
            ),
            missing_roles=(),
            missing_utility=(),
            score=3.0,
        )
        recommendation = Recommendation(
            map_info=MAPS["Ascent"],
            team=(),
            analysis=analysis,
            best=best,
            alternatives=alternatives,
            best_role_to_fill=None,
            advice="Advice.",
            warning=None,
        )

        output = render_recommendation(recommendation)

        self.assertIn(t("en", "render_alternatives", alternatives="Astra, Brimstone, Clove, Miks"), output)
        self.assertNotIn("Viper", output)
        self.assertNotIn("Harbor", output)
        for index in range(MAX_REASONS):
            self.assertIn(f"reason-{index}", output)
        self.assertNotIn(f"reason-{MAX_REASONS}", output)
        for index in range(MAX_WARNINGS):
            self.assertIn(f"warning-{index}", output)
        self.assertNotIn(f"warning-{MAX_WARNINGS}", output)
        for problem in analysis.problems[:MAX_PROBLEMS]:
            self.assertIn(format_composition_problem(problem, "en"), output)
        for problem in analysis.problems[MAX_PROBLEMS:]:
            self.assertNotIn(format_composition_problem(problem, "en"), output)

    def test_live_snapshot_render_respects_normalization_issue_limits(self):
        normalized = PreGameNormalizationResult(
            map_info=MAPS["Ascent"],
            team=(),
            warnings=tuple(
                NormalizationIssue(NormalizationIssueKind.UNKNOWN_MAP, {"map_id": f"warning-map-{index}"})
                for index in range(MAX_NORMALIZATION_WARNINGS + 2)
            ),
            errors=tuple(
                NormalizationIssue(NormalizationIssueKind.BAD_PLAYER, {"index": index})
                for index in range(MAX_NORMALIZATION_ERRORS + 2)
            ),
            match_id="match-1",
            map_id=MAPS["Ascent"].map_id,
        )
        snapshot = LivePregameSnapshot(
            status=LiveStatus.AGENT_SELECT,
            message="Agent Select lobby detected.",
            normalized_match=normalized,
        )

        output = render_live_snapshot(snapshot)

        for index in range(MAX_NORMALIZATION_WARNINGS):
            self.assertIn(f"warning-map-{index}", output)
        self.assertNotIn(f"warning-map-{MAX_NORMALIZATION_WARNINGS}", output)
        for index in range(MAX_NORMALIZATION_ERRORS):
            self.assertIn(t("en", "normalizer_bad_player", index=index), output)
        self.assertNotIn(t("en", "normalizer_bad_player", index=MAX_NORMALIZATION_ERRORS), output)


if __name__ == "__main__":
    unittest.main()
