import unittest
from unittest.mock import patch

from valo_picker.app_settings import AppSettings
from valo_picker.cli import _parse_style_choices, _settings_menu, run_interactive, run_live_first
from valo_picker.models import LivePregameSnapshot, LiveStatus, UserProfile


class CliProfileTests(unittest.TestCase):
    def test_profile_choices_can_be_mixed_with_commas(self):
        styles, beginner = _parse_style_choices("4,7")

        self.assertEqual(styles, {"controller", "solo_queue"})
        self.assertFalse(beginner)

    def test_profile_choices_allow_spaces_and_beginner_in_mixed_input(self):
        styles, beginner = _parse_style_choices("4, 7, 8")

        self.assertEqual(styles, {"controller", "solo_queue"})
        self.assertTrue(beginner)

    def test_manual_mode_uses_saved_profile_on_empty_profile_input(self):
        profile = UserProfile(preferred_styles=frozenset({"controller", "solo_queue"}), beginner_mode=True)
        recommendation = object()
        inputs = iter(["Ascent", "", "", "", "", "", ""])

        with (
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            patch("valo_picker.cli.recommend", return_value=recommendation) as recommend_mock,
            patch("valo_picker.cli.print_recommendation") as print_recommendation,
            patch("valo_picker.cli._pause_after_manual_result"),
            patch("builtins.print"),
        ):
            run_interactive(profile)

        self.assertEqual(recommend_mock.call_args.args[2], profile)
        print_recommendation.assert_called_once_with(recommendation, "en")

    def test_manual_mode_can_return_to_menu_from_map_prompt(self):
        with (
            patch("builtins.input", return_value="0"),
            patch("valo_picker.cli.recommend") as recommend_mock,
            patch("builtins.print"),
        ):
            completed = run_interactive(UserProfile())

        self.assertFalse(completed)
        recommend_mock.assert_not_called()

    def test_manual_mode_can_return_to_menu_from_agent_prompt(self):
        inputs = iter(["Ascent", "0"])

        with (
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            patch("valo_picker.cli.recommend") as recommend_mock,
            patch("builtins.print"),
        ):
            completed = run_interactive(UserProfile())

        self.assertFalse(completed)
        recommend_mock.assert_not_called()

    def test_live_mode_passes_saved_profile_to_snapshot_reader(self):
        profile = UserProfile(preferred_styles=frozenset({"support"}), beginner_mode=False)
        settings = AppSettings(profile=profile)
        snapshot = LivePregameSnapshot(status=LiveStatus.NO_CLIENT, message="No client.")

        with (
            patch("valo_picker.cli.ValorantApiService.read_live_snapshot", return_value=snapshot) as read_snapshot,
            patch("valo_picker.cli.clear_terminal"),
            patch("valo_picker.cli.render_live_snapshot", return_value="snapshot"),
            patch("valo_picker.cli._read_menu_choice", return_value="0"),
            patch("builtins.print"),
        ):
            run_live_first(settings)

        read_snapshot.assert_called_once_with(None, profile, "en")

    def test_settings_profile_accepts_style_numbers_without_importing(self):
        settings = AppSettings()
        inputs = iter(["", "", "", "4,7", ""])

        with (
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            patch("valo_picker.cli.save_settings") as save_settings,
            patch("valo_picker.cli.clear_terminal"),
            patch("builtins.print"),
        ):
            updated = _settings_menu(settings)

        self.assertEqual(updated.profile.preferred_styles, frozenset({"controller", "solo_queue"}))
        self.assertFalse(updated.profile.beginner_mode)
        save_settings.assert_called_once_with(updated)

    def test_settings_profile_numbers_replace_previous_beginner_flag(self):
        settings = AppSettings(
            profile=UserProfile(preferred_styles=frozenset({"controller"}), beginner_mode=True)
        )
        inputs = iter(["", "", "", "4,7", ""])

        with (
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            patch("valo_picker.cli.save_settings"),
            patch("valo_picker.cli.clear_terminal"),
            patch("builtins.print"),
        ):
            updated = _settings_menu(settings)

        self.assertEqual(updated.profile.preferred_styles, frozenset({"controller", "solo_queue"}))
        self.assertFalse(updated.profile.beginner_mode)

    def test_settings_profile_uses_8_for_beginner_mode(self):
        settings = AppSettings()
        inputs = iter(["", "", "", "4,7,8", ""])

        with (
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            patch("valo_picker.cli.save_settings"),
            patch("valo_picker.cli.clear_terminal"),
            patch("builtins.print"),
        ):
            updated = _settings_menu(settings)

        self.assertEqual(updated.profile.preferred_styles, frozenset({"controller", "solo_queue"}))
        self.assertTrue(updated.profile.beginner_mode)


if __name__ == "__main__":
    unittest.main()
