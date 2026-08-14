from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.sequence_continuity import (
    SequenceContinuityRule,
    SequenceContinuityStore,
    SequenceObservation,
    SequenceReviewResult,
    SequenceReviewTarget,
)
from uv_studio.projects.sequence_review_assist import (
    SequenceReviewAssistError,
    build_sequence_review_assist,
    normalize_sequence_review_suggestion,
)
from uv_studio.projects.store import ProjectStore


class SequenceReviewAssistTests(unittest.TestCase):
    def _register_video(
        self,
        store: ProjectStore,
        project_id: str,
        reference_id: str,
        filename: str,
        payload: bytes,
        duration_us: int,
    ) -> None:
        project_dir = store.project_directory(project_id)
        path = project_dir / "sources" / filename
        path.write_bytes(payload)
        current = store.load_project(project_id)
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
        store.update_project(project_id, sources=(*current.sources, reference))

    def _prepare_linked_candidate(self, store: ProjectStore, project_id: str) -> SequenceContinuityStore:
        self._register_video(store, project_id, "src_anchor", "anchor.mp4", b"anchor", 4_000_000)
        self._register_video(
            store, project_id, "src_candidate", "candidate.mp4", b"candidate", 3_000_000
        )
        service = SequenceContinuityStore(store)
        service.create_sequence(project_id, sequence_id="seq", title="Assist")
        service.upsert_plan(
            project_id,
            sequence_id="seq",
            shot_id="shot_01",
            order=0,
            intent="Establish subject.",
            anchor_take_id=None,
            locks=(),
            allowed_changes=(),
            review_targets=(
                SequenceReviewTarget(target_id="identity", criterion="Identity matches."),
            ),
        )
        service.register_take(
            project_id,
            sequence_id="seq",
            shot_id="shot_01",
            reference_id="src_anchor",
            take_id="take_anchor",
        )
        anchor_review = service.review_take(
            project_id,
            sequence_id="seq",
            take_id="take_anchor",
            verdict="approved",
            results=(SequenceReviewResult(target_id="identity", outcome="pass"),),
            observations=(
                SequenceObservation(
                    observation_id="exit",
                    kind="observation",
                    category="motion",
                    statement="Subject exits screen-right.",
                    confidence="high",
                ),
            ),
        )
        service.accept_take(project_id, sequence_id="seq", review_id=anchor_review.review_id)
        service.reanchor(project_id, sequence_id="seq", take_id="take_anchor")
        service.upsert_plan(
            project_id,
            sequence_id="seq",
            shot_id="shot_02",
            order=1,
            intent="Continue into a closer framing.",
            anchor_take_id="take_anchor",
            locks=(
                SequenceContinuityRule(
                    rule_id="direction",
                    category="motion",
                    requirement="Continue screen-right movement.",
                ),
            ),
            allowed_changes=(
                SequenceContinuityRule(
                    rule_id="framing",
                    category="visual",
                    requirement="Framing may get closer.",
                ),
            ),
            review_targets=(
                SequenceReviewTarget(
                    target_id="continuity",
                    criterion="Direction continues from accepted anchor.",
                ),
            ),
        )
        service.register_take(
            project_id,
            sequence_id="seq",
            shot_id="shot_02",
            reference_id="src_candidate",
            take_id="take_candidate",
        )
        return service

    def test_package_is_bounded_provider_neutral_and_project_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Assist package")
            service = self._prepare_linked_candidate(store, project.project_id)

            package = build_sequence_review_assist(
                service,
                project.project_id,
                sequence_id="seq",
                take_id="take_candidate",
                window_us=1_000_000,
                samples=3,
            ).to_dict()

            self.assertEqual(package["capability_id"], "media.understand")
            self.assertTrue(package["requires_human_confirmation"])
            self.assertFalse(package["canonical_state_mutated"])
            media = package["capability_input"]["media"]
            self.assertEqual([item["role"] for item in media], ["anchor", "candidate"])
            self.assertEqual(media[0]["project_reference"], "sources/anchor.mp4")
            self.assertEqual(media[1]["project_reference"], "sources/candidate.mp4")
            self.assertEqual(media[0]["sample_times_us"], [3_000_000, 3_500_000, 4_000_000])
            self.assertEqual(media[1]["sample_times_us"], [0, 500_000, 1_000_000])
            self.assertEqual(
                package["capability_input"]["context"]["anchor_observations"][0]["statement"],
                "Subject exits screen-right.",
            )
            for item in media:
                self.assertFalse(Path(item["project_reference"]).is_absolute())

    def test_approved_vlm_suggestion_does_not_create_review_or_accept_take(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Assist no authority")
            service = self._prepare_linked_candidate(store, project.project_id)
            package = build_sequence_review_assist(
                service,
                project.project_id,
                sequence_id="seq",
                take_id="take_candidate",
            )
            before = service.load(project.project_id).sequence("seq")
            self.assertEqual(before.take("take_candidate").status, "prepared")
            self.assertIsNone(before.take("take_candidate").current_review_id)

            suggestion = normalize_sequence_review_suggestion(
                service,
                project.project_id,
                sequence_id="seq",
                take_id="take_candidate",
                payload={
                    "binding": package.binding.to_dict(),
                    "verdict": "approved",
                    "results": [
                        {
                            "target_id": "continuity",
                            "outcome": "pass",
                            "note": "Bounded evidence is consistent.",
                        }
                    ],
                    "observations": [
                        {
                            "observation_id": "candidate_direction",
                            "kind": "observation",
                            "category": "motion",
                            "statement": "Candidate continues screen-right.",
                            "confidence": "high",
                        }
                    ],
                    "note": "VLM suggestion only.",
                },
            )
            self.assertEqual(suggestion.verdict, "approved")
            self.assertTrue(suggestion.to_dict()["requires_human_confirmation"])

            after = service.load(project.project_id).sequence("seq")
            self.assertEqual(after.take("take_candidate").status, "prepared")
            self.assertIsNone(after.take("take_candidate").current_review_id)
            self.assertEqual(len(after.reviews), len(before.reviews))

    def test_stale_suggestion_is_rejected_after_plan_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Assist stale")
            service = self._prepare_linked_candidate(store, project.project_id)
            package = build_sequence_review_assist(
                service,
                project.project_id,
                sequence_id="seq",
                take_id="take_candidate",
            )
            service.upsert_plan(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_02",
                order=1,
                intent="Continue with a revised closer framing.",
                anchor_take_id="take_anchor",
                locks=(
                    SequenceContinuityRule(
                        rule_id="direction",
                        category="motion",
                        requirement="Continue screen-right movement.",
                    ),
                ),
                allowed_changes=(),
                review_targets=(
                    SequenceReviewTarget(
                        target_id="continuity",
                        criterion="Direction continues from accepted anchor.",
                    ),
                ),
            )

            with self.assertRaisesRegex(SequenceReviewAssistError, "stale"):
                normalize_sequence_review_suggestion(
                    service,
                    project.project_id,
                    sequence_id="seq",
                    take_id="take_candidate",
                    payload={
                        "binding": package.binding.to_dict(),
                        "verdict": "approved",
                        "results": [
                            {
                                "target_id": "continuity",
                                "outcome": "pass",
                                "note": None,
                            }
                        ],
                        "observations": [],
                        "note": None,
                    },
                )


if __name__ == "__main__":
    unittest.main()
