from __future__ import annotations

import unittest

from uv_studio.production.directions import (
    ProductionDirectionNotFound,
    get_production_direction,
    list_production_directions,
)


class ProductionDirectionTests(unittest.TestCase):
    def test_builtin_directions_are_unique_and_distinct_from_operation_tools(self) -> None:
        directions = list_production_directions()
        ids = [direction.direction_id for direction in directions]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            ids,
            [
                "micro_drama",
                "commercial",
                "music_video",
                "narrated_video",
                "dub_battle",
                "free_project",
            ],
        )

        forbidden_tool_ids = {
            "dubbing",
            "photo_to_video",
            "visualizer",
            "action_transfer",
            "digital_human",
            "performance_lip_sync",
        }
        self.assertTrue(forbidden_tool_ids.isdisjoint(ids))

    def test_direction_metadata_describes_production_composition(self) -> None:
        micro_drama = get_production_direction("micro_drama")
        self.assertIn("characters", micro_drama.workspace_sections)
        self.assertIn("scenes", micro_drama.workspace_sections)
        self.assertIn("shots", micro_drama.workspace_sections)

        commercial = get_production_direction("commercial")
        self.assertIn("product", commercial.workspace_sections)
        self.assertIn("audience", commercial.workspace_sections)

        dub_battle = get_production_direction("dub_battle")
        self.assertIn("dialogue", dub_battle.workspace_sections)
        self.assertIn("cast", dub_battle.workspace_sections)
        self.assertIn("takes", dub_battle.workspace_sections)

    def test_unknown_direction_fails_closed(self) -> None:
        with self.assertRaisesRegex(ProductionDirectionNotFound, "unknown production direction"):
            get_production_direction("missing")


if __name__ == "__main__":
    unittest.main()
