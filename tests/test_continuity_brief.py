from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    AcceptedRangeEdit,
    ContinuityBriefError,
    ContinuityConstraint,
    ContinuityEvidence,
    ContinuityObservation,
    MechanicalFact,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefState,
    RangeContinuityBriefStore,
    RangeEditStateStore,
    ReviewTarget,
)


class RangeContinuityBriefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Continuity brief")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        (self.project_dir / "artifacts" / "replacement.mkv").write_bytes(b"replacement")
        (self.project_dir / "assets" / "reference.txt").write_text("reference", encoding="utf-8")
        self.accepted = AcceptedRangeEdit(
            edit_id="edit_1",
            source_path="sources/source.mkv",
            start_us=1_000_000,
            end_us=2_000_000,
            replacement_path="artifacts/replacement.mkv",
        )
        RangeEditStateStore(self.store).accept(self.project.project_id, self.accepted)
        self.briefs = RangeContinuityBriefStore(self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _brief(self) -> RangeContinuityBrief:
        evidence = (
            ContinuityEvidence(
                evidence_id="ev_before",
                role="before",
                path="sources/source.mkv",
                source_start_us=500_000,
                source_end_us=1_000_000,
            ),
            ContinuityEvidence(
                evidence_id="ev_requested",
                role="requested",
                path="sources/source.mkv",
                source_start_us=1_000_000,
                source_end_us=2_000_000,
            ),
            ContinuityEvidence(
                evidence_id="ev_after",
                role="after",
                path="sources/source.mkv",
                source_start_us=2_000_000,
                source_end_us=2_500_000,
            ),
            ContinuityEvidence(
                evidence_id="ev_reference",
                role="reference",
                path="assets/reference.txt",
            ),
        )
        return RangeContinuityBrief(
            edit_id=self.accepted.edit_id,
            source_path=self.accepted.source_path,
            start_us=self.accepted.start_us,
            end_us=self.accepted.end_us,
            replacement_path=self.accepted.replacement_path,
            evidence=evidence,
            mechanical_facts=(
                MechanicalFact(
                    fact_id="fact_width",
                    key="width_px",
                    value=160,
                    unit="px",
                    evidence_ids=("ev_requested",),
                ),
                MechanicalFact(
                    fact_id="fact_audio",
                    key="has_audio",
                    value=False,
                    evidence_ids=("ev_requested",),
                ),
            ),
            observations=(
                ContinuityObservation(
                    observation_id="obs_motion",
                    kind="observation",
                    statement="Camera is static immediately before the requested range.",
                    confidence="high",
                    evidence_ids=("ev_before",),
                ),
                ContinuityObservation(
                    observation_id="inf_direction",
                    kind="inference",
                    statement="A static replacement is likely to preserve camera continuity.",
                    confidence="medium",
                    evidence_ids=("ev_before", "ev_after"),
                ),
            ),
            constraints=(
                ContinuityConstraint(
                    constraint_id="constraint_motion",
                    category="motion",
                    requirement="Do not introduce a camera move at either edit boundary.",
                    evidence_ids=("ev_before", "ev_after"),
                ),
            ),
            review_targets=(
                ReviewTarget(
                    target_id="review_boundaries",
                    criterion="Verify both cut boundaries preserve the static camera state.",
                    required=True,
                    evidence_ids=("ev_before", "ev_after"),
                ),
            ),
        )

    def test_valid_brief_round_trips_and_requires_no_media_execution(self) -> None:
        artifacts_before = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        expected = self._brief()
        state = self.briefs.upsert(self.project.project_id, expected)
        self.assertEqual(state.get("edit_1"), expected)
        self.assertEqual(self.briefs.validate_project(self.project.project_id).get("edit_1"), expected)
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before,
        )
        self.assertEqual(RangeContinuityBrief.from_dict(expected.to_dict()), expected)

    def test_requested_before_after_roles_are_range_consistent(self) -> None:
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id=self.accepted.edit_id,
                source_path=self.accepted.source_path,
                start_us=self.accepted.start_us,
                end_us=self.accepted.end_us,
                replacement_path=self.accepted.replacement_path,
                evidence=(
                    ContinuityEvidence(
                        evidence_id="bad_before",
                        role="before",
                        path="sources/source.mkv",
                        source_start_us=900_000,
                        source_end_us=1_100_000,
                    ),
                ),
            )
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id=self.accepted.edit_id,
                source_path=self.accepted.source_path,
                start_us=self.accepted.start_us,
                end_us=self.accepted.end_us,
                replacement_path=self.accepted.replacement_path,
                evidence=(
                    ContinuityEvidence(
                        evidence_id="bad_requested",
                        role="requested",
                        path="sources/source.mkv",
                        source_start_us=1_100_000,
                        source_end_us=1_900_000,
                    ),
                ),
            )

    def test_evidence_windows_are_bounded(self) -> None:
        with self.assertRaises(ContinuityBriefError):
            ContinuityEvidence(
                evidence_id="too_long",
                role="reference",
                path="sources/source.mkv",
                source_start_us=0,
                source_end_us=30_000_001,
            )

    def test_observations_and_other_structures_cannot_reference_unknown_evidence(self) -> None:
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id=self.accepted.edit_id,
                source_path=self.accepted.source_path,
                start_us=self.accepted.start_us,
                end_us=self.accepted.end_us,
                replacement_path=self.accepted.replacement_path,
                observations=(
                    ContinuityObservation(
                        observation_id="obs_unknown",
                        kind="observation",
                        statement="Visible fact with missing evidence.",
                        confidence="low",
                        evidence_ids=("missing_evidence",),
                    ),
                ),
            )

    def test_store_requires_exact_current_accepted_edit_identity(self) -> None:
        brief = self._brief()
        wrong_replacement = RangeContinuityBrief.from_dict(
            {**brief.to_dict(), "replacement_path": "artifacts/other.mkv"}
        )
        (self.project_dir / "artifacts" / "other.mkv").write_bytes(b"other")
        with self.assertRaises(ContinuityBriefError):
            self.briefs.upsert(self.project.project_id, wrong_replacement)

    def test_strict_json_rejects_provider_runtime_fields_and_wrong_scalar_types(self) -> None:
        data = self._brief().to_dict()
        data["provider_id"] = "forbidden-runtime-binding"
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief.from_dict(data)

        data = self._brief().to_dict()
        data["mechanical_facts"][0]["value"] = 12.5
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief.from_dict(data)

    def test_removed_edit_leaves_brief_structurally_readable_and_removable(self) -> None:
        self.briefs.upsert(self.project.project_id, self._brief())
        RangeEditStateStore(self.store).remove(self.project.project_id, "edit_1")

        structural = self.briefs.load(self.project.project_id)
        self.assertEqual(structural.get("edit_1").edit_id, "edit_1")
        with self.assertRaises(ContinuityBriefError):
            self.briefs.validate_project(self.project.project_id)
        repaired = self.briefs.remove(self.project.project_id, "edit_1")
        self.assertEqual(repaired, RangeContinuityBriefState())
        self.assertEqual(self.briefs.validate_project(self.project.project_id), RangeContinuityBriefState())


if __name__ == "__main__":
    unittest.main()
