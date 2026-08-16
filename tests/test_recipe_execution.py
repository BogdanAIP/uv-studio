from __future__ import annotations

import unittest

from uv_studio.recipes import (
    ExecutionCompatibility,
    InputSlotKind,
    PolicyMode,
    build_builtin_registry,
    resolve_project_execution,
)


class RecipeExecutionPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_builtin_registry()

    def test_general_video_does_not_fall_back_to_narrated_pipeline(self) -> None:
        plan = resolve_project_execution(self.registry, "general_video")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.UNAVAILABLE)
        self.assertFalse(plan.can_prepare_native_execution)
        self.assertIsNone(plan.target)
        self.assertIn("narration-led", plan.reason)

    def test_narrated_video_maps_to_standard_with_runtime_model_slots(self) -> None:
        plan = resolve_project_execution(self.registry, "narrated_video")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.AVAILABLE)
        self.assertTrue(plan.can_prepare_native_execution)
        self.assertEqual(plan.target.target_id, "standard")
        self.assertEqual(plan.target.launch_path, "/api/pipelines/standard/tasks")
        self.assertEqual(
            [slot.slot_id for slot in plan.runtime_config_slots],
            ["llm_model", "image_model", "video_model"],
        )
        self.assertEqual(
            [slot.slot_id for slot in plan.input_slots if slot.required],
            ["text"],
        )

    def test_music_video_is_uv_owned_and_song_input_is_audio(self) -> None:
        plan = resolve_project_execution(self.registry, "music_video")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.UNAVAILABLE)
        self.assertFalse(plan.can_prepare_native_execution)
        self.assertIsNone(plan.target)
        self.assertIn("UV Studio-owned", plan.reason)
        self.assertEqual([slot.slot_id for slot in plan.input_slots], ["song"])
        self.assertEqual(plan.input_slots[0].kind, InputSlotKind.AUDIO)
        self.assertEqual(plan.production_policy.sample_first, PolicyMode.REQUIRED)
        encoded = str(plan.to_dict()).lower()
        self.assertNotIn("qwen", encoded)
        self.assertNotIn("kling", encoded)
        self.assertNotIn("seedance", encoded)

    def test_action_transfer_binding_is_available_and_sample_first(self) -> None:
        plan = resolve_project_execution(self.registry, "action_transfer")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.AVAILABLE)
        self.assertEqual(plan.target.target_id, "action_transfer")
        self.assertEqual(
            [slot.slot_id for slot in plan.input_slots],
            ["target_reference", "source_video", "instruction"],
        )
        instruction = next(slot for slot in plan.input_slots if slot.slot_id == "instruction")
        self.assertFalse(instruction.required)
        self.assertTrue(instruction.default)
        self.assertEqual(plan.production_policy.source_review, PolicyMode.REQUIRED)
        self.assertEqual(plan.production_policy.sample_first, PolicyMode.REQUIRED)
        self.assertEqual(plan.production_policy.final_review, PolicyMode.REQUIRED)

    def test_digital_human_is_partial_not_falsely_launchable(self) -> None:
        plan = resolve_project_execution(self.registry, "digital_human")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.PARTIAL)
        self.assertFalse(plan.can_prepare_native_execution)
        self.assertIsNone(plan.target)
        self.assertIn("does not accept", plan.reason)
        self.assertEqual([slot.slot_id for slot in plan.input_slots], ["portrait", "speech"])

    def test_stage8_story_uses_typed_compositional_inputs(self) -> None:
        plan = resolve_project_execution(self.registry, "story_video")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.UNAVAILABLE)
        self.assertIsNone(plan.target)
        self.assertIn("compositional", plan.reason)
        self.assertEqual(
            [(slot.slot_id, slot.kind, slot.required) for slot in plan.input_slots],
            [
                ("brief", InputSlotKind.TEXT, True),
                ("script", InputSlotKind.TEXT, False),
                ("image", InputSlotKind.IMAGE, False),
                ("video", InputSlotKind.VIDEO, False),
                ("audio", InputSlotKind.AUDIO, False),
            ],
        )
        self.assertEqual(plan.production_policy.scene_ledger, PolicyMode.REQUIRED)

    def test_stage8_commercial_preserves_product_media_types(self) -> None:
        plan = resolve_project_execution(self.registry, "commercial_product")
        slots = {slot.slot_id: slot for slot in plan.input_slots}
        self.assertEqual(plan.compatibility, ExecutionCompatibility.UNAVAILABLE)
        self.assertEqual(slots["brief"].kind, InputSlotKind.TEXT)
        self.assertEqual(slots["product_image"].kind, InputSlotKind.IMAGE)
        self.assertEqual(slots["product_video"].kind, InputSlotKind.VIDEO)
        self.assertEqual(slots["audio"].kind, InputSlotKind.AUDIO)
        self.assertEqual(plan.production_policy.sample_first, PolicyMode.REQUIRED)

    def test_stage8_performance_is_partial_and_does_not_fake_native_launch(self) -> None:
        plan = resolve_project_execution(self.registry, "performance_lip_sync")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.PARTIAL)
        self.assertFalse(plan.can_prepare_native_execution)
        self.assertIsNone(plan.target)
        slots = {slot.slot_id: slot for slot in plan.input_slots}
        self.assertEqual(slots["portrait"].kind, InputSlotKind.IMAGE)
        self.assertEqual(slots["speech"].kind, InputSlotKind.AUDIO)
        self.assertEqual(slots["performance_video"].kind, InputSlotKind.VIDEO)
        self.assertFalse(slots["performance_video"].required)
        self.assertIn("no accepted executable offer", plan.reason)

    def test_stage8_free_project_has_only_optional_typed_inputs(self) -> None:
        plan = resolve_project_execution(self.registry, "free_project")
        self.assertEqual(plan.compatibility, ExecutionCompatibility.UNAVAILABLE)
        self.assertFalse(plan.can_prepare_native_execution)
        self.assertTrue(plan.input_slots)
        self.assertTrue(all(not slot.required for slot in plan.input_slots))
        self.assertEqual(
            [slot.kind for slot in plan.input_slots],
            [InputSlotKind.TEXT, InputSlotKind.IMAGE, InputSlotKind.VIDEO, InputSlotKind.AUDIO],
        )
        self.assertIn("no one-click", plan.reason)

    def test_execution_plan_preserves_recipe_production_policy(self) -> None:
        recipe = self.registry.get("action_transfer")
        plan = resolve_project_execution(self.registry, recipe.recipe_id)
        self.assertEqual(plan.production_policy, recipe.production_policy)
        self.assertEqual(plan.to_dict()["production_policy"], recipe.production_policy.to_dict())

    def test_plan_json_does_not_choose_provider_or_model(self) -> None:
        for recipe_id in self.registry.ids():
            encoded = str(resolve_project_execution(self.registry, recipe_id).to_dict()).lower()
            self.assertNotIn("dashscope", encoded)
            self.assertNotIn("qwen", encoded)
            self.assertNotIn("openclaw", encoded)
            # Native compatibility is allowed to name the adapter, but never a concrete provider/model ID.
            self.assertNotIn("wan2", encoded)
            self.assertNotIn("seedance", encoded)
            self.assertNotIn("kling", encoded)


if __name__ == "__main__":
    unittest.main()
