from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_assembly import MusicAssemblyStore, MusicVisualAssignment
from uv_studio.projects.music_direction import MusicDirectionStore, MusicShotPlan
from uv_studio.projects.music_map import MusicExcerpt, MusicMapStore, MusicSection, MusicTimingMarker
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class MusicAnalysisAndFinalReviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _project(self, title: str = "Music HTTP") -> str:
        response = self.client.post("/api/uv/projects", json={"title": title, "recipe_id": "music_video"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["project_id"]

    def _reference(self, project_id: str, *, ref_id: str, kind: str, path: str, payload: bytes, duration_us: int, artifact: bool = False, metadata: dict[str, object] | None = None) -> ProjectReference:
        target = self.store.project_directory(project_id) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        values: dict[str, object] = {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload), "duration_us": duration_us}
        values.update(metadata or {})
        reference = ProjectReference(id=ref_id, kind=kind, path=path, metadata=values)
        project = self.store.load_project(project_id)
        self.store.update_project(project_id, **({"artifacts": (*project.artifacts, reference)} if artifact else {"sources": (*project.sources, reference)}))
        return reference

    def test_analysis_assist_normalizes_advice_without_writing_music_map(self) -> None:
        project_id = self._project("Analysis HTTP")
        song = self._reference(project_id, ref_id="song", kind="audio", path="sources/song.wav", payload=b"analysis-http-song", duration_us=30_000_000)
        package = self.client.get(f"/api/uv/projects/{project_id}/music-analysis-assist", params={"song_reference_id": song.id})
        self.assertEqual(package.status_code, 200, package.text)
        body = package.json()
        self.assertEqual(body["capability_id"], "audio.analyze_music")
        self.assertTrue(body["requires_human_confirmation"])
        self.assertFalse(body["canonical_state_mutated"])
        normalized = self.client.post(f"/api/uv/projects/{project_id}/music-analysis-assist/normalize", params={"song_reference_id": song.id}, json={
            "binding": body["binding"], "excerpt": {"start_us": 5_000_000, "end_us": 25_000_000},
            "sections": [{"section_id": "chorus", "kind": "chorus", "label": "Chorus", "start_us": 5_000_000, "end_us": 25_000_000}],
            "markers": [{"marker_id": "accent", "kind": "accent", "time_us": 15_000_000}], "lyric_phrases": [], "note": "advisory",
        })
        self.assertEqual(normalized.status_code, 200, normalized.text)
        self.assertFalse(normalized.json()["canonical_state_mutated"])
        current_map = self.client.get(f"/api/uv/projects/{project_id}/music-map")
        self.assertEqual(current_map.status_code, 200, current_map.text)
        self.assertIsNone(current_map.json()["music_map"])
        (self.store.project_directory(project_id) / song.path).write_bytes(b"substituted")
        stale = self.client.post(f"/api/uv/projects/{project_id}/music-analysis-assist/normalize", params={"song_reference_id": song.id}, json={
            "binding": body["binding"], "excerpt": {"start_us": 5_000_000, "end_us": 25_000_000}, "sections": [], "markers": [], "lyric_phrases": [], "note": None,
        })
        self.assertEqual(stale.status_code, 422, stale.text)

    def _review_fixture(self, *, duration_us: int) -> tuple[str, ProjectReference]:
        project_id = self._project("Review HTTP")
        song = self._reference(project_id, ref_id="song", kind="audio", path="sources/song.wav", payload=b"review-http-song", duration_us=max(duration_us, 30_000_000))
        visual = self._reference(project_id, ref_id="visual", kind="video", path="sources/visual.mp4", payload=b"review-http-visual", duration_us=max(duration_us, 30_000_000))
        split = duration_us // 2
        music_map = MusicMapStore(self.store).set_map(project_id, song_reference_id=song.id, excerpt=MusicExcerpt(0, duration_us), sections=(MusicSection("whole", "other", "Whole", 0, duration_us),), markers=(MusicTimingMarker("cut", "cut_point", split),))
        direction = MusicDirectionStore(self.store).set_direction(project_id, music_map_revision_sha256=music_map.revision_sha256, shots=(MusicShotPlan("a", 0, 0, split, "A", ("cut",)), MusicShotPlan("b", 1, split, duration_us, "B")))
        assembly = MusicAssemblyStore(self.store).set_assembly(project_id, music_direction_revision_sha256=direction.revision_sha256, assignments=(MusicVisualAssignment("a", visual.id, 0), MusicVisualAssignment("b", visual.id, split)))
        artifact = self._reference(project_id, ref_id="final", kind="video", path="artifacts/final.mp4", payload=b"review-http-final", duration_us=duration_us, artifact=True, metadata={
            "lifecycle": "music_video_render", "capability_id": "video.render_music_video",
            "composition_mode": "music_assembly_visual_concat_with_exact_master_song_excerpt",
            "music_map_revision_sha256": music_map.revision_sha256, "music_direction_revision_sha256": direction.revision_sha256,
            "music_assembly_revision_sha256": assembly.revision_sha256, "song_reference_id": music_map.song.reference_id,
            "song_sha256": music_map.song.sha256, "song_excerpt": music_map.excerpt.to_dict(),
            "visual_bindings": [item.to_dict() for item in assembly.bindings],
            "actual_output_video_duration_us": duration_us, "actual_output_audio_duration_us": duration_us,
        })
        return project_id, artifact

    def test_final_review_http_enforces_release_gate_and_reopens_current_evidence(self) -> None:
        project_id, artifact = self._review_fixture(duration_us=20_000_000)
        empty = self.client.get(f"/api/uv/projects/{project_id}/music-video-review")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertIsNone(empty.json()["music_video_review"])
        approved = self.client.post(f"/api/uv/projects/{project_id}/music-video-review", json={"artifact_id": artifact.id, "verdict": "approved", "transition_outcome": "pass", "note": "Transitions checked on final render."})
        self.assertEqual(approved.status_code, 201, approved.text)
        review = approved.json()["music_video_review"]
        self.assertEqual(review["verdict"], "approved")
        self.assertEqual(review["evidence"]["release_duration"]["outcome"], "pass")
        self.assertEqual(review["evidence"]["rhythm_alignment"]["outcome"], "pass")
        self.assertEqual(review["evidence"]["render_output_binding"]["outcome"], "pass")
        reopened = self.client.get(f"/api/uv/projects/{project_id}/music-video-review")
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["music_video_review"]["artifact_sha256"], artifact.metadata["sha256"])
        short_id, short_artifact = self._review_fixture(duration_us=4_000_000)
        rejected = self.client.post(f"/api/uv/projects/{short_id}/music-video-review", json={"artifact_id": short_artifact.id, "verdict": "approved", "transition_outcome": "pass", "note": None})
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertIn("20", rejected.json()["detail"])


if __name__ == "__main__":
    unittest.main()
