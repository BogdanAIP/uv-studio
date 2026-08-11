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
            ["general_video", "narrated_video", "action_transfer", "digital_human"],
        )
        encoded = str(recipes).lower()
        self.assertNotIn("dashscope", encoded)
        self.assertNotIn("openclaw", encoded)
        self.assertNotIn("qwen", encoded)
        self.assertNotIn("videoclaw", encoded)

    def test_get_general_video_recipe(self) -> None:
        response = self.client.get("/api/uv/recipes/general_video")
        self.assertEqual(response.status_code, 200, response.text)
        recipe = response.json()
        self.assertEqual(recipe["schema_version"], 1)
        self.assertEqual(recipe["recipe_id"], "general_video")
        self.assertEqual(recipe["production_policy"]["continuity"], "off")
        self.assertNotIn("speech.synthesize", recipe["required_capabilities"])
        self.assertNotIn("music", recipe["required_inputs"])

    def test_specialized_recipe_exposes_production_policy(self) -> None:
        response = self.client.get("/api/uv/recipes/action_transfer")
        self.assertEqual(response.status_code, 200, response.text)
        recipe = response.json()
        self.assertEqual(recipe["production_policy"]["source_review"], "required")
        self.assertEqual(recipe["production_policy"]["sample_first"], "required")
        self.assertEqual(recipe["production_policy"]["final_review"], "required")

    def test_unknown_recipe_is_404(self) -> None:
        response = self.client.get("/api/uv/recipes/unknown_recipe")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
