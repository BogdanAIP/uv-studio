from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from uv_studio.server import app


class RecipesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_recipe_catalog_route_is_retired(self) -> None:
        response = self.client.get("/api/uv/recipes")
        self.assertEqual(response.status_code, 404, response.text)

    def test_recipe_item_route_is_retired(self) -> None:
        response = self.client.get("/api/uv/recipes/general_video")
        self.assertEqual(response.status_code, 404, response.text)

    def test_openapi_does_not_advertise_recipe_catalog(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200, response.text)
        paths = response.json()["paths"]
        self.assertNotIn("/api/uv/recipes", paths)
        self.assertFalse(any(path.startswith("/api/uv/recipes/") for path in paths))


if __name__ == "__main__":
    unittest.main()
