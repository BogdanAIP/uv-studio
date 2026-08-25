from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import ProjectReference, ProjectStore, export_project, import_project
from uv_studio.projects.sequence_continuity import (
    SequenceContinuityRule,
    SequenceContinuityStore,
    SequenceObservation,
    SequenceReviewResult,
    SequenceReviewTarget,
)


class SequenceContinuityArchiveTests(unittest.TestCase):
    def test_export_import_and_fresh_reopen_preserve_accepted_anchor_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_store = ProjectStore(root / "source-projects")
            project = source_store.create_project(recipe_id="general_video",
                title="Sequence archive",
                project_id="prj_sequence",
            )
            project_dir = source_store.project_directory(project.project_id)
            payload = b"accepted-sequence-video"
            source_path = project_dir / "sources" / "anchor.mp4"
            source_path.write_bytes(payload)
            source = ProjectReference(
                id="src_anchor",
                kind="video",
                path="sources/anchor.mp4",
                metadata={
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "duration_us": 5_000_000,
                },
            )
            source_store.update_project(project.project_id, sources=(source,))

            continuity = SequenceContinuityStore(source_store)
            continuity.create_sequence(
                project.project_id,
                sequence_id="seq_main",
                title="Persistent continuity",
            )
            continuity.upsert_plan(
                project.project_id,
                sequence_id="seq_main",
                shot_id="shot_01",
                order=0,
                intent="Establish the persistent anchor.",
                anchor_take_id=None,
                locks=(
                    SequenceContinuityRule(
                        rule_id="lock_identity",
                        category="content",
                        requirement="Keep subject identity.",
                    ),
                ),
                allowed_changes=(),
                review_targets=(
                    SequenceReviewTarget(
                        target_id="target_identity",
                        criterion="Identity is consistent.",
                        required=True,
                    ),
                ),
            )
            continuity.register_take(
                project.project_id,
                sequence_id="seq_main",
                shot_id="shot_01",
                reference_id=source.id,
                take_id="take_anchor",
            )
            review = continuity.review_take(
                project.project_id,
                sequence_id="seq_main",
                take_id="take_anchor",
                verdict="approved",
                results=(
                    SequenceReviewResult(
                        target_id="target_identity",
                        outcome="pass",
                    ),
                ),
                observations=(
                    SequenceObservation(
                        observation_id="obs_anchor",
                        kind="observation",
                        category="visual",
                        statement="Accepted frame establishes the factual anchor.",
                        confidence="high",
                    ),
                ),
            )
            continuity.accept_take(
                project.project_id,
                sequence_id="seq_main",
                review_id=review.review_id,
            )
            continuity.reanchor(
                project.project_id,
                sequence_id="seq_main",
                take_id="take_anchor",
            )
            expected = continuity.load(project.project_id, validate_current=True).to_dict()

            archive = export_project(
                source_store,
                project.project_id,
                root / "sequence.uvproj.zip",
            )
            target_root = root / "target-projects"
            imported = import_project(ProjectStore(target_root), archive)
            self.assertEqual(imported.project_id, project.project_id)

            fresh_store = ProjectStore(target_root)
            reopened = SequenceContinuityStore(fresh_store).load(
                project.project_id,
                validate_current=True,
            )
            self.assertEqual(reopened.to_dict(), expected)
            sequence = reopened.sequence("seq_main")
            self.assertEqual(sequence.anchor_take_id, "take_anchor")
            self.assertEqual(sequence.take("take_anchor").status, "accepted")
            self.assertEqual(
                sequence.review(review.review_id).observations[0].statement,
                "Accepted frame establishes the factual anchor.",
            )


if __name__ == "__main__":
    unittest.main()
