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


class StoryOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Story", recipe_id="story_video")
        self.media = ProjectSourceMediaStore(self.store)
        self.recipes = build_builtin_registry()
        self.registry = CapabilityRegistry((), (), ())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _state(self):
        project = self.store.load_project(self.project.project_id)
        return project_workflow_state(
            project,
            self.recipes.get("story_video"),
            self.registry,
            self.media,
        )

    def _register_image(self):
        body = b"story-image-fixture"
        allocation = self.media.allocate(self.project.project_id, "story.png")
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

    def test_story_requires_saved_stage8_workspace(self) -> None:
        state = self._state()

        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertEqual(state.relevant_workspaces[0].workspace_id, "story_video")
        self.assertFalse(state.prerequisites[0].satisfied)
        self.assertEqual(state.next_actions, ())
        self.assertIsNone(state.current_outcome)
        self.assertIn(
            "story_final_render_not_authoritative",
            {item.code for item in state.diagnostics},
        )

    def test_saved_story_workspace_is_authoritative_preparation_state(self) -> None:
        image, _ = self._register_image()
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="История о путешествии",
            script="Герой уезжает и возвращается домой.",
            source_ids=[image.id],
        )

        state = self._state()

        self.assertEqual(state.readiness, WorkflowReadiness.READY)
        self.assertTrue(state.prerequisites[0].satisfied)
        self.assertEqual(state.next_actions, ())
        self.assertIsNone(state.current_outcome)
        self.assertIn("визуальных привязок: 1", state.relevant_workspaces[0].description)
        self.assertNotIn("workflow_not_migrated", {item.code for item in state.diagnostics})

    def test_tampered_story_source_fails_closed(self) -> None:
        image, path = self._register_image()
        save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="История с проверяемым кадром",
            script="",
            source_ids=[image.id],
        )
        path.write_bytes(b"tampered-story-image")

        state = self._state()

        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertFalse(state.prerequisites[0].satisfied)
        diagnostics = {item.code: item for item in state.diagnostics}
        self.assertIn("story_workspace_invalid", diagnostics)
        self.assertEqual(diagnostics["story_workspace_invalid"].severity, "error")
        self.assertEqual(state.next_actions, ())
        self.assertIsNone(state.current_outcome)


if __name__ == "__main__":
    unittest.main()
