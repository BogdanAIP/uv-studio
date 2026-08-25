from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    ContinuityEvidence,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
    export_project,
    import_project,
)


class ReplacementPlanArchiveTests(unittest.TestCase):
    def test_pre_replacement_plan_survives_archive_and_fresh_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_store = ProjectStore(root / "source-projects")
            project = source_store.create_project(recipe_id="general_video",
                title="Plan archive",
                project_id="prj_plan",
            )
            project_dir = source_store.project_directory(project.project_id)
            (project_dir / "sources" / "source.mkv").write_bytes(b"source")
            RangeContinuityBriefStore(source_store).upsert(
                project.project_id,
                RangeContinuityBrief(
                    edit_id="edit_1",
                    source_path="sources/source.mkv",
                    start_us=1_000_000,
                    end_us=2_000_000,
                    evidence=(
                        ContinuityEvidence(
                            evidence_id="requested",
                            role="requested",
                            path="sources/source.mkv",
                            source_start_us=1_000_000,
                            source_end_us=2_000_000,
                        ),
                    ),
                ),
            )
            expected = ReplacementPlanStore(source_store).approve(
                project.project_id,
                ReplacementPlanProposal(
                    edit_id="edit_1",
                    method_class="generative_transform",
                    goal="Replace the object without changing camera continuity.",
                    required_changes=("Replace the unwanted object.",),
                    forbidden_changes=("Do not change camera motion.",),
                    audio_strategy="preserve_source",
                ),
            ).get("edit_1")

            self.assertEqual(list((project_dir / "artifacts").iterdir()), [])
            archive = export_project(
                source_store,
                project.project_id,
                root / "plan.uvproj.zip",
            )
            target_root = root / "target-projects"
            imported = import_project(ProjectStore(target_root), archive)
            self.assertEqual(imported.project_id, project.project_id)

            fresh_store = ProjectStore(target_root)
            reopened = ReplacementPlanStore(fresh_store).validate_project(project.project_id)
            self.assertEqual(reopened.get("edit_1"), expected)
            self.assertEqual(
                list((target_root / project.project_id / "artifacts").iterdir()),
                [],
            )


if __name__ == "__main__":
    unittest.main()
