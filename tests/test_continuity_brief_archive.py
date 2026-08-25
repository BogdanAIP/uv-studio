from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    ContinuityEvidence,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    export_project,
    import_project,
)


class ContinuityBriefArchiveTests(unittest.TestCase):
    def test_export_import_and_fresh_reopen_preserve_pre_replacement_brief_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_store = ProjectStore(root / "source-projects")
            project = source_store.create_project(recipe_id="general_video",
                title="Brief archive",
                project_id="prj_brief",
            )
            project_dir = source_store.project_directory(project.project_id)
            (project_dir / "sources" / "source.mkv").write_bytes(b"source")

            expected = RangeContinuityBrief(
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
            )
            RangeContinuityBriefStore(source_store).upsert(
                project.project_id,
                expected,
            )

            archive = export_project(
                source_store,
                project.project_id,
                root / "brief.uvproj.zip",
            )
            target_root = root / "target-projects"
            imported = import_project(ProjectStore(target_root), archive)
            self.assertEqual(imported.project_id, project.project_id)

            fresh_store = ProjectStore(target_root)
            reopened = RangeContinuityBriefStore(fresh_store).validate_project(
                project.project_id
            )
            self.assertEqual(reopened.get("edit_1"), expected)
            imported_artifacts = target_root / project.project_id / "artifacts"
            self.assertEqual(list(imported_artifacts.glob("*.mkv")), [])


if __name__ == "__main__":
    unittest.main()
