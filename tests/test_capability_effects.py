from __future__ import annotations

import unittest
from unittest import mock

from uv_studio.capabilities import build_builtin_capability_registry


class CapabilityEffectsTests(unittest.TestCase):
    def test_named_generation_offer_effects_expose_media_long_running_and_cost_risk(self) -> None:
        registry = build_builtin_capability_registry()
        effects = registry.effects_for_offer("native_videoclaw.image_generate")

        self.assertTrue(effects.generates_media)
        self.assertTrue(effects.long_running)
        self.assertTrue(effects.cost_bearing)
        self.assertFalse(effects.destructive)
        self.assertFalse(effects.mutates_timeline)

    def test_free_local_deterministic_offer_does_not_invent_cost_or_long_running_effect(self) -> None:
        with mock.patch(
            "uv_studio.capabilities.builtin.shutil.which",
            side_effect=lambda tool: f"/tools/{tool}",
        ):
            registry = build_builtin_capability_registry()
            effects = registry.effects_for_offer("local_ffmpeg.timeline_assemble")

        self.assertTrue(effects.generates_media)
        self.assertFalse(effects.cost_bearing)
        self.assertFalse(effects.long_running)
        self.assertFalse(effects.destructive)

    def test_effects_are_serializable_stable_policy_metadata(self) -> None:
        registry = build_builtin_capability_registry()
        payload = registry.effects_for_offer("native_videoclaw.video_generate").to_dict()

        self.assertEqual(
            set(payload),
            {
                "mutates_project",
                "mutates_timeline",
                "generates_media",
                "destructive",
                "long_running",
                "reversible",
                "cost_bearing",
            },
        )
        self.assertTrue(all(isinstance(value, bool) for value in payload.values()))


if __name__ == "__main__":
    unittest.main()
