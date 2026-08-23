from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities import CapabilityRegistry
from uv_studio.orchestration import WorkflowReadiness, project_workflow_state
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import save_stage8_workspace
from uv_studio.projects.store import ProjectStore
from uv_studio.recipes import build_builtin_registry


class CommercialProductOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Product", recipe_id="commercial_product")
        self.media = ProjectSourceMediaStore(self.store)
        self.recipes = build_builtin_registry()
        self.registry = CapabilityRegistry((), (), ())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _state(self):
        project = self.store.load_project(self.project.project_id)
        return project_workflow_state(
            project,
            self.recipes.get("commercial_product"),
            self.registry,
            self.media,
        )

    def _register(self, *, kind: str = "image", body: bytes = b"product-image-fixture"):
        suffix = "png" if kind == "image" else "wav"
        allocation = self.media.allocate(self.project.project_id, f"product.{suffix}")
        allocation.absolute_path.write_bytes(body)
        updated = self.media.register(
            self.project.project_id,
            allocation,
            media_kind=kind,
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        reference = next(item for item in updated.sources if item.id == allocation.source_id)
        return reference, allocation.absolute_path

    def test_commercial_requires_workspace_and_product_visual(self) -> None:
        state = self._state()
        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertEqual(state.relevant_workspaces[0].workspace_id, "commercial_product")
        self.assertEqual([item.satisfied for item in state.prerequisites], [False, False])
        self.assertEqual(state.next_actions, ())
        self.assertIsNone(state.current_outcome)
        codes = {item.code for item in state.diagnostics}
        self.assertIn("commercial_required_gates_not_authoritative", codes)
        self.assertIn("commercial_final_render_not_authoritative", codes)

    def test_text_only_workspace_does_not_claim_product_identity(self) -> None:
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Ролик о новой упаковке",
            script="Показать форму, логотип и ключевое преимущество.",
            source_ids=[],
        )
        state = self._state()
        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertTrue(state.prerequisites[0].satisfied)
        self.assertFalse(state.prerequisites[1].satisfied)

    def test_verified_product_visual_reaches_preparation_ready(self) -> None:
        image, _ = self._register()
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Ролик о новой упаковке",
            script="Показать форму, логотип и ключевое преимущество.",
            source_ids=[image.id],
        )
        state = self._state()
        self.assertEqual(state.readiness, WorkflowReadiness.READY)
        self.assertEqual([item.satisfied for item in state.prerequisites], [True, True])
        self.assertEqual(state.next_actions, ())
        self.assertIsNone(state.current_outcome)
        self.assertIn("продуктовых image/video: 1", state.relevant_workspaces[0].description)
        self.assertNotIn("workflow_not_migrated", {item.code for item in state.diagnostics})

    def test_audio_only_workspace_is_not_product_reference(self) -> None:
        audio, _ = self._register(kind="audio", body=b"product-audio")
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Реклама продукта с музыкой",
            script="",
            source_ids=[audio.id],
        )
        state = self._state()
        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertTrue(state.prerequisites[0].satisfied)
        self.assertFalse(state.prerequisites[1].satisfied)

    def test_tampered_product_visual_fails_closed(self) -> None:
        image, path = self._register()
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Проверяемый продуктовый референс",
            script="",
            source_ids=[image.id],
        )
        path.write_bytes(b"tampered-product-image")
        state = self._state()
        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertFalse(state.prerequisites[0].satisfied)
        self.assertFalse(state.prerequisites[1].satisfied)
        diagnostics = {item.code: item for item in state.diagnostics}
        self.assertIn("commercial_workspace_invalid", diagnostics)
        self.assertEqual(diagnostics["commercial_workspace_invalid"].severity, "error")
        self.assertEqual(state.next_actions, ())
        self.assertIsNone(state.current_outcome)


if __name__ == "__main__":
    unittest.main()
