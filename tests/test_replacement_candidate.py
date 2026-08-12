from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    ContinuityConstraint,
    ContinuityEvidence,
    ProjectReference,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementCandidateError,
    ReplacementCandidateStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
    ReviewTarget,
)


class ReplacementCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Candidates")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        self.briefs = RangeContinuityBriefStore(self.store)
        self.plans = ReplacementPlanStore(self.store)
        self.candidates = ReplacementCandidateStore(self.store)
        self.briefs.upsert(self.project.project_id, self._brief())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _brief(self, *, suffix: str = "") -> RangeContinuityBrief:
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
            constraints=(
                ContinuityConstraint(
                    constraint_id="keep_motion",
                    category="motion",
                    requirement=f"Keep motion{suffix}.",
                    evidence_ids=("requested",),
                ),
            ),
            review_targets=(
                ReviewTarget(
                    target_id="review_motion",
                    criterion="Check motion.",
                    required=True,
                    evidence_ids=("requested",),
                ),
            ),
        )

    def _approve_plan(self, method_class: str) -> None:
        self.plans.approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class=method_class,
                goal="Prepare a replacement.",
                required_changes=("Apply the approved change.",),
            ),
        )

    def _artifact(self, artifact_id: str, suffix: str = ".mp4") -> ProjectReference:
        path = f"artifacts/{artifact_id}{suffix}"
        (self.project_dir / path).write_bytes(b"candidate-bytes")
        ref = ProjectReference(id=artifact_id, kind="video", path=path)
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, ref),
        )
        return ref

    def test_candidate_inherits_current_plan_and_does_not_create_accepted_edit(self) -> None:
        self._approve_plan("prepared_asset")
        ref = self._artifact("art_candidate")
        candidate = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_1",
            edit_id="edit_1",
            stage="full",
            artifact_id=ref.id,
            artifact_path=ref.path,
        )
        state = self.candidates.register(self.project.project_id, candidate)

        self.assertEqual(state.get("cand_1"), candidate)
        self.assertEqual(candidate.method_class, "prepared_asset")
        self.assertEqual(candidate.target_identity, ("edit_1", "sources/source.mkv", 1_000_000, 2_000_000))
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

    def test_full_generative_candidate_requires_current_approved_sample(self) -> None:
        self._approve_plan("generative_transform")
        sample_ref = self._artifact("art_sample")
        full_ref = self._artifact("art_full")
        sample = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_sample",
            edit_id="edit_1",
            stage="sample",
            artifact_id=sample_ref.id,
            artifact_path=sample_ref.path,
            execution_run_id="run_sample",
        )
        self.candidates.register(self.project.project_id, sample)

        full = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_full",
            edit_id="edit_1",
            stage="full",
            artifact_id=full_ref.id,
            artifact_path=full_ref.path,
            execution_run_id="run_full",
        )
        with self.assertRaises(ReplacementCandidateError):
            self.candidates.register(self.project.project_id, full)

        approved = self.candidates.approve_sample(self.project.project_id, "cand_sample")
        self.assertEqual(approved.sample_approvals[0].candidate_id, "cand_sample")
        registered = self.candidates.register(self.project.project_id, full)
        self.assertEqual(registered.get("cand_full"), full)

    def test_plan_change_makes_old_candidate_and_sample_approval_stale(self) -> None:
        self._approve_plan("generative_transform")
        ref = self._artifact("art_sample")
        sample = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_sample",
            edit_id="edit_1",
            stage="sample",
            artifact_id=ref.id,
            artifact_path=ref.path,
        )
        self.candidates.register(self.project.project_id, sample)
        self.candidates.approve_sample(self.project.project_id, "cand_sample")

        self.briefs.upsert(self.project.project_id, self._brief(suffix=" after revision"))
        self._approve_plan("generative_transform")
        self.assertEqual(self.candidates.load(self.project.project_id).get("cand_sample"), sample)
        with self.assertRaises(ReplacementCandidateError) as ctx:
            self.candidates.validate_candidate(self.project.project_id, "cand_sample")
        self.assertIn("stale because its approved plan changed", str(ctx.exception))

    def test_candidate_requires_registered_nonempty_project_artifact(self) -> None:
        self._approve_plan("prepared_asset")
        missing = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_missing",
            edit_id="edit_1",
            stage="full",
            artifact_id="art_missing",
            artifact_path="artifacts/art_missing.mp4",
        )
        with self.assertRaises(ReplacementCandidateError):
            self.candidates.register(self.project.project_id, missing)

        empty_path = self.project_dir / "artifacts" / "art_empty.mp4"
        empty_path.write_bytes(b"")
        ref = ProjectReference(id="art_empty", kind="video", path="artifacts/art_empty.mp4")
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(self.project.project_id, artifacts=(*project.artifacts, ref))
        empty = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_empty",
            edit_id="edit_1",
            stage="full",
            artifact_id=ref.id,
            artifact_path=ref.path,
        )
        with self.assertRaises(ReplacementCandidateError):
            self.candidates.register(self.project.project_id, empty)

    def test_non_generative_sample_is_rejected(self) -> None:
        self._approve_plan("prepared_asset")
        ref = self._artifact("art_candidate")
        with self.assertRaises(ReplacementCandidateError):
            self.candidates.make_candidate(
                self.project.project_id,
                candidate_id="cand_sample",
                edit_id="edit_1",
                stage="sample",
                artifact_id=ref.id,
                artifact_path=ref.path,
            )


if __name__ == "__main__":
    unittest.main()
