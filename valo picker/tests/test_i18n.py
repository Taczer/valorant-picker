import unittest

from valo_picker.i18n import DEFAULT_LANGUAGE, MESSAGES, SUPPORTED_LANGUAGES, normalize_language, t


class I18nTests(unittest.TestCase):
    def test_all_supported_languages_have_message_tables(self):
        self.assertEqual(set(MESSAGES), SUPPORTED_LANGUAGES)

    def test_pl_has_all_en_keys(self):
        missing = set(MESSAGES["en"]) - set(MESSAGES["pl"])

        self.assertFalse(missing, f"PL missing keys: {sorted(missing)}")

    def test_en_has_all_pl_keys(self):
        missing = set(MESSAGES["pl"]) - set(MESSAGES["en"])

        self.assertFalse(missing, f"EN missing keys: {sorted(missing)}")

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
