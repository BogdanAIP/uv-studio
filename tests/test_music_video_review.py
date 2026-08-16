from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_assembly import MusicAssemblyStore, MusicVisualAssignment
from uv_studio.projects.music_direction import MusicDirectionStore, MusicShotPlan
from uv_studio.projects.music_map import MusicExcerpt, MusicMapStore, MusicSection, MusicTimingMarker
from uv_studio.projects.music_video_review import MusicVideoReviewError, MusicVideoReviewStore
from uv_studio.projects.store import ProjectStore


class MusicVideoReviewTests(unittest.TestCase):
    def _reference(self, store, project_id, *, ref_id, kind, path, payload, duration_us, artifact=False, metadata=None):
        target = store.project_directory(project_id) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        base = {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload), "duration_us": duration_us}
        base.update(metadata or {})
        ref = ProjectReference(id=ref_id, kind=kind, path=path, metadata=base)
        project = store.load_project(project_id)
        store.update_project(project_id, **({"artifacts": (*project.artifacts, ref)} if artifact else {"sources": (*project.sources, ref)}))
        return ref

    def _setup(self, tmp: str, *, excerpt_end_us: int = 20_000_000):
        store = ProjectStore(Path(tmp) / "projects")
        project = store.create_project(title="Final review", recipe_id="music_video")
        pid = project.project_id
        song = self._reference(store, pid, ref_id="song", kind="audio", path="sources/song.wav", payload=b"review-song", duration_us=30_000_000)
        visual = self._reference(store, pid, ref_id="visual", kind="video", path="sources/visual.mp4", payload=b"review-visual", duration_us=30_000_000)
        split = excerpt_end_us // 2
        music_map = MusicMapStore(store).set_map(pid, song_reference_id=song.id, excerpt=MusicExcerpt(0, excerpt_end_us), sections=(MusicSection("whole", "other", "Whole", 0, excerpt_end_us),), markers=(MusicTimingMarker("cut", "cut_point", split),))
        direction = MusicDirectionStore(store).set_direction(pid, music_map_revision_sha256=music_map.revision_sha256, shots=(MusicShotPlan("a", 0, 0, split, "A", ("cut",)), MusicShotPlan("b", 1, split, excerpt_end_us, "B")))
        assembly = MusicAssemblyStore(store).set_assembly(pid, music_direction_revision_sha256=direction.revision_sha256, assignments=(MusicVisualAssignment("a", visual.id, 0), MusicVisualAssignment("b", visual.id, split)))
        artifact = self._reference(store, pid, ref_id="final", kind="video", path="artifacts/final.mp4", payload=b"canonical-final-render", duration_us=excerpt_end_us, artifact=True, metadata={
            "lifecycle": "music_video_render",
            "capability_id": "video.render_music_video",
            "composition_mode": "music_assembly_visual_concat_with_exact_master_song_excerpt",
            "music_map_revision_sha256": music_map.revision_sha256,
            "music_direction_revision_sha256": direction.revision_sha256,
            "music_assembly_revision_sha256": assembly.revision_sha256,
            "song_reference_id": music_map.song.reference_id,
            "song_sha256": music_map.song.sha256,
            "song_excerpt": music_map.excerpt.to_dict(),
            "visual_bindings": [item.to_dict() for item in assembly.bindings],
            "actual_output_video_duration_us": excerpt_end_us,
            "actual_output_audio_duration_us": excerpt_end_us,
        })
        return store, pid, artifact

    def test_approved_review_requires_and_records_exact_release_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, pid, artifact = self._setup(tmp)
            service = MusicVideoReviewStore(store)
            review = service.review(pid, artifact_id=artifact.id, verdict="approved", transition_outcome="pass", note="Transitions checked against the final render.")
            self.assertEqual(review.evidence["release_duration"]["outcome"], "pass")
            self.assertEqual(review.evidence["rhythm_alignment"]["outcome"], "pass")
            self.assertEqual(review.evidence["render_output_binding"]["outcome"], "pass")
            self.assertEqual(review.verdict, "approved")
            reopened = service.load(pid, validate_current=True)
            self.assertIsNotNone(reopened)
            assert reopened is not None
            self.assertEqual(reopened.artifact_sha256, artifact.metadata["sha256"])

    def test_short_excerpt_cannot_be_approved_but_can_be_marked_needs_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, pid, artifact = self._setup(tmp, excerpt_end_us=4_000_000)
            service = MusicVideoReviewStore(store)
            with self.assertRaisesRegex(MusicVideoReviewError, "20–30"):
                service.review(pid, artifact_id=artifact.id, verdict="approved", transition_outcome="pass")
            review = service.review(pid, artifact_id=artifact.id, verdict="needs_revision", transition_outcome="pass")
            self.assertEqual(review.evidence["release_duration"]["outcome"], "fail")

    def test_transition_failure_artifact_substitution_and_provenance_tamper_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, pid, artifact = self._setup(tmp)
            service = MusicVideoReviewStore(store)
            with self.assertRaisesRegex(MusicVideoReviewError, "transition"):
                service.review(pid, artifact_id=artifact.id, verdict="approved", transition_outcome="fail")
            service.review(pid, artifact_id=artifact.id, verdict="needs_revision", transition_outcome="fail")
            (store.project_directory(pid) / artifact.path).write_bytes(b"substituted-final")
            with self.assertRaises(MusicVideoReviewError):
                service.load(pid, validate_current=True)

        with tempfile.TemporaryDirectory() as tmp:
            store, pid, artifact = self._setup(tmp)
            project = store.load_project(pid)
            tampered = ProjectReference(id=artifact.id, kind=artifact.kind, path=artifact.path, metadata={**artifact.metadata, "composition_mode": "fake"})
            store.update_project(pid, artifacts=tuple(tampered if item.id == artifact.id else item for item in project.artifacts))
            with self.assertRaisesRegex(MusicVideoReviewError, "composition mode"):
                MusicVideoReviewStore(store).review(pid, artifact_id=artifact.id, verdict="needs_revision", transition_outcome="fail")


if __name__ == "__main__":
    unittest.main()
