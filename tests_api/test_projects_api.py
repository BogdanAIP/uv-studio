from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ProjectsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.project_root)
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_upstream_health_route_remains_available(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_create_list_get_and_update_project(self) -> None:
        create = self.client.post(
            "/api/uv/projects",
            json={
                "title": "API Project",
                "recipe_id": "general_video",
                "settings": {"aspect_ratio": "16:9"},
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created = create.json()
        project_id = created["project_id"]
        self.assertEqual(created["schema_version"], 2)
        self.assertEqual(created["recipe_id"], "general_video")
        self.assertEqual(created["title"], "API Project")

        listed = self.client.get("/api/uv/projects")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["project_id"] for item in listed.json()], [project_id])

        fetched = self.client.get(f"/api/uv/projects/{project_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["settings"]["aspect_ratio"], "16:9")

        updated = self.client.patch(
            f"/api/uv/projects/{project_id}",
            json={"title": "Updated API Project", "extensions": {"demo": {"enabled": True}}},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Updated API Project")

        fresh_store = ProjectStore(self.project_root)
        persisted = fresh_store.load_project(project_id)
        self.assertEqual(persisted.title, "Updated API Project")
        self.assertTrue(persisted.extensions["demo"]["enabled"])

    def test_create_rejects_nonfinite_nested_project_state(self) -> None:
        response = self.client.post(
            "/api/uv/projects",
            content='{"title":"Bad JSON","recipe_id":"general_video","settings":{"nested":{"value":NaN}}}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(list(self.project_root.iterdir()), [])

    def test_list_projects_skips_corrupt_project_without_changing_response_shape(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Healthy A", project_id="prj_api_healthy_a")
        self.store.create_project(recipe_id="general_video", title="Broken", project_id="prj_api_corrupt")
        self.store.create_project(recipe_id="general_video", title="Healthy B", project_id="prj_api_healthy_b")
        corrupt_path = self.store.project_path("prj_api_corrupt")
        corrupt_bytes = b"{broken-json\n"
        corrupt_path.write_bytes(corrupt_bytes)

        response = self.client.get("/api/uv/projects")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertEqual(
            {item["project_id"] for item in payload},
            {"prj_api_healthy_a", "prj_api_healthy_b"},
        )
        self.assertEqual(corrupt_path.read_bytes(), corrupt_bytes)
        _projects, diagnostics = self.store.list_projects_with_diagnostics()
        self.assertEqual([item.project_id for item in diagnostics], ["prj_api_corrupt"])

    def test_archive_export_and_import_round_trip(self) -> None:
        created = self.client.post(
            "/api/uv/projects",
            json={"recipe_id": "general_video", "title": "Archive API", "settings": {"quality": "preview"}},
        ).json()
        project_id = created["project_id"]
        source_file = self.store.project_path(project_id).parent / "sources" / "input.txt"
        source_file.write_text("portable source", encoding="utf-8")

        exported = self.client.get(f"/api/uv/projects/{project_id}/archive")
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(exported.headers["content-type"], "application/zip")
        self.assertIn(".uvproj.zip", exported.headers.get("content-disposition", ""))
        archive_bytes = exported.content
        self.assertGreater(len(archive_bytes), 0)

        target_store = ProjectStore(Path(self.tmp.name) / "imported-projects")
        app.dependency_overrides[get_project_store] = lambda: target_store
        imported = self.client.post(
            "/api/uv/projects/import",
            content=archive_bytes,
            headers={"Content-Type": "application/zip"},
        )
        self.assertEqual(imported.status_code, 201, imported.text)
        self.assertEqual(imported.json()["project_id"], project_id)
        self.assertEqual(imported.json()["title"], "Archive API")
        self.assertEqual(
            (target_store.project_path(project_id).parent / "sources" / "input.txt").read_text(
                encoding="utf-8"
            ),
            "portable source",
        )

        duplicate = self.client.post(
            "/api/uv/projects/import",
            content=archive_bytes,
            headers={"Content-Type": "application/zip"},
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_invalid_archive_is_422_and_empty_archive_is_400(self) -> None:
        invalid = self.client.post(
            "/api/uv/projects/import",
            content=b"not-a-zip",
            headers={"Content-Type": "application/zip"},
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)

        empty = self.client.post(
            "/api/uv/projects/import",
            content=b"",
            headers={"Content-Type": "application/zip"},
        )
        self.assertEqual(empty.status_code, 400, empty.text)

    def test_missing_project_is_404(self) -> None:
        response = self.client.get("/api/uv/projects/prj_missing")
        self.assertEqual(response.status_code, 404)

    def test_invalid_project_id_is_422(self) -> None:
        response = self.client.get("/api/uv/projects/bad$id")
        self.assertEqual(response.status_code, 422)

    def test_invalid_recipe_is_422(self) -> None:
        response = self.client.post(
            "/api/uv/projects",
            json={"title": "Bad Recipe", "recipe_id": "../escape"},
        )
        self.assertEqual(response.status_code, 422)

    def test_update_rejects_explicit_null(self) -> None:
        created = self.client.post("/api/uv/projects", json={"recipe_id": "general_video", "title": "Null Test"}).json()
        response = self.client.patch(
            f"/api/uv/projects/{created['project_id']}",
            json={"title": None},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
