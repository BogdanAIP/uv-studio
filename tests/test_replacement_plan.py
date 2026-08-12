from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    ContinuityConstraint,
    ContinuityEvidence,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementPlan,
    ReplacementPlanError,
    ReplacementPlanProposal,
    ReplacementPlanState,
    ReplacementPlanStore,
    ReviewTarget,
)


class ReplacementPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Replacement plan")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.source.write_bytes(b"source")
        self.briefs = RangeContinuityBriefStore(self.store)
        self.plans = ReplacementPlanStore(self.store)
        self.briefs.upsert(self.project.project_id, self._brief())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _brief(self, *, goal_suffix: str = "") -> RangeContinuityBrief:
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
                    requirement=f"Preserve boundary motion{goal_suffix}.",
                    evidence_ids=("requested",),
                ),
            ),
            review_targets=(
                ReviewTarget(
                    target_id="review_motion",
                    criterion="Verify boundary motion continuity.",
                    required=True,
                    evidence_ids=("requested",),
                ),
            ),
        )

    def _proposal(
        self,
        *,
        method_class: str = "deterministic_edit",
        audio_strategy: str = "preserve_source",
    ) -> ReplacementPlanProposal:
        return ReplacementPlanProposal(
            edit_id="edit_1",
            method_class=method_class,
            goal="Remove the unwanted object while preserving continuity.",
            required_changes=("Remove the unwanted object.",),
            allowed_changes=("Minor local texture repair.",),
            forbidden_changes=("Do not change camera motion.",),
            audio_strategy=audio_strategy,
        )

    def test_approval_inherits_exact_brief_identity_and_creates_no_artifact(self) -> None:
        before = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        state = self.plans.approve(self.project.project_id, self._proposal())
        after = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())

        plan = state.get("edit_1")
        self.assertEqual(before, after)
        self.assertEqual(
            plan.target_identity,
            ("edit_1", "sources/source.mkv", 1_000_000, 2_000_000),
        )
        self.assertEqual(len(plan.brief_sha256), 64)
        self.assertEqual(plan.sample_policy, "not_required")
        self.assertEqual(plan.constraint_ids, ("keep_motion",))
        self.assertEqual(plan.review_target_ids, ("review_motion",))
        self.assertEqual(self.plans.validate_project(self.project.project_id), state)
        self.assertEqual(ReplacementPlan.from_dict(plan.to_dict()), plan)

    def test_generative_method_derives_mandatory_sample_first_policy(self) -> None:
        plan = self.plans.approve(
            self.project.project_id,
            self._proposal(method_class="generative_transform"),
        ).get("edit_1")
        self.assertEqual(plan.sample_policy, "required_before_full_generation")

        raw = plan.to_dict()
        raw["sample_policy"] = "not_required"
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlan.from_dict(raw)

    def test_plan_requires_current_valid_brief_but_not_replacement_media(self) -> None:
        self.briefs.remove(self.project.project_id, "edit_1")
        with self.assertRaises(ReplacementPlanError) as ctx:
            self.plans.approve(self.project.project_id, self._proposal())
        self.assertIn("requires a current valid RangeContinuityBrief", str(ctx.exception))
        self.assertEqual(self.plans.load(self.project.project_id), ReplacementPlanState())

    def test_changed_brief_makes_approved_plan_stale_but_repairable(self) -> None:
        expected = self.plans.approve(self.project.project_id, self._proposal()).get("edit_1")
        self.briefs.upsert(self.project.project_id, self._brief(goal_suffix=" after review"))

        structural = self.plans.load(self.project.project_id)
        self.assertEqual(structural.get("edit_1"), expected)
        with self.assertRaises(ReplacementPlanError) as ctx:
            self.plans.validate_project(self.project.project_id)
        self.assertIn("stale because its Brief changed", str(ctx.exception))
        repaired = self.plans.remove(self.project.project_id, "edit_1")
        self.assertEqual(repaired, ReplacementPlanState())

    def test_reapproval_after_brief_change_refreshes_digest_and_traceability(self) -> None:
        first = self.plans.approve(self.project.project_id, self._proposal()).get("edit_1")
        changed = RangeContinuityBrief(
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
                    requirement="Preserve boundary motion.",
                    evidence_ids=("requested",),
                ),
                ContinuityConstraint(
                    constraint_id="keep_lighting",
                    category="visual",
                    requirement="Preserve lighting direction.",
                    evidence_ids=("requested",),
                ),
            ),
            review_targets=(
                ReviewTarget(
                    target_id="review_motion",
                    criterion="Verify boundary motion continuity.",
                    required=True,
                    evidence_ids=("requested",),
                ),
                ReviewTarget(
                    target_id="review_lighting",
                    criterion="Verify lighting continuity.",
                    required=True,
                    evidence_ids=("requested",),
                ),
            ),
        )
        self.briefs.upsert(self.project.project_id, changed)
        second = self.plans.approve(self.project.project_id, self._proposal()).get("edit_1")
        self.assertNotEqual(first.brief_sha256, second.brief_sha256)
        self.assertEqual(second.constraint_ids, ("keep_lighting", "keep_motion"))
        self.assertEqual(second.review_target_ids, ("review_lighting", "review_motion"))
        self.assertEqual(self.plans.validate_project(self.project.project_id).get("edit_1"), second)

    def test_change_scope_is_bounded_nonempty_and_disjoint(self) -> None:
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="deterministic_edit",
                goal="Do something.",
                required_changes=(),
            )
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="deterministic_edit",
                goal="Do something.",
                required_changes=("Same change",),
                forbidden_changes=("Same change",),
            )
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="deterministic_edit",
                goal="Do something.",
                required_changes=tuple(f"change-{index}" for index in range(33)),
            )

    def test_strict_proposal_rejects_provider_runtime_fields_and_invalid_strategy(self) -> None:
        raw = self._proposal().to_dict()
        raw["provider_id"] = "forbidden"
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlanProposal.from_dict(raw)

        raw = self._proposal().to_dict()
        raw["method_class"] = "kling"
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlanProposal.from_dict(raw)

        raw = self._proposal().to_dict()
        raw["audio_strategy"] = "provider_mix"
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlanProposal.from_dict(raw)

    def test_structural_plan_json_cannot_override_derived_sample_policy_or_target_types(self) -> None:
        plan = self.plans.approve(self.project.project_id, self._proposal()).get("edit_1")
        raw = plan.to_dict()
        raw["start_us"] = True
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlan.from_dict(raw)

        raw = plan.to_dict()
        raw["constraint_ids"] = ["keep_motion", "keep_motion"]
        with self.assertRaises(ReplacementPlanError):
            ReplacementPlan.from_dict(raw)


if __name__ == "__main__":
    unittest.main()
