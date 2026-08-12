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
    ReplacementReviewError,
    ReplacementReviewObservation,
    ReplacementReviewStore,
    ReviewEvidenceReference,
    ReviewTarget,
)


class ReplacementReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Replacement reviews")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        self.briefs = RangeContinuityBriefStore(self.store)
        self.plans = ReplacementPlanStore(self.store)
        self.candidates = ReplacementCandidateStore(self.store)
        self.reviews = ReplacementReviewStore(self.store)
        self.briefs.upsert(self.project.project_id, self._brief())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _brief(
        self,
        *,
        suffix: str = "",
        include_targets: bool = True,
    ) -> RangeContinuityBrief:
        targets = (
            (
                ReviewTarget(
                    target_id="review_motion",
                    criterion=f"Replacement motion must remain continuous{suffix}.",
                    required=True,
                    evidence_ids=("requested",),
                ),
                ReviewTarget(
                    target_id="review_style",
                    criterion=f"Replacement style should remain coherent{suffix}.",
                    required=False,
                    evidence_ids=("requested",),
                ),
            )
            if include_targets
            else ()
        )
        return RangeContinuityBrief(
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
            review_targets=targets,
        )

    def _approve_plan(self, method_class: str = "prepared_asset") -> None:
        self.plans.approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class=method_class,
                goal="Prepare the reviewed replacement.",
                required_changes=("Apply the approved replacement.",),
            ),
        )

    def _artifact(self, artifact_id: str) -> ProjectReference:
        path = f"artifacts/{artifact_id}.mp4"
        (self.project_dir / path).write_bytes(b"candidate-video")
        reference = ProjectReference(id=artifact_id, kind="video", path=path)
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, reference),
        )
        return reference

    def _candidate(
        self,
        *,
        candidate_id: str = "cand_full",
        method_class: str = "prepared_asset",
        stage: str = "full",
    ) -> ProjectReference:
        self._approve_plan(method_class)
        reference = self._artifact(f"art_{candidate_id}")
        candidate = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id=candidate_id,
            edit_id="edit_1",
            stage=stage,
            artifact_id=reference.id,
            artifact_path=reference.path,
        )
        self.candidates.register(self.project.project_id, candidate)
        return reference

    def _observation(
        self,
        artifact_id: str,
        *,
        observation_id: str = "obs_candidate",
        include_candidate: bool = True,
        brief_evidence_id: str = "requested",
    ) -> ReplacementReviewObservation:
        evidence = [
            ReviewEvidenceReference(
                kind="brief_evidence",
                ref_id=brief_evidence_id,
            ),
        ]
        if include_candidate:
            evidence.append(
                ReviewEvidenceReference(
                    kind="candidate_artifact",
                    ref_id=artifact_id,
                )
            )
        return ReplacementReviewObservation(
            observation_id=observation_id,
            kind="observation",
            statement=(
                "The candidate remains continuous with the requested source context."
            ),
            confidence="high",
            evidence=tuple(evidence),
        )

    @staticmethod
    def _assessments(
        *,
        motion: str = "pass",
        style: str = "pass",
        observation_id: str = "obs_candidate",
    ) -> tuple[ReplacementReviewAssessment, ...]:
        return (
            ReplacementReviewAssessment(
                target_id="review_motion",
                outcome=motion,
                observation_ids=(observation_id,),
            ),
            ReplacementReviewAssessment(
                target_id="review_style",
                outcome=style,
                observation_ids=(observation_id,),
            ),
        )

    def _create_review(
        self,
        artifact_id: str,
        *,
        review_id: str = "review_1",
        verdict: str = "approved",
        motion: str = "pass",
        style: str = "pass",
    ):
        return self.reviews.create_review(
            self.project.project_id,
            review_id=review_id,
            candidate_id="cand_full",
            verdict=verdict,
            observations=(self._observation(artifact_id),),
            assessments=self._assessments(motion=motion, style=style),
        ).get(review_id)

    def test_approved_review_accepts_exact_candidate_artifact_and_range(self) -> None:
        reference = self._candidate()
        review = self._create_review(reference.id)

        self.assertEqual(review.candidate_id, "cand_full")
        self.assertEqual(
            review.target_identity,
            ("edit_1", "sources/source.mkv", 1_000_000, 2_000_000),
        )
        self.assertEqual(len(review.artifact_sha256), 64)
        self.assertFalse(
            (self.project_dir / "timeline" / "range-edits.json").exists()
        )
        self.assertTrue(
            (self.project_dir / "reviews" / "replacement-reviews.json").is_file()
        )

        accepted = self.reviews.accept_review(
            self.project.project_id,
            review.review_id,
        )
        self.assertEqual(len(accepted.edits), 1)
        edit = accepted.edits[0]
        self.assertEqual(edit.edit_id, "edit_1")
        self.assertEqual(edit.source_path, "sources/source.mkv")
        self.assertEqual((edit.start_us, edit.end_us), (1_000_000, 2_000_000))
        self.assertEqual(edit.replacement_path, reference.path)

    def test_review_requires_exact_current_brief_targets_and_candidate_grounding(self) -> None:
        reference = self._candidate()
        observation = self._observation(reference.id)

        with self.assertRaises(ReplacementReviewError) as missing_target:
            self.reviews.create_review(
                self.project.project_id,
                review_id="review_missing",
                candidate_id="cand_full",
                verdict="approved",
                observations=(observation,),
                assessments=(self._assessments()[0],),
            )
        self.assertIn(
            "exactly match current review targets",
            str(missing_target.exception),
        )

        with self.assertRaises(ReplacementReviewError) as no_candidate_evidence:
            self.reviews.create_review(
                self.project.project_id,
                review_id="review_context_only",
                candidate_id="cand_full",
                verdict="approved",
                observations=(
                    self._observation(reference.id, include_candidate=False),
                ),
                assessments=self._assessments(),
            )
        self.assertIn(
            "exact candidate artifact",
            str(no_candidate_evidence.exception),
        )

        with self.assertRaises(ReplacementReviewError) as unknown_evidence:
            self.reviews.create_review(
                self.project.project_id,
                review_id="review_unknown_evidence",
                candidate_id="cand_full",
                verdict="approved",
                observations=(
                    self._observation(
                        reference.id,
                        brief_evidence_id="missing_evidence",
                    ),
                ),
                assessments=self._assessments(),
            )
        self.assertIn(
            "unknown Brief evidence",
            str(unknown_evidence.exception),
        )

    def test_verdict_must_match_persisted_assessments(self) -> None:
        reference = self._candidate()

        with self.assertRaises(ReplacementReviewError):
            self._create_review(
                reference.id,
                review_id="bad_approved",
                verdict="approved",
                motion="fail",
            )
        with self.assertRaises(ReplacementReviewError):
            self._create_review(
                reference.id,
                review_id="bad_rejected",
                verdict="rejected",
            )
        with self.assertRaises(ReplacementReviewError):
            self._create_review(
                reference.id,
                review_id="bad_revision",
                verdict="needs_revision",
            )

        rejected = self._create_review(
            reference.id,
            review_id="review_rejected",
            verdict="rejected",
            motion="fail",
        )
        with self.assertRaises(ReplacementReviewError):
            self.reviews.accept_review(
                self.project.project_id,
                rejected.review_id,
            )
        self.assertFalse(
            (self.project_dir / "timeline" / "range-edits.json").exists()
        )

        needs_revision = self._create_review(
            reference.id,
            review_id="review_revision",
            verdict="needs_revision",
            style="uncertain",
        )
        with self.assertRaises(ReplacementReviewError):
            self.reviews.accept_review(
                self.project.project_id,
                needs_revision.review_id,
            )

    def test_plan_or_brief_revision_makes_review_stale_but_keeps_history_readable(self) -> None:
        reference = self._candidate()
        expected = self._create_review(reference.id)

        self.briefs.upsert(
            self.project.project_id,
            self._brief(suffix=" after revision"),
        )
        self._approve_plan()

        structural = self.reviews.load(self.project.project_id).get(
            expected.review_id
        )
        self.assertEqual(structural, expected)
        with self.assertRaises(ReplacementReviewError):
            self.reviews.validate_review(
                self.project.project_id,
                expected.review_id,
            )
        with self.assertRaises(ReplacementReviewError):
            self.reviews.accept_review(
                self.project.project_id,
                expected.review_id,
            )
        self.assertFalse(
            (self.project_dir / "timeline" / "range-edits.json").exists()
        )

    def test_candidate_artifact_byte_change_makes_review_stale_without_erasing_history(self) -> None:
        reference = self._candidate()
        expected = self._create_review(reference.id)
        artifact_path = self.project_dir / reference.path
        artifact_path.write_bytes(b"candidate-video-tampered-after-review")

        structural = self.reviews.load(self.project.project_id).get(
            expected.review_id
        )
        self.assertEqual(structural, expected)
        with self.assertRaises(ReplacementReviewError) as validation:
            self.reviews.validate_review(
                self.project.project_id,
                expected.review_id,
            )
        self.assertIn(
            "artifact bytes changed",
            str(validation.exception),
        )
        with self.assertRaises(ReplacementReviewError):
            self.reviews.accept_review(
                self.project.project_id,
                expected.review_id,
            )
        self.assertFalse(
            (self.project_dir / "timeline" / "range-edits.json").exists()
        )

    def test_final_review_rejects_sample_candidate(self) -> None:
        reference = self._candidate(
            candidate_id="cand_sample",
            method_class="generative_transform",
            stage="sample",
        )
        with self.assertRaises(ReplacementReviewError) as ctx:
            self.reviews.create_review(
                self.project.project_id,
                review_id="review_sample",
                candidate_id="cand_sample",
                verdict="approved",
                observations=(self._observation(reference.id),),
                assessments=self._assessments(),
            )
        self.assertIn("full candidate", str(ctx.exception))

    def test_final_review_requires_explicit_brief_review_targets(self) -> None:
        self.briefs.upsert(
            self.project.project_id,
            self._brief(include_targets=False),
        )
        reference = self._candidate()
        with self.assertRaises(ReplacementReviewError) as ctx:
            self.reviews.create_review(
                self.project.project_id,
                review_id="review_no_targets",
                candidate_id="cand_full",
                verdict="approved",
                observations=(self._observation(reference.id),),
                assessments=self._assessments(),
            )
        self.assertIn("at least one review target", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
