from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.sequence_context import build_sequence_timeline_context
from uv_studio.projects.sequence_continuity import (
    SequenceContinuityRule,
    SequenceContinuityStore,
    SequenceObservation,
    SequenceReviewResult,
    SequenceReviewTarget,
)
from uv_studio.projects.store import ProjectStore


class SequenceContextTests(unittest.TestCase):
    def test_linked_context_exposes_observed_anchor_review_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Observed sequence context")
            project_dir = store.project_directory(project.project_id)

            def register(reference_id: str, filename: str, payload: bytes, duration_us: int) -> None:
                path = project_dir / "sources" / filename
                path.write_bytes(payload)
                current = store.load_project(project.project_id)
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
                store.update_project(project.project_id, sources=(*current.sources, reference))

            register("src_anchor", "anchor.mp4", b"anchor", 4_000_000)
            register("src_candidate", "candidate.mp4", b"candidate", 3_000_000)
            service = SequenceContinuityStore(store)
            service.create_sequence(project.project_id, sequence_id="seq", title="Observed facts")
            service.upsert_plan(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_01",
                order=0,
                intent="Establish anchor.",
                anchor_take_id=None,
                locks=(),
                allowed_changes=(),
                review_targets=(SequenceReviewTarget(target_id="identity", criterion="Identity matches."),),
            )
            service.register_take(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_01",
                reference_id="src_anchor",
                take_id="take_anchor",
            )
            anchor_review = service.review_take(
                project.project_id,
                sequence_id="seq",
                take_id="take_anchor",
                verdict="approved",
                results=(SequenceReviewResult(target_id="identity", outcome="pass"),),
                observations=(
                    SequenceObservation(
                        observation_id="exit_direction",
                        kind="observation",
                        category="motion",
                        statement="Subject exits screen-right.",
                        confidence="high",
                    ),
                ),
            )
            service.accept_take(
                project.project_id,
                sequence_id="seq",
                review_id=anchor_review.review_id,
            )
            service.reanchor(project.project_id, sequence_id="seq", take_id="take_anchor")
            service.upsert_plan(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_02",
                order=1,
                intent="Continue from accepted exit.",
                anchor_take_id="take_anchor",
                locks=(
                    SequenceContinuityRule(
                        rule_id="direction",
                        category="motion",
                        requirement="Continue screen-right movement.",
                    ),
                ),
                allowed_changes=(),
                review_targets=(SequenceReviewTarget(target_id="continuity", criterion="Direction continues."),),
            )
            service.register_take(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_02",
                reference_id="src_candidate",
                take_id="take_candidate",
            )

            context = build_sequence_timeline_context(
                service,
                project.project_id,
                sequence_id="seq",
                take_id="take_candidate",
                window_us=1_000_000,
                samples=3,
            )
            self.assertEqual(
                context["anchor"]["observations"],
                [
                    {
                        "observation_id": "exit_direction",
                        "kind": "observation",
                        "category": "motion",
                        "statement": "Subject exits screen-right.",
                        "confidence": "high",
                    }
                ],
            )
            self.assertEqual(context["candidate"]["observations"], [])
            self.assertEqual(context["anchor"]["sample_times_us"], [3_000_000, 3_500_000, 4_000_000])
            self.assertEqual(context["candidate"]["sample_times_us"], [0, 500_000, 1_000_000])


if __name__ == "__main__":
    unittest.main()
