import tempfile
import unittest
from pathlib import Path

from valo_picker.app_settings import (
    AppSettings,
    load_settings,
    profile_from_dict,
    save_settings,
    settings_from_dict,
)
from valo_picker.models import UserProfile


class AppSettingsTests(unittest.TestCase):
    def test_load_missing_settings_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_settings(Path(tmp) / "missing.json")

        self.assertEqual(settings.refresh_seconds, 5.0)
        self.assertEqual(settings.default_start_mode, "live")
        self.assertEqual(settings.language, "en")
        self.assertEqual(settings.profile, UserProfile())

    def test_save_and_load_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"

            profile = UserProfile(preferred_styles=frozenset({"controller", "solo_queue"}), beginner_mode=True)
            save_settings(AppSettings(refresh_seconds=7.5, default_start_mode="manual", language="pl", profile=profile), path)
            settings = load_settings(path)

        self.assertEqual(settings.refresh_seconds, 7.5)
        self.assertEqual(settings.default_start_mode, "manual")
        self.assertEqual(settings.language, "pl")
        self.assertEqual(settings.profile, profile)

    def test_invalid_settings_are_clamped_or_defaulted(self):
        settings = settings_from_dict({"refresh_seconds": 99, "default_start_mode": "bad", "language": "bad"})

        self.assertEqual(settings.refresh_seconds, 10.0)
        self.assertEqual(settings.default_start_mode, "live")
        self.assertEqual(settings.language, "en")

    def test_old_settings_without_profile_load_default_profile(self):
        settings = settings_from_dict({"refresh_seconds": 4, "default_start_mode": "status"})

        self.assertEqual(settings.refresh_seconds, 4.0)
        self.assertEqual(settings.default_start_mode, "status")
        self.assertEqual(settings.language, "en")
        self.assertEqual(settings.profile, UserProfile())

    def test_valid_polish_language_loads_from_settings(self):
        settings = settings_from_dict({"language": "pl"})

        self.assertEqual(settings.language, "pl")

    def test_load_settings_accepts_utf8_bom_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text('\ufeff{"language": "pl"}', encoding="utf-8")
            settings = load_settings(path)

        self.assertEqual(settings.language, "pl")

    def test_profile_rejects_unknown_styles(self):
        profile = profile_from_dict(
            {
                "preferred_styles": ["controller", "bad-style", "solo_queue", 123, "beginner"],
                "beginner_mode": False,
            }
        )

        self.assertEqual(profile.preferred_styles, frozenset({"controller", "solo_queue"}))
        self.assertTrue(profile.beginner_mode)


if __name__ == "__main__":
    unittest.main()
