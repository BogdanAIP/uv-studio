from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.sequence_continuity import (
    MAX_OBSERVATIONS_PER_REVIEW,
    SequenceContinuityStore,
    SequenceReviewTarget,
)
from uv_studio.projects.sequence_review_assist import (
    SequenceReviewAssistError,
    build_sequence_review_assist,
    normalize_sequence_review_suggestion,
)
from uv_studio.projects.store import ProjectStore


class SequenceReviewAssistBoundsTests(unittest.TestCase):
    def test_normalize_rejects_observations_over_declared_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(recipe_id="general_video", title="Review assist bounds")
            project_dir = store.project_directory(project.project_id)
            media = b"bounded-review-assist-video"
            media_path = project_dir / "sources" / "candidate.mp4"
            media_path.write_bytes(media)
            current = store.load_project(project.project_id)
            store.update_project(
                project.project_id,
                sources=(
                    *current.sources,
                    ProjectReference(
                        id="src_candidate",
                        kind="video",
                        path="sources/candidate.mp4",
                        metadata={
                            "sha256": hashlib.sha256(media).hexdigest(),
                            "size_bytes": len(media),
                            "duration_us": 2_000_000,
                        },
                    ),
                ),
            )

            service = SequenceContinuityStore(store)
            service.create_sequence(project.project_id, sequence_id="seq", title="Bounds")
            service.upsert_plan(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_01",
                order=0,
                intent="Review a bounded candidate.",
                anchor_take_id=None,
                locks=(),
                allowed_changes=(),
                review_targets=(
                    SequenceReviewTarget(
                        target_id="continuity",
                        criterion="Candidate is internally coherent.",
                    ),
                ),
            )
            service.register_take(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_01",
                reference_id="src_candidate",
                take_id="take_candidate",
            )
            package = build_sequence_review_assist(
                service,
                project.project_id,
                sequence_id="seq",
                take_id="take_candidate",
            )
            observations = [
                {
                    "observation_id": f"obs_{index}",
                    "kind": "observation",
                    "category": "visual",
                    "statement": f"Observation {index}",
                    "confidence": "medium",
                }
                for index in range(MAX_OBSERVATIONS_PER_REVIEW + 1)
            ]

            with self.assertRaisesRegex(
                SequenceReviewAssistError,
                f"at most {MAX_OBSERVATIONS_PER_REVIEW}",
            ):
                normalize_sequence_review_suggestion(
                    service,
                    project.project_id,
                    sequence_id="seq",
                    take_id="take_candidate",
                    payload={
                        "binding": package.binding.to_dict(),
                        "verdict": "needs_revision",
                        "results": [
                            {
                                "target_id": "continuity",
                                "outcome": "uncertain",
                                "note": None,
                            }
                        ],
                        "observations": observations,
                        "note": None,
                    },
                )


if __name__ == "__main__":
    unittest.main()
