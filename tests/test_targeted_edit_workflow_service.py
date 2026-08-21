from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uv_studio.editor.targeted_edit_workflow import (
    TargetedEditWorkflowError,
    TargetedEditWorkflowService,
)
from uv_studio.projects.replacement_candidate import ReplacementCandidateError
from uv_studio.projects.replacement_plan import ReplacementPlanProposal, ReplacementPlanStore
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

    def _select_edit(self, source_id: str) -> dict:
        return self.service.select_target_range(
            self.project.project_id,
            source_id=source_id,
            start_us=1_000_000,
            end_us=3_000_000,
            change_request="Replace the selected interval.",
        )

    def _approve_distinct_plan(self, edit_id: str, *, goal: str):
        plans = ReplacementPlanStore(self.store)
        state = plans.approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id=edit_id,
                method_class="deterministic_edit",
                goal=goal,
                required_changes=(goal,),
                allowed_changes=(),
                forbidden_changes=(),
                audio_strategy="preserve_source",
            ),
        )
        return state.get(edit_id)

    def test_failed_candidate_preparation_restores_exact_previous_plan(self) -> None:
        source_id = self._add_video("source.mp4", b"source")
        unsupported_replacement_id = self._add_video("replacement.txt", b"replacement")
        selected = self._select_edit(source_id)
        previous_plan = self._approve_distinct_plan(
            selected["edit_id"],
            goal="Preserve the previously approved deterministic plan.",
        )

        with self.assertRaisesRegex(TargetedEditWorkflowError, "unsupported video extension"):
            self.service.prepare_replacement(
                self.project.project_id,
                edit_id=selected["edit_id"],
                replacement_source_id=unsupported_replacement_id,
            )

        restored = ReplacementPlanStore(self.store).load(self.project.project_id).get(selected["edit_id"])
        self.assertEqual(restored, previous_plan)
        project = self.store.load_project(self.project.project_id)
        self.assertEqual(project.artifacts, ())

    def test_failed_candidate_does_not_overwrite_concurrent_plan_change(self) -> None:
        source_id = self._add_video("source.mp4", b"source")
        replacement_id = self._add_video("replacement.mp4", b"replacement")
        selected = self._select_edit(source_id)
        real_copyfile = shutil.copyfile
        concurrent_goal = "Concurrent plan must survive failed candidate registration."

        def copy_then_change_plan(source: Path, destination: Path):
            result = real_copyfile(source, destination)
            self._approve_distinct_plan(selected["edit_id"], goal=concurrent_goal)
            return result

        with patch(
            "uv_studio.editor.targeted_edit_workflow.shutil.copyfile",
            side_effect=copy_then_change_plan,
        ):
            with self.assertRaises(ReplacementCandidateError):
                self.service.prepare_replacement(
                    self.project.project_id,
                    edit_id=selected["edit_id"],
                    replacement_source_id=replacement_id,
                )

        current = ReplacementPlanStore(self.store).load(self.project.project_id).get(selected["edit_id"])
        self.assertEqual(current.goal, concurrent_goal)
        project = self.store.load_project(self.project.project_id)
        self.assertEqual(project.artifacts, ())


if __name__ == "__main__":
    unittest.main()
