from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.sequence_continuity import (
    SEQUENCE_CONTINUITY_PATH,
    SequenceContinuityError,
    SequenceContinuityRule,
    SequenceContinuityStore,
    SequenceObservation,
    SequenceReviewResult,
    SequenceReviewTarget,
)
from uv_studio.projects.store import ProjectStore


class SequenceContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Sequence continuity")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.continuity = SequenceContinuityStore(self.store)
        self.source_a = self._register_video("src_a", "a.mp4", b"anchor-video", 4_000_000)
        self.source_b = self._register_video("src_b", "b.mp4", b"candidate-video", 3_000_000)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _register_video(
        self,
        reference_id: str,
        filename: str,
        payload: bytes,
        duration_us: int,
    ) -> ProjectReference:
        path = self.project_dir / "sources" / filename
        path.write_bytes(payload)
        reference = ProjectReference(
            id=reference_id,
            kind="video",
            path=f"sources/{filename}",
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": duration_us,
            },
        )
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            sources=(*project.sources, reference),
        )
        return reference

    def _first_plan(self):
        sequence = self.continuity.create_sequence(
            self.project.project_id,
            sequence_id="seq_main",
            title="Linked shots",
        )
        self.assertEqual(sequence.anchor_take_id, None)
        return self.continuity.upsert_plan(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_01",
            order=0,
            intent="Establish the subject in a static wide shot.",
            anchor_take_id=None,
            locks=(
                SequenceContinuityRule(
                    rule_id="lock_subject",
                    category="content",
                    requirement="Keep the same subject identity.",
                ),
            ),
            allowed_changes=(
                SequenceContinuityRule(
                    rule_id="allow_pose",
                    category="visual",
                    requirement="Pose may change between shots.",
                ),
            ),
            review_targets=(
                SequenceReviewTarget(
                    target_id="target_subject",
                    criterion="Subject identity is visually consistent.",
                    required=True,
                ),
            ),
        )

    def _accept_first_take(self):
        plan = self._first_plan()
        take = self.continuity.register_take(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id=plan.shot_id,
            reference_id=self.source_a.id,
            take_id="take_01",
        )
        review = self.continuity.review_take(
            self.project.project_id,
            sequence_id="seq_main",
            take_id=take.take_id,
            verdict="approved",
            results=(
                SequenceReviewResult(
                    target_id="target_subject",
                    outcome="pass",
                    note="Manual review confirmed identity.",
                ),
            ),
            observations=(
                SequenceObservation(
                    observation_id="obs_subject",
                    kind="observation",
                    category="content",
                    statement="Subject exits frame looking screen-right.",
                    confidence="high",
                ),
            ),
        )
        accepted = self.continuity.accept_take(
            self.project.project_id,
            sequence_id="seq_main",
            review_id=review.review_id,
        )
        self.assertEqual(accepted.status, "accepted")
        return self.continuity.reanchor(
            self.project.project_id,
            sequence_id="seq_main",
            take_id=accepted.take_id,
        )

    def test_standalone_project_has_no_sequence_state_until_opted_in(self) -> None:
        state = self.continuity.load(self.project.project_id)
        self.assertEqual(state.sequences, ())
        self.assertFalse((self.project_dir / SEQUENCE_CONTINUITY_PATH).exists())

    def test_accept_reanchor_and_link_next_shot_with_bounded_context(self) -> None:
        sequence = self._accept_first_take()
        self.assertEqual(sequence.anchor_take_id, "take_01")

        plan_2 = self.continuity.upsert_plan(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_02",
            order=1,
            intent="Continue from the accepted exit direction into a closer shot.",
            anchor_take_id="take_01",
            locks=(
                SequenceContinuityRule(
                    rule_id="lock_direction",
                    category="motion",
                    requirement="Preserve the accepted screen-right movement direction.",
                ),
            ),
            allowed_changes=(
                SequenceContinuityRule(
                    rule_id="allow_scale",
                    category="visual",
                    requirement="Camera framing may move to a closer shot.",
                ),
            ),
            review_targets=(
                SequenceReviewTarget(
                    target_id="target_direction",
                    criterion="Entry direction continues the accepted anchor.",
                    required=True,
                ),
            ),
        )
        self.assertEqual(plan_2.anchor_take_id, "take_01")
        take_2 = self.continuity.register_take(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_02",
            reference_id=self.source_b.id,
            take_id="take_02",
        )
        context = self.continuity.timeline_context(
            self.project.project_id,
            sequence_id="seq_main",
            take_id=take_2.take_id,
            window_us=1_000_000,
            samples=3,
        )
        self.assertEqual(context["anchor"]["take_id"], "take_01")
        self.assertEqual(context["anchor"]["sample_times_us"], [3_000_000, 3_500_000, 4_000_000])
        self.assertEqual(context["candidate"]["sample_times_us"], [0, 500_000, 1_000_000])
        self.assertEqual(context["locks"][0]["rule_id"], "lock_direction")

        review_2 = self.continuity.review_take(
            self.project.project_id,
            sequence_id="seq_main",
            take_id="take_02",
            verdict="approved",
            results=(
                SequenceReviewResult(
                    target_id="target_direction",
                    outcome="pass",
                ),
            ),
            observations=(
                SequenceObservation(
                    observation_id="obs_entry",
                    kind="observation",
                    category="motion",
                    statement="Candidate enters with matching screen direction.",
                    confidence="high",
                ),
            ),
        )
        accepted_2 = self.continuity.accept_take(
            self.project.project_id,
            sequence_id="seq_main",
            review_id=review_2.review_id,
        )
        self.assertEqual(accepted_2.status, "accepted")
        final = self.continuity.reanchor(
            self.project.project_id,
            sequence_id="seq_main",
            take_id="take_02",
        )
        self.assertEqual(final.anchor_take_id, "take_02")

        reloaded = self.continuity.load(self.project.project_id, validate_current=True)
        current = reloaded.sequence("seq_main")
        self.assertEqual(current.plan("shot_02").intent, plan_2.intent)
        self.assertEqual(current.take("take_02").status, "accepted")
        self.assertEqual(current.review(review_2.review_id).observations[0].statement,
                         "Candidate enters with matching screen direction.")

    def test_required_review_target_must_pass_before_approval(self) -> None:
        self._first_plan()
        self.continuity.register_take(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_01",
            reference_id=self.source_a.id,
            take_id="take_01",
        )
        with self.assertRaises(SequenceContinuityError) as ctx:
            self.continuity.review_take(
                self.project.project_id,
                sequence_id="seq_main",
                take_id="take_01",
                verdict="approved",
                results=(SequenceReviewResult(target_id="target_subject", outcome="uncertain"),),
            )
        self.assertIn("requires pass", str(ctx.exception))

    def test_plan_revision_invalidates_prepared_take_review(self) -> None:
        self._first_plan()
        self.continuity.register_take(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_01",
            reference_id=self.source_a.id,
            take_id="take_01",
        )
        self.continuity.upsert_plan(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_01",
            order=0,
            intent="Changed plan that requires a new take.",
            anchor_take_id=None,
            locks=(),
            allowed_changes=(),
            review_targets=(
                SequenceReviewTarget(
                    target_id="target_subject",
                    criterion="Subject remains consistent.",
                    required=True,
                ),
            ),
        )
        with self.assertRaises(SequenceContinuityError) as ctx:
            self.continuity.review_take(
                self.project.project_id,
                sequence_id="seq_main",
                take_id="take_01",
                verdict="approved",
                results=(SequenceReviewResult(target_id="target_subject", outcome="pass"),),
            )
        self.assertIn("older shot plan", str(ctx.exception))

    def test_current_bytes_are_revalidated_before_review_and_anchor_use(self) -> None:
        self._first_plan()
        self.continuity.register_take(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_01",
            reference_id=self.source_a.id,
            take_id="take_01",
        )
        (self.project_dir / self.source_a.path).write_bytes(b"mutated-after-registration")
        with self.assertRaises(SequenceContinuityError):
            self.continuity.review_take(
                self.project.project_id,
                sequence_id="seq_main",
                take_id="take_01",
                verdict="approved",
                results=(SequenceReviewResult(target_id="target_subject", outcome="pass"),),
            )

    def test_rejected_take_cannot_be_accepted_or_reanchored(self) -> None:
        self._first_plan()
        self.continuity.register_take(
            self.project.project_id,
            sequence_id="seq_main",
            shot_id="shot_01",
            reference_id=self.source_a.id,
            take_id="take_01",
        )
        review = self.continuity.review_take(
            self.project.project_id,
            sequence_id="seq_main",
            take_id="take_01",
            verdict="rejected",
            results=(SequenceReviewResult(target_id="target_subject", outcome="fail"),),
        )
        with self.assertRaises(SequenceContinuityError):
            self.continuity.accept_take(
                self.project.project_id,
                sequence_id="seq_main",
                review_id=review.review_id,
            )
        with self.assertRaises(SequenceContinuityError):
            self.continuity.reanchor(
                self.project.project_id,
                sequence_id="seq_main",
                take_id="take_01",
            )


if __name__ == "__main__":
    unittest.main()
