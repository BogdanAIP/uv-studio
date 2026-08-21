from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.editor.targeted_edit_workflow import (
    TargetedEditWorkflowError,
    TargetedEditWorkflowService,
)
from uv_studio.projects.replacement_plan import ReplacementPlanStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore


class TargetedEditWorkflowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Targeted service", recipe_id="free_project")
        self.media = ProjectSourceMediaStore(self.store)
        self.service = TargetedEditWorkflowService(self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _add_video(self, filename: str, body: bytes) -> str:
        allocation = self.media.allocate(self.project.project_id, filename)
        allocation.absolute_path.write_bytes(body)
        project = self.media.register(
            self.project.project_id,
            allocation,
            media_kind="video",
            metadata={
                "original_name": filename,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
                "duration_us": 6_000_000,
                "width": 640,
                "height": 360,
            },
        )
        return next(item.id for item in project.sources if item.id == allocation.source_id)

    def test_failed_candidate_preparation_restores_hidden_plan_state(self) -> None:
        source_id = self._add_video("source.mp4", b"source")
        unsupported_replacement_id = self._add_video("replacement.txt", b"replacement")
        selected = self.service.select_target_range(
            self.project.project_id,
            source_id=source_id,
            start_us=1_000_000,
            end_us=3_000_000,
            change_request="Replace the selected interval.",
        )
        plans = ReplacementPlanStore(self.store)
        self.assertEqual(plans.load(self.project.project_id).plans, ())

        with self.assertRaisesRegex(TargetedEditWorkflowError, "unsupported video extension"):
            self.service.prepare_replacement(
                self.project.project_id,
                edit_id=selected["edit_id"],
                replacement_source_id=unsupported_replacement_id,
            )

        self.assertEqual(plans.load(self.project.project_id).plans, ())
        project = self.store.load_project(self.project.project_id)
        self.assertEqual(project.artifacts, ())


if __name__ == "__main__":
    unittest.main()
