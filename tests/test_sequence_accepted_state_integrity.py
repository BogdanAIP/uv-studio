from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.sequence_continuity import (
    SEQUENCE_CONTINUITY_PATH,
    SequenceContinuityError,
    SequenceContinuityStore,
    SequenceReviewResult,
    SequenceReviewTarget,
)
from uv_studio.projects.store import ProjectStore


class SequenceAcceptedStateIntegrityTests(unittest.TestCase):
    def test_corrupted_required_result_invalidates_already_accepted_take_on_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(recipe_id="general_video", title="Accepted state integrity")
            project_dir = store.project_directory(project.project_id)
            media = b"accepted-sequence-anchor"
            media_path = project_dir / "sources" / "anchor.mp4"
            media_path.write_bytes(media)
            reference = ProjectReference(
                id="src_anchor",
                kind="video",
                path="sources/anchor.mp4",
                metadata={
                    "sha256": hashlib.sha256(media).hexdigest(),
                    "size_bytes": len(media),
                    "duration_us": 3_000_000,
                },
            )
            current = store.load_project(project.project_id)
            store.update_project(project.project_id, sources=(*current.sources, reference))

            service = SequenceContinuityStore(store)
            service.create_sequence(project.project_id, sequence_id="seq", title="Integrity")
            service.upsert_plan(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_01",
                order=0,
                intent="Keep the subject identity stable.",
                anchor_take_id=None,
                locks=(),
                allowed_changes=(),
                review_targets=(
                    SequenceReviewTarget(
                        target_id="identity",
                        criterion="Subject identity matches.",
                        required=True,
                    ),
                ),
            )
            service.register_take(
                project.project_id,
                sequence_id="seq",
                shot_id="shot_01",
                reference_id="src_anchor",
                take_id="take_anchor",
            )
            review = service.review_take(
                project.project_id,
                sequence_id="seq",
                take_id="take_anchor",
                verdict="approved",
                results=(SequenceReviewResult(target_id="identity", outcome="pass"),),
            )
            accepted = service.accept_take(
                project.project_id,
                sequence_id="seq",
                review_id=review.review_id,
            )
            self.assertEqual(accepted.status, "accepted")

            state_path = project_dir / SEQUENCE_CONTINUITY_PATH
            corrupted = json.loads(state_path.read_text(encoding="utf-8"))
            corrupted["sequences"][0]["reviews"][0]["results"][0]["outcome"] = "fail"
            state_path.write_text(
                json.dumps(corrupted, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                SequenceContinuityError,
                "review no longer passes required targets",
            ):
                service.load(project.project_id)

            with self.assertRaisesRegex(
                SequenceContinuityError,
                "review no longer passes required targets",
            ):
                service.reanchor(
                    project.project_id,
                    sequence_id="seq",
                    take_id="take_anchor",
                )


if __name__ == "__main__":
    unittest.main()
