from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.editor_commands import get_dubbing_loudness_measure
from uv_studio.api.projects import get_project_store
from uv_studio.projects.dubbing_review import DubbingReviewStore
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class DubbingReviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_dubbing_loudness_measure] = lambda: self._measure_loudness
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"title": "Dubbing review"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, "source.mp4")
        source_body = b"source-video"
        allocation.absolute_path.write_bytes(source_body)
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "source.mp4",
                "content_type": "video/mp4",
                "size_bytes": len(source_body),
                "sha256": hashlib.sha256(source_body).hexdigest(),
                "duration_us": 8_000_000,
                "has_audio": True,
                "width": 1280,
                "height": 720,
            },
        )
        self.source = project.sources[0]
        self.loudness_true_peak = -2.0
        self.loudness_measurable = True

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @property
    def command_url(self) -> str:
        return f"/api/uv/projects/{self.project_id}/editor/commands"

    def _measure_loudness(self, _project_id: str, audio_id: str):
        reference = next(item for item in self.store.load_project(self.project_id).artifacts if item.id == audio_id)
        return {
            "audio_id": reference.id,
            "audio_sha256": reference.metadata["sha256"],
            "duration_us": reference.metadata["duration_us"],
            "measurable": self.loudness_measurable,
            "integrated_lufs": -20.0 if self.loudness_measurable else None,
            "true_peak_dbtp": self.loudness_true_peak if self.loudness_measurable else None,
            "loudness_range_lu": 3.2 if self.loudness_measurable else None,
            "threshold_lufs": -30.0 if self.loudness_measurable else None,
        }

    def _create_transcript(self) -> dict:
        response = self.client.post(
            self.command_url,
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 1_000_000,
                "end_us": 6_000_000,
                "segments": [
                    {"segment_id": "seg_001", "start_us": 1_000_000, "end_us": 3_000_000, "text": "First line"},
                    {"segment_id": "seg_002", "start_us": 3_500_000, "end_us": 5_500_000, "text": "Second line"},
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _register_audio(self, *, duration_us: int = 1_850_000):
        audio_store = ProjectPreparedAudioStore(self.store)
        allocation = audio_store.allocate(self.project_id, "take.wav")
        body = f"speech-{duration_us}".encode()
        allocation.absolute_path.write_bytes(body)
        project = audio_store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "take.wav",
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": duration_us,
                "has_audio": True,
                "has_video": False,
                "origin": "recorded",
            },
        )
        return next(item for item in project.artifacts if item.id == allocation.audio_id)

    def _attach_take(self, *, duration_us: int = 1_850_000) -> dict:
        transcript = self._create_transcript()
        audio = self._register_audio(duration_us=duration_us)
        response = self.client.post(
            self.command_url,
            json={"command": "attach_prepared_speech", "dubbing_id": transcript["dubbing_id"], "audio_id": audio.id, "segment_id": "seg_001"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["payload"]["prepared_speech"]

    def _review(self, take_id: str, *, verdict: str = "approved", content: bool = True, sync: bool = True):
        return self.client.post(
            self.command_url,
            json={
                "command": "review_prepared_speech",
                "take_id": take_id,
                "verdict": verdict,
                "content_fidelity_confirmed": content,
                "synchronization_confirmed": sync,
                "note": "Reviewed against selected dialogue",
            },
        )

    def _accept(self, review_id: str):
        return self.client.post(
            self.command_url,
            json={"command": "accept_dubbing_review", "review_id": review_id, "composition_policy": "replace_source_audio_range"},
        )

    def test_approved_review_is_current_and_can_be_accepted(self) -> None:
        take = self._attach_take()
        reviewed = self._review(take["take_id"])
        self.assertEqual(reviewed.status_code, 201, reviewed.text)
        payload = reviewed.json()["payload"]
        review = payload["review"]
        self.assertEqual(payload["current_review_id"], review["review_id"])
        self.assertTrue(review["timing_pass"])
        self.assertTrue(review["audio_safety_pass"])
        current = self.client.get(f"/api/uv/projects/{self.project_id}/dubbing-reviews/current")
        self.assertEqual(current.status_code, 200, current.text)
        self.assertEqual(current.json()["current_by_take"][take["take_id"]], review["review_id"])
        self.assertEqual(self._accept(review["review_id"]).status_code, 201)

    def test_newer_review_supersedes_old_approved_review(self) -> None:
        take = self._attach_take()
        approved = self._review(take["take_id"])
        self.assertEqual(approved.status_code, 201, approved.text)
        approved_id = approved.json()["payload"]["review"]["review_id"]
        rejected = self._review(take["take_id"], verdict="rejected", content=False, sync=False)
        self.assertEqual(rejected.status_code, 201, rejected.text)
        rejected_id = rejected.json()["payload"]["review"]["review_id"]
        self.assertEqual(self._accept(approved_id).status_code, 422)
        current = self.client.get(f"/api/uv/projects/{self.project_id}/dubbing-reviews/current").json()
        self.assertEqual(current["current_by_take"][take["take_id"]], rejected_id)
        self.assertEqual(self._accept(rejected_id).status_code, 422)

    def test_audio_change_after_review_prevents_acceptance(self) -> None:
        take = self._attach_take()
        reviewed = self._review(take["take_id"])
        self.assertEqual(reviewed.status_code, 201, reviewed.text)
        review_id = reviewed.json()["payload"]["review"]["review_id"]
        _reference, path = ProjectPreparedAudioStore(self.store).resolve(self.project_id, take["audio_id"])
        path.write_bytes(b"changed-after-review")
        self.assertEqual(self._accept(review_id).status_code, 422)

    def test_audio_policy_and_human_confirmations_fail_closed(self) -> None:
        take = self._attach_take()
        self.loudness_true_peak = -0.2
        self.assertEqual(self._review(take["take_id"]).status_code, 422)
        self.loudness_true_peak = -2.0
        for content, sync in ((False, True), (True, False), (False, False)):
            with self.subTest(content=content, sync=sync):
                self.assertEqual(self._review(take["take_id"], content=content, sync=sync).status_code, 422)

    def test_overrun_can_be_reviewed_but_not_accepted(self) -> None:
        take = self._attach_take(duration_us=2_250_000)
        self.assertEqual(self._review(take["take_id"]).status_code, 422)
        needs_revision = self._review(take["take_id"], verdict="needs_revision", content=True, sync=False)
        self.assertEqual(needs_revision.status_code, 201, needs_revision.text)
        review = needs_revision.json()["payload"]["review"]
        self.assertFalse(review["timing_pass"])
        self.assertEqual(self._accept(review["review_id"]).status_code, 422)

    def test_same_review_cannot_be_accepted_twice(self) -> None:
        take = self._attach_take()
        reviewed = self._review(take["take_id"])
        self.assertEqual(reviewed.status_code, 201, reviewed.text)
        review_id = reviewed.json()["payload"]["review"]["review_id"]
        self.assertEqual(self._accept(review_id).status_code, 201)
        self.assertEqual(self._accept(review_id).status_code, 422)

    def test_review_history_remains_durable(self) -> None:
        take = self._attach_take()
        first = self._review(take["take_id"], verdict="needs_revision", content=True, sync=False)
        second = self._review(take["take_id"])
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(len(DubbingReviewStore(self.store).load_reviews(self.project_id).reviews), 2)


if __name__ == "__main__":
    unittest.main()
