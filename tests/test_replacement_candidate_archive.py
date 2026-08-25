from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    ContinuityEvidence,
    ProjectReference,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementCandidateStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
    export_project,
    import_project,
)


class ReplacementCandidateArchiveTests(unittest.TestCase):
    def test_candidate_and_artifact_survive_archive_without_accepted_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_store = ProjectStore(root / "source-projects")
            project = source_store.create_project(recipe_id="general_video", title="Candidate archive", project_id="prj_candidate")
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
            ReplacementPlanStore(source_store).approve(
                project.project_id,
                ReplacementPlanProposal(
                    edit_id="edit_1",
                    method_class="prepared_asset",
                    goal="Use prepared candidate.",
                    required_changes=("Use the prepared replacement.",),
                ),
            )
            artifact_path = project_dir / "artifacts" / "art_candidate.mp4"
            artifact_path.write_bytes(b"video-candidate")
            reference = ProjectReference(
                id="art_candidate",
                kind="video",
                path="artifacts/art_candidate.mp4",
            )
            current = source_store.load_project(project.project_id)
            source_store.update_project(
                project.project_id,
                artifacts=(*current.artifacts, reference),
            )
            candidates = ReplacementCandidateStore(source_store)
            expected = candidates.make_candidate(
                project.project_id,
                candidate_id="cand_1",
                edit_id="edit_1",
                stage="full",
                artifact_id=reference.id,
                artifact_path=reference.path,
            )
            candidates.register(project.project_id, expected)
            self.assertFalse((project_dir / "timeline" / "range-edits.json").exists())

            archive = export_project(
                source_store,
                project.project_id,
                root / "candidate.uvproj.zip",
            )
            target_root = root / "target-projects"
            import_project(ProjectStore(target_root), archive)
            fresh_store = ProjectStore(target_root)
            reopened = ReplacementCandidateStore(fresh_store).validate_candidate(
                project.project_id,
                "cand_1",
            )
            self.assertEqual(reopened, expected)
            self.assertTrue((target_root / project.project_id / expected.artifact_path).is_file())
            self.assertFalse((target_root / project.project_id / "timeline" / "range-edits.json").exists())


if __name__ == "__main__":
    unittest.main()
