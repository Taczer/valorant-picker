import unittest

from valo_picker.data.agents import AGENTS
from valo_picker.data.map_tuning import MAP_TUNING
from valo_picker.data.maps import MAPS
from valo_picker.data.synergies import MAP_AGENT_NOTES, MAP_AGENT_TIPS, PAIR_SYNERGIES


class DataIntegrityTests(unittest.TestCase):
    def test_pair_synergy_agents_and_maps_exist(self):
        for pair, (_, localized_reason, maps) in PAIR_SYNERGIES.items():
            for agent_name in pair:
                self.assertIn(agent_name, AGENTS, f"Unknown agent in PAIR_SYNERGIES: {agent_name}")
            for map_name in maps:
                self.assertIn(map_name, MAPS, f"Unknown map in PAIR_SYNERGIES: {map_name}")
            self.assertLocalizedText(localized_reason)

    def test_map_agent_notes_reference_known_data(self):
        for map_name, agent_notes in MAP_AGENT_NOTES.items():
            self.assertIn(map_name, MAPS, f"Unknown map in MAP_AGENT_NOTES: {map_name}")
            for agent_name, localized_note in agent_notes.items():
                self.assertIn(agent_name, AGENTS, f"Unknown agent in MAP_AGENT_NOTES: {agent_name}")
                self.assertLocalizedText(localized_note)

    def test_map_agent_tips_reference_known_data(self):
        for map_name, agent_tips in MAP_AGENT_TIPS.items():
            self.assertIn(map_name, MAPS, f"Unknown map in MAP_AGENT_TIPS: {map_name}")
            for agent_name, localized_tips in agent_tips.items():
                self.assertIn(agent_name, AGENTS, f"Unknown agent in MAP_AGENT_TIPS: {agent_name}")
                self.assertEqual(set(localized_tips), {"en", "pl"})
                for language, tips in localized_tips.items():
                    self.assertIsInstance(tips, tuple, f"{language} tips must be a tuple")
                    self.assertTrue(tips, f"{map_name}/{agent_name}/{language} tips are empty")
                    for tip in tips:
                        self.assertIsInstance(tip, str)
                        self.assertTrue(tip.strip())

    def test_map_tuning_and_agent_map_names_exist(self):
        for map_name in MAP_TUNING:
            self.assertIn(map_name, MAPS, f"Unknown map in MAP_TUNING: {map_name}")
        for agent in AGENTS.values():
            for map_name in agent.strong_maps:
                self.assertIn(map_name, MAPS, f"Unknown strong map for {agent.name}: {map_name}")
            for map_name in agent.weak_maps:
                self.assertIn(map_name, MAPS, f"Unknown weak map for {agent.name}: {map_name}")

    def test_selfish_duelist_traits_are_on_agents(self):
        for agent_name in ("Reyna", "Iso", "Phoenix"):
            self.assertIn("selfish", AGENTS[agent_name].traits)

    def assertLocalizedText(self, localized_text):
        self.assertEqual(set(localized_text), {"en", "pl"})
        for language, text in localized_text.items():
            self.assertIsInstance(text, str, f"{language} text must be a string")
            self.assertTrue(text.strip(), f"{language} text is empty")


if __name__ == "__main__":
    unittest.main()
