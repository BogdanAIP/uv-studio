from __future__ import annotations

import unittest

from uv_studio.recipes import (
    BUILTIN_RECIPES,
    DuplicateRecipe,
    PolicyMode,
    ProductionPolicy,
    RecipeDefinition,
    RecipeRegistry,
    RecipeStep,
    RecipeUIHints,
    RecipeValidationError,
    UnknownRecipe,
    VIDEOCLAW_PIPELINE_BINDINGS,
    build_builtin_registry,
)


class RecipeRegistryTests(unittest.TestCase):
    def test_builtin_registry_is_deterministic(self) -> None:
        registry = build_builtin_registry()
        self.assertEqual(
            registry.ids(),
            (
                "general_video",
                "narrated_video",
                "music_video",
                "action_transfer",
                "digital_human",
                "story_video",
                "commercial_product",
                "performance_lip_sync",
                "free_project",
            ),
        )
        self.assertEqual(registry.list(), BUILTIN_RECIPES)

    def test_general_video_has_no_mandatory_specialized_modes(self) -> None:
        recipe = build_builtin_registry().get("general_video")
        self.assertNotIn("narration", recipe.required_inputs)
        self.assertNotIn("music", recipe.required_inputs)
        self.assertNotIn("song", recipe.required_inputs)
        self.assertNotIn("story", recipe.required_inputs)
        self.assertEqual(recipe.production_policy.continuity, PolicyMode.OFF)
        self.assertNotEqual(recipe.production_policy.final_review, PolicyMode.REQUIRED)
        self.assertNotIn("speech.synthesize", recipe.required_capabilities)

    def test_music_video_is_explicit_music_specific_recipe(self) -> None:
        recipe = build_builtin_registry().get("music_video")
        self.assertEqual(recipe.required_inputs, ("song",))
        self.assertEqual(recipe.required_capabilities, ("timeline.assemble",))
        self.assertIn("media.understand", recipe.optional_capabilities)
        self.assertEqual(recipe.production_policy.source_review, PolicyMode.REQUIRED)
        self.assertEqual(recipe.production_policy.direction_gate, PolicyMode.REQUIRED)
        self.assertEqual(recipe.production_policy.sample_first, PolicyMode.REQUIRED)
        self.assertEqual(recipe.production_policy.plan_gate, PolicyMode.REQUIRED)
        self.assertEqual(recipe.production_policy.final_review, PolicyMode.REQUIRED)
        self.assertEqual(recipe.production_policy.continuity, PolicyMode.OPTIONAL)
        self.assertNotIn(recipe.recipe_id, VIDEOCLAW_PIPELINE_BINDINGS)

    def test_narrated_video_is_not_the_general_default(self) -> None:
        recipe = build_builtin_registry().get("narrated_video")
        self.assertIn("speech.synthesize", recipe.required_capabilities)
        self.assertEqual(VIDEOCLAW_PIPELINE_BINDINGS[recipe.recipe_id], "standard")
        self.assertNotEqual(recipe.recipe_id, "general_video")

    def test_existing_video_specialized_recipes_require_source_review(self) -> None:
        registry = build_builtin_registry()
        self.assertEqual(
            registry.get("action_transfer").production_policy.source_review,
            PolicyMode.REQUIRED,
        )
        self.assertEqual(
            registry.get("digital_human").production_policy.source_review,
            PolicyMode.REQUIRED,
        )

    def test_stage8_story_and_commercial_are_compositional_not_native_bindings(self) -> None:
        registry = build_builtin_registry()
        story = registry.get("story_video")
        commercial = registry.get("commercial_product")
        self.assertEqual(story.required_capabilities, ("timeline.assemble",))
        self.assertEqual(commercial.required_capabilities, ("timeline.assemble",))
        self.assertEqual(story.production_policy.scene_ledger, PolicyMode.REQUIRED)
        self.assertEqual(commercial.production_policy.sample_first, PolicyMode.REQUIRED)
        self.assertNotIn(story.recipe_id, VIDEOCLAW_PIPELINE_BINDINGS)
        self.assertNotIn(commercial.recipe_id, VIDEOCLAW_PIPELINE_BINDINGS)

    def test_stage8_performance_is_explicitly_capability_gated(self) -> None:
        recipe = build_builtin_registry().get("performance_lip_sync")
        self.assertEqual(recipe.required_inputs, ("portrait", "speech"))
        self.assertEqual(recipe.required_capabilities, ("video.digital_human",))
        self.assertEqual(recipe.production_policy.sample_first, PolicyMode.REQUIRED)
        self.assertEqual(recipe.production_policy.final_review, PolicyMode.REQUIRED)
        self.assertNotIn(recipe.recipe_id, VIDEOCLAW_PIPELINE_BINDINGS)

    def test_stage8_free_project_has_no_fake_required_pipeline(self) -> None:
        recipe = build_builtin_registry().get("free_project")
        self.assertEqual(recipe.required_inputs, ())
        self.assertEqual(recipe.required_capabilities, ())
        self.assertIn("timeline.assemble", recipe.optional_capabilities)
        self.assertNotIn(recipe.recipe_id, VIDEOCLAW_PIPELINE_BINDINGS)

    def test_duplicate_registration_is_rejected(self) -> None:
        recipe = build_builtin_registry().get("general_video")
        registry = RecipeRegistry([recipe])
        with self.assertRaises(DuplicateRecipe):
            registry.register(recipe)

    def test_unknown_recipe_is_explicit(self) -> None:
        with self.assertRaises(UnknownRecipe):
            build_builtin_registry().get("missing_recipe")
        with self.assertRaises(UnknownRecipe):
            build_builtin_registry().get("../escape")

    def test_required_and_optional_inputs_cannot_overlap(self) -> None:
        with self.assertRaises(RecipeValidationError):
            RecipeDefinition(
                recipe_id="bad_recipe",
                title="Bad",
                description="Invalid overlapping inputs",
                required_inputs=("brief",),
                optional_inputs=("brief",),
                required_capabilities=("video.generate",),
                optional_capabilities=(),
                steps=(RecipeStep("generate", "Generate", "Generate video", "video.generate"),),
                production_policy=ProductionPolicy(),
                ui=RecipeUIHints(category="test", primary_input_label="Brief"),
            )

    def test_step_cannot_reference_undeclared_capability(self) -> None:
        with self.assertRaises(RecipeValidationError):
            RecipeDefinition(
                recipe_id="bad_capability",
                title="Bad",
                description="Undeclared capability",
                required_inputs=("brief",),
                optional_inputs=(),
                required_capabilities=(),
                optional_capabilities=(),
                steps=(RecipeStep("generate", "Generate", "Generate video", "video.generate"),),
                production_policy=ProductionPolicy(),
                ui=RecipeUIHints(category="test", primary_input_label="Brief"),
            )

    def test_duplicate_step_ids_are_rejected(self) -> None:
        with self.assertRaises(RecipeValidationError):
            RecipeDefinition(
                recipe_id="bad_steps",
                title="Bad",
                description="Duplicate steps",
                required_inputs=("brief",),
                optional_inputs=(),
                required_capabilities=(),
                optional_capabilities=(),
                steps=(
                    RecipeStep("plan", "Plan", "First plan"),
                    RecipeStep("plan", "Plan again", "Second plan"),
                ),
                production_policy=ProductionPolicy(),
                ui=RecipeUIHints(category="test", primary_input_label="Brief"),
            )

    def test_policy_string_values_are_normalized(self) -> None:
        policy = ProductionPolicy(source_review="required", final_review="optional")
        self.assertEqual(policy.source_review, PolicyMode.REQUIRED)
        self.assertEqual(policy.final_review, PolicyMode.OPTIONAL)

    def test_invalid_policy_value_is_rejected(self) -> None:
        with self.assertRaises(RecipeValidationError):
            ProductionPolicy(source_review="always")


if __name__ == "__main__":
    unittest.main()
