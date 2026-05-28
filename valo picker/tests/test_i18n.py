import unittest

from valo_picker.i18n import (
    DEFAULT_LANGUAGE,
    MESSAGES,
    SUPPORTED_LANGUAGES,
    display_text,
    localized_text,
    localized_texts,
    normalize_language,
    t,
)
from valo_picker.models import NormalizationIssue, NormalizationIssueKind
from valo_picker.normalizer import format_normalization_issue


class I18nTests(unittest.TestCase):
    def test_all_supported_languages_have_message_tables(self):
        self.assertEqual(set(MESSAGES), SUPPORTED_LANGUAGES)

    def test_all_supported_languages_have_same_message_keys(self):
        expected = set(MESSAGES[DEFAULT_LANGUAGE])
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                missing = expected - set(MESSAGES[language])
                extra = set(MESSAGES[language]) - expected
                self.assertFalse(missing, f"{language} missing keys: {sorted(missing)}")
                self.assertFalse(extra, f"{language} extra keys: {sorted(extra)}")

    def test_message_values_are_non_empty_strings(self):
        empty = [
            f"{language}.{key}"
            for language, messages in MESSAGES.items()
            for key, value in messages.items()
            if not isinstance(value, str) or not value
        ]

        self.assertFalse(empty, f"Empty i18n messages: {empty}")

    def test_normalize_language_defaults_to_english(self):
        self.assertEqual(normalize_language("pl"), "pl")
        self.assertEqual(normalize_language("EN"), "en")
        self.assertEqual(normalize_language("bad"), DEFAULT_LANGUAGE)
        self.assertEqual(normalize_language(None), DEFAULT_LANGUAGE)

    def test_t_formats_message(self):
        self.assertEqual(t("en", "snapshot_map", map="Ascent"), "Map: Ascent")
        self.assertEqual(t("pl", "snapshot_map", map="Ascent"), "Mapa: Ascent")

    def test_polish_display_text_is_ascii_safe_for_raster_console(self):
        text = t("pl", "rec_no_controller")

        self.assertIn("zadnego", text)
        self.assertIn("najwyzszym", text)
        self.assertEqual(display_text("Zażółć gęślą jaźń", "pl"), "Zazolc gesla jazn")

    def test_localized_text_uses_language_then_english_fallback(self):
        localized = {"en": "English text", "pl": "Zażółć"}

        self.assertEqual(localized_text(localized, "pl"), "Zazolc")
        self.assertEqual(localized_text({"en": "English text"}, "pl"), "English text")
        self.assertIsNone(localized_text({}, "pl"))

    def test_localized_texts_return_tuple_and_ascii_safe_output(self):
        localized = {"en": ("English tip",), "pl": ("Zażółć",)}

        self.assertEqual(localized_texts(localized, "pl"), ("Zazolc",))
        self.assertEqual(localized_texts({"en": ("English tip",)}, "pl"), ("English tip",))

    def test_all_normalization_issue_kinds_have_i18n_keys(self):
        for kind in NormalizationIssueKind:
            key = f"normalizer_{kind.value}"
            with self.subTest(key=key):
                for language in SUPPORTED_LANGUAGES:
                    self.assertIn(key, MESSAGES[language], f"Missing {language} key: {key}")

    def test_all_normalization_issue_kinds_can_be_formatted(self):
        issue_cases = (
            NormalizationIssue(NormalizationIssueKind.UNKNOWN_MAP, {"map_id": "/Game/Maps/Test/Test"}),
            NormalizationIssue(NormalizationIssueKind.BAD_PREGAME_PAYLOAD),
            NormalizationIssue(NormalizationIssueKind.BAD_COREGAME_PAYLOAD),
            NormalizationIssue(NormalizationIssueKind.MISSING_PREGAME_MAP),
            NormalizationIssue(NormalizationIssueKind.MISSING_COREGAME_MAP),
            NormalizationIssue(NormalizationIssueKind.MISSING_ALLY_TEAM),
            NormalizationIssue(NormalizationIssueKind.MISSING_ALLY_PLAYERS),
            NormalizationIssue(NormalizationIssueKind.BAD_PLAYER, {"index": 2}),
            NormalizationIssue(NormalizationIssueKind.UNKNOWN_STATE, {"index": 3, "state": "hovered"}),
            NormalizationIssue(NormalizationIssueKind.UNKNOWN_CHARACTER, {"index": 4, "character_id": "agent-id"}),
            NormalizationIssue(NormalizationIssueKind.MISSING_CORE_PLAYERS),
            NormalizationIssue(NormalizationIssueKind.NO_ALLIES),
        )

        self.assertEqual({issue.kind for issue in issue_cases}, set(NormalizationIssueKind))
        for issue in issue_cases:
            for language in SUPPORTED_LANGUAGES:
                with self.subTest(kind=issue.kind, language=language):
                    formatted = format_normalization_issue(issue, language)
                    self.assertTrue(formatted.strip())
                    self.assertFalse(formatted.startswith("normalizer_"))

    def test_common_polish_live_keys_are_not_english_fallbacks(self):
        keys = (
            "local_valorant_missing",
            "menu_refresh",
            "menu_agents",
            "menu_manual",
            "menu_settings",
            "menu_exit",
            "live_refresh",
            "live_profile",
            "unknown_map",
            "unknown_agent",
            "state_selected",
            "state_locked",
            "render_level_unknown",
        )

        for key in keys:
            with self.subTest(key=key):
                self.assertNotEqual(MESSAGES["pl"][key], MESSAGES["en"][key])


if __name__ == "__main__":
    unittest.main()
