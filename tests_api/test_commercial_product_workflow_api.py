from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import CapabilityRegistry
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import save_stage8_workspace
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class CommercialProductWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Commercial API",
            recipe_id="commercial_product",
        )
        self.registry = CapabilityRegistry((), (), ())
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        self.client = TestClient(app)
        self.media = ProjectSourceMediaStore(self.store)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/workflow"

    def _add_image(self):
        body = b"commercial-api-product-image"
        allocation = self.media.allocate(self.project.project_id, "product.png")
        allocation.absolute_path.write_bytes(body)
        updated = self.media.register(
            self.project.project_id,
            allocation,
            media_kind="image",
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        reference = next(item for item in updated.sources if item.id == allocation.source_id)
        return reference, allocation.absolute_path

    def test_api_projects_missing_commercial_preparation(self) -> None:
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["recipe_id"], "commercial_product")
        self.assertEqual(state["readiness"], "setup_required")
        self.assertEqual(
            [item["workspace_id"] for item in state["relevant_workspaces"]],
            ["commercial_product"],
        )
        self.assertEqual(state["next_actions"], [])
        self.assertIsNone(state["current_outcome"])
        codes = {item["code"] for item in state["diagnostics"]}
        self.assertNotIn("workflow_not_migrated", codes)
        self.assertIn("commercial_required_gates_not_authoritative", codes)
        self.assertIn("commercial_final_render_not_authoritative", codes)

    def test_api_projects_verified_product_preparation(self) -> None:
        image, _ = self._add_image()
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Показать новую упаковку продукта",
            script="Крупный план продукта и ключевое преимущество.",
            source_ids=[image.id],
        )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "ready")
        self.assertEqual([item["satisfied"] for item in state["prerequisites"]], [True, True])
        self.assertEqual(state["next_actions"], [])
        self.assertIsNone(state["current_outcome"])

    def test_api_fails_closed_after_product_bytes_change(self) -> None:
        image, path = self._add_image()
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Проверить идентичность продукта",
            script="",
            source_ids=[image.id],
        )
        path.write_bytes(b"tampered-commercial-api-product-image")

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertEqual([item["satisfied"] for item in state["prerequisites"]], [False, False])
        diagnostics = {item["code"]: item for item in state["diagnostics"]}
        self.assertIn("commercial_workspace_invalid", diagnostics)
        self.assertEqual(diagnostics["commercial_workspace_invalid"]["severity"], "error")


if __name__ == "__main__":
    unittest.main()
