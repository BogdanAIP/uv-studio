from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from uv_studio.server import app


class RecipesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_list_recipes_is_stable_and_provider_neutral(self) -> None:
        response = self.client.get("/api/uv/recipes")
        self.assertEqual(response.status_code, 200, response.text)
        recipes = response.json()
        self.assertEqual(
            [item["recipe_id"] for item in recipes],
            [
                "general_video",
                "narrated_video",
                "music_video",
                "action_transfer",
                "digital_human",
                "story_video",
                "commercial_product",
                "photo_to_video",
                "visualizer",
                "performance_lip_sync",
                "free_project",
            ],
        )
        encoded = str(recipes).lower()
        for provider in ("dashscope", "openclaw", "qwen", "videoclaw", "kling", "seedance"):
            self.assertNotIn(provider, encoded)

    def test_get_general_video_recipe(self) -> None:
        response = self.client.get("/api/uv/recipes/general_video")
        self.assertEqual(response.status_code, 200, response.text)
        recipe = response.json()
        self.assertEqual(recipe["schema_version"], 1)
        self.assertEqual(recipe["recipe_id"], "general_video")
        self.assertEqual(recipe["production_policy"]["continuity"], "off")
        self.assertNotIn("speech.synthesize", recipe["required_capabilities"])
        self.assertNotIn("music", recipe["required_inputs"])
        self.assertNotIn("song", recipe["required_inputs"])

    def test_music_video_recipe_is_explicit_provider_neutral_mode(self) -> None:
        response = self.client.get("/api/uv/recipes/music_video")
        self.assertEqual(response.status_code, 200, response.text)
        recipe = response.json()
        self.assertEqual(recipe["required_inputs"], ["song"])
        self.assertEqual(recipe["required_capabilities"], ["timeline.assemble"])
        self.assertIn("media.understand", recipe["optional_capabilities"])
        self.assertEqual(recipe["production_policy"]["direction_gate"], "required")
        self.assertEqual(recipe["production_policy"]["sample_first"], "required")
        self.assertEqual(recipe["production_policy"]["plan_gate"], "required")
        self.assertEqual(recipe["production_policy"]["final_review"], "required")
        encoded = str(recipe).lower()
        for provider in ("videoclaw", "qwen", "dashscope", "kling", "seedance"):
            self.assertNotIn(provider, encoded)

    def test_specialized_recipe_exposes_production_policy(self) -> None:
        response = self.client.get("/api/uv/recipes/action_transfer")
        self.assertEqual(response.status_code, 200, response.text)
        recipe = response.json()
        self.assertEqual(recipe["production_policy"]["source_review"], "required")
        self.assertEqual(recipe["production_policy"]["sample_first"], "required")
        self.assertEqual(recipe["production_policy"]["final_review"], "required")

    def test_stage8_story_and_commercial_are_explicit_compositional_recipes(self) -> None:
        story_response = self.client.get("/api/uv/recipes/story_video")
        commercial_response = self.client.get("/api/uv/recipes/commercial_product")
        self.assertEqual(story_response.status_code, 200, story_response.text)
        self.assertEqual(commercial_response.status_code, 200, commercial_response.text)
        story = story_response.json()
        commercial = commercial_response.json()
        self.assertEqual(story["required_inputs"], ["brief"])
        self.assertEqual(story["required_capabilities"], ["timeline.assemble"])
        self.assertEqual(story["production_policy"]["scene_ledger"], "required")
        self.assertEqual(commercial["required_inputs"], ["brief"])
        self.assertIn("product_image", commercial["optional_inputs"])
        self.assertIn("product_video", commercial["optional_inputs"])
        self.assertEqual(commercial["production_policy"]["sample_first"], "required")

    def test_stage8_photo_and_visualizer_expose_deterministic_local_capabilities(self) -> None:
        photo_response = self.client.get("/api/uv/recipes/photo_to_video")
        visualizer_response = self.client.get("/api/uv/recipes/visualizer")
        self.assertEqual(photo_response.status_code, 200, photo_response.text)
        self.assertEqual(visualizer_response.status_code, 200, visualizer_response.text)
        photo = photo_response.json()
        visualizer = visualizer_response.json()
        self.assertEqual(photo["required_inputs"], ["images"])
        self.assertEqual(photo["required_capabilities"], ["video.compose_photos"])
        self.assertEqual(photo["production_policy"]["source_review"], "required")
        self.assertEqual(photo["production_policy"]["final_review"], "required")
        self.assertEqual(visualizer["required_inputs"], ["audio"])
        self.assertEqual(visualizer["required_capabilities"], ["audio.visualize"])
        self.assertIn("artwork", visualizer["optional_inputs"])
        self.assertIn("audio.analyze_music", visualizer["optional_capabilities"])

    def test_stage8_performance_and_free_project_do_not_claim_fake_pipeline(self) -> None:
        performance_response = self.client.get("/api/uv/recipes/performance_lip_sync")
        free_response = self.client.get("/api/uv/recipes/free_project")
        self.assertEqual(performance_response.status_code, 200, performance_response.text)
        self.assertEqual(free_response.status_code, 200, free_response.text)
        performance = performance_response.json()
        free_project = free_response.json()
        self.assertEqual(performance["required_inputs"], ["portrait", "speech"])
        self.assertEqual(performance["required_capabilities"], ["video.digital_human"])
        self.assertEqual(free_project["required_inputs"], [])
        self.assertEqual(free_project["required_capabilities"], [])
        encoded = str({"performance": performance, "free_project": free_project}).lower()
        for provider in ("videoclaw", "qwen", "dashscope", "kling", "seedance"):
            self.assertNotIn(provider, encoded)

    def test_unknown_recipe_is_404(self) -> None:
        response = self.client.get("/api/uv/recipes/unknown_recipe")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
