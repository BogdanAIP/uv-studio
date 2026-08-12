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
        self.source = self.project_dir / "sources" / "source.mkv"
        self.replacement = self.project_dir / "artifacts" / "replacement.mkv"
        self.reference = self.project_dir / "assets" / "reference.txt"
        self.source.write_bytes(b"source")
        self.replacement.write_bytes(b"replacement")
        self.reference.write_text("reference", encoding="utf-8")
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

    def _evidence(self) -> tuple[ContinuityEvidence, ...]:
        return (
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

    def _brief(self) -> RangeContinuityBrief:
        return RangeContinuityBrief(
            edit_id=self.accepted.edit_id,
            source_path=self.accepted.source_path,
            start_us=self.accepted.start_us,
            end_us=self.accepted.end_us,
            evidence=self._evidence(),
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

    def _minimal_brief(
        self,
        *,
        edit_id: str = "edit_1",
        start_us: int = 1_000_000,
        end_us: int = 2_000_000,
    ) -> RangeContinuityBrief:
        return RangeContinuityBrief(
            edit_id=edit_id,
            source_path="sources/source.mkv",
            start_us=start_us,
            end_us=end_us,
            evidence=(
                ContinuityEvidence(
                    evidence_id="requested",
                    role="requested",
                    path="sources/source.mkv",
                    source_start_us=start_us,
                    source_end_us=end_us,
                ),
            ),
        )

    def test_valid_brief_round_trips_and_requires_no_media_execution(self) -> None:
        artifacts_before = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        expected = self._brief()
        state = self.briefs.upsert(self.project.project_id, expected)
        self.assertEqual(state.get("edit_1"), expected)
        self.assertEqual(
            self.briefs.validate_project(self.project.project_id).get("edit_1"),
            expected,
        )
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before,
        )
        self.assertEqual(RangeContinuityBrief.from_dict(expected.to_dict()), expected)
        self.assertNotIn("replacement_path", expected.to_dict())

    def test_brief_can_exist_before_replacement_or_accepted_edit(self) -> None:
        RangeEditStateStore(self.store).remove(self.project.project_id, "edit_1")
        self.replacement.unlink()

        expected = self._brief()
        state = self.briefs.upsert(self.project.project_id, expected)
        self.assertEqual(state.get("edit_1"), expected)
        self.assertEqual(
            self.briefs.validate_project(self.project.project_id).get("edit_1"),
            expected,
        )

        self.replacement.write_bytes(b"replacement")
        RangeEditStateStore(self.store).accept(self.project.project_id, self.accepted)
        self.assertEqual(
            self.briefs.validate_project(self.project.project_id).get("edit_1"),
            expected,
        )

    def test_existing_accepted_edit_must_match_target_but_not_replacement_identity(self) -> None:
        with self.assertRaises(ContinuityBriefError) as ctx:
            self.briefs.upsert(
                self.project.project_id,
                self._minimal_brief(start_us=1_100_000),
            )
        self.assertIn("does not exactly match accepted edit", str(ctx.exception))

        self.briefs.upsert(self.project.project_id, self._brief())
        RangeEditStateStore(self.store).remove(self.project.project_id, "edit_1")
        alternate = self.project_dir / "artifacts" / "alternate.mkv"
        alternate.write_bytes(b"alternate")
        RangeEditStateStore(self.store).accept(
            self.project.project_id,
            AcceptedRangeEdit(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                replacement_path="artifacts/alternate.mkv",
            ),
        )
        self.assertEqual(
            self.briefs.validate_project(self.project.project_id).get("edit_1"),
            self._brief(),
        )

    def test_temporal_evidence_is_source_bound_and_adjacent_to_target(self) -> None:
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                evidence=(
                    ContinuityEvidence(
                        evidence_id="requested",
                        role="requested",
                        path="assets/reference.txt",
                        source_start_us=1_000_000,
                        source_end_us=2_000_000,
                    ),
                ),
            )

        with self.assertRaises(ContinuityBriefError):
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
                    ContinuityEvidence(
                        evidence_id="bad_before",
                        role="before",
                        path="sources/source.mkv",
                        source_start_us=500_000,
                        source_end_us=900_000,
                    ),
                ),
            )

        with self.assertRaises(ContinuityBriefError):
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
                    ContinuityEvidence(
                        evidence_id="bad_after",
                        role="after",
                        path="sources/source.mkv",
                        source_start_us=2_100_000,
                        source_end_us=2_500_000,
                    ),
                ),
            )

    def test_reference_coordinates_are_only_meaningful_on_target_source(self) -> None:
        with self.assertRaises(ContinuityBriefError):
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
                    ContinuityEvidence(
                        evidence_id="reference",
                        role="reference",
                        path="assets/reference.txt",
                        source_start_us=0,
                        source_end_us=500_000,
                    ),
                ),
            )

    def test_evidence_windows_are_bounded_and_requested_evidence_is_required_once(self) -> None:
        with self.assertRaises(ContinuityBriefError):
            ContinuityEvidence(
                evidence_id="too_long",
                role="reference",
                path="sources/source.mkv",
                source_start_us=0,
                source_end_us=30_000_001,
            )
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                evidence=(),
            )
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                evidence=(
                    ContinuityEvidence(
                        evidence_id="requested_a",
                        role="requested",
                        path="sources/source.mkv",
                        source_start_us=1_000_000,
                        source_end_us=2_000_000,
                    ),
                    ContinuityEvidence(
                        evidence_id="requested_b",
                        role="requested",
                        path="sources/source.mkv",
                        source_start_us=1_000_000,
                        source_end_us=2_000_000,
                    ),
                ),
            )

    def test_observations_and_other_structures_cannot_reference_unknown_evidence(self) -> None:
        with self.assertRaises(ContinuityBriefError):
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

    def test_strict_json_and_mechanical_fact_keys_reject_runtime_binding(self) -> None:
        data = self._brief().to_dict()
        data["provider_id"] = "forbidden-runtime-binding"
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief.from_dict(data)

        data = self._brief().to_dict()
        data["mechanical_facts"][0]["value"] = 12.5
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief.from_dict(data)

        with self.assertRaises(ContinuityBriefError):
            MechanicalFact(
                fact_id="bad_provider",
                key="provider_id",
                value="provider-x",
            )
        with self.assertRaises(ContinuityBriefError):
            MechanicalFact(
                fact_id="bad_runtime",
                key="runtime_pid",
                value=123,
            )

    def test_collection_sizes_are_bounded(self) -> None:
        evidence = [
            ContinuityEvidence(
                evidence_id="requested",
                role="requested",
                path="sources/source.mkv",
                source_start_us=1_000_000,
                source_end_us=2_000_000,
            )
        ]
        evidence.extend(
            ContinuityEvidence(
                evidence_id=f"ref_{index}",
                role="reference",
                path="assets/reference.txt",
            )
            for index in range(32)
        )
        with self.assertRaises(ContinuityBriefError):
            RangeContinuityBrief(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                evidence=tuple(evidence),
            )

    def test_stale_source_is_structurally_readable_and_removable(self) -> None:
        self.briefs.upsert(self.project.project_id, self._brief())
        self.source.unlink()

        structural = self.briefs.load(self.project.project_id)
        self.assertEqual(structural.get("edit_1").edit_id, "edit_1")
        with self.assertRaises(ContinuityBriefError):
            self.briefs.validate_project(self.project.project_id)
        repaired = self.briefs.remove(self.project.project_id, "edit_1")
        self.assertEqual(repaired, RangeContinuityBriefState())

    def test_later_conflicting_accepted_edit_makes_brief_stale_without_hiding_it(self) -> None:
        RangeEditStateStore(self.store).remove(self.project.project_id, "edit_1")
        self.briefs.upsert(self.project.project_id, self._brief())
        RangeEditStateStore(self.store).accept(
            self.project.project_id,
            AcceptedRangeEdit(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=3_000_000,
                end_us=4_000_000,
                replacement_path="artifacts/replacement.mkv",
            ),
        )

        self.assertEqual(
            self.briefs.load(self.project.project_id).get("edit_1").start_us,
            1_000_000,
        )
        with self.assertRaises(ContinuityBriefError):
            self.briefs.validate_project(self.project.project_id)


if __name__ == "__main__":
    unittest.main()
