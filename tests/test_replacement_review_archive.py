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
    ReplacementReviewAssessment,
    ReplacementReviewObservation,
    ReplacementReviewStore,
    ReviewEvidenceReference,
    ReviewTarget,
    export_project,
    import_project,
)


class ReplacementReviewArchiveTests(unittest.TestCase):
    def test_review_history_and_candidate_survive_archive_before_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_store = ProjectStore(root / "source-projects")
            project = source_store.create_project(title="Review archive", project_id="prj_review")
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
                    review_targets=(
                        ReviewTarget(
                            target_id="review_motion",
                            criterion="Check continuity.",
                            required=True,
                            evidence_ids=("requested",),
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
                    required_changes=("Use replacement.",),
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
            candidate = candidates.make_candidate(
                project.project_id,
                candidate_id="cand_1",
                edit_id="edit_1",
                stage="full",
                artifact_id=reference.id,
                artifact_path=reference.path,
            )
            candidates.register(project.project_id, candidate)
            reviews = ReplacementReviewStore(source_store)
            expected = reviews.create_review(
                project.project_id,
                review_id="review_1",
                candidate_id="cand_1",
                verdict="approved",
                observations=(
                    ReplacementReviewObservation(
                        observation_id="obs_candidate",
                        kind="observation",
                        statement="Candidate matches the required continuity target.",
                        confidence="high",
                        evidence=(
                            ReviewEvidenceReference(
                                kind="brief_evidence",
                                ref_id="requested",
                            ),
                            ReviewEvidenceReference(
                                kind="candidate_artifact",
                                ref_id=reference.id,
                            ),
                        ),
                    ),
                ),
                assessments=(
                    ReplacementReviewAssessment(
                        target_id="review_motion",
                        outcome="pass",
                        observation_ids=("obs_candidate",),
                    ),
                ),
            ).get("review_1")
            self.assertFalse((project_dir / "timeline" / "range-edits.json").exists())

            archive = export_project(
                source_store,
                project.project_id,
                root / "review.uvproj.zip",
            )
            target_root = root / "target-projects"
            import_project(ProjectStore(target_root), archive)
            fresh_store = ProjectStore(target_root)
            reopened = ReplacementReviewStore(fresh_store).validate_review(
                project.project_id,
                "review_1",
            )
            self.assertEqual(reopened, expected)
            self.assertTrue((target_root / project.project_id / candidate.artifact_path).is_file())
            self.assertFalse((target_root / project.project_id / "timeline" / "range-edits.json").exists())


if __name__ == "__main__":
    unittest.main()
