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
        allocation.absolute_path.write_bytes(b"source-video")
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "source.mp4",
                "content_type": "video/mp4",
                "size_bytes": 12,
                "sha256": "2" * 64,
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

    def _measure_loudness(self, _project_id: str, audio_id: str):
        reference = next(
            item for item in self.store.load_project(self.project_id).artifacts if item.id == audio_id
        )
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
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 1_000_000,
                "end_us": 6_000_000,
                "segments": [
                    {
                        "segment_id": "seg_001",
                        "start_us": 1_000_000,
                        "end_us": 3_000_000,
                        "text": "First line",
                    },
                    {
                        "segment_id": "seg_002",
                        "start_us": 3_500_000,
                        "end_us": 5_500_000,
                        "text": "Second line",
                    },
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
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "attach_prepared_speech",
                "dubbing_id": transcript["dubbing_id"],
                "audio_id": audio.id,
                "segment_id": "seg_001",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["payload"]["prepared_speech"]

    def _review(self, take_id: str, *, verdict: str = "approved", content=True, sync=True):
        return self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "review_prepared_speech",
                "take_id": take_id,
                "verdict": verdict,
                "content_fidelity_confirmed": content,
                "synchronization_confirmed": sync,
                "note": "Reviewed against the selected dialogue segment",
            },
        )

    def test_approved_review_uses_server_loudness_and_acceptance_revalidates_exact_state(self) -> None:
        take = self._attach_take()
        reviewed = self._review(take["take_id"])
        self.assertEqual(reviewed.status_code, 201, reviewed.text)
        review = reviewed.json()["payload"]["review"]
        self.assertTrue(review["review_id"].startswith("dreview_"))
        self.assertEqual(review["take_id"], take["take_id"])
        self.assertEqual(review["take_sha256"], DubbingReviewStore(self.store).validate_review(
            self.project_id, review["review_id"]
        ).take_sha256)
        self.assertEqual(review["target_start_us"], 1_000_000)
        self.assertEqual(review["target_end_us"], 3_000_000)
        self.assertEqual(review["audio_duration_us"], 1_850_000)
        self.assertEqual(review["timing_delta_us"], -150_000)
        self.assertTrue(review["timing_pass"])
        self.assertTrue(review["audio_safety_pass"])
        self.assertEqual(review["loudness"]["integrated_lufs"], -20.0)
        self.assertEqual(review["loudness"]["true_peak_dbtp"], -2.0)
        self.assertTrue(review["content_fidelity_confirmed"])
        self.assertTrue(review["synchronization_confirmed"])
        self.assertEqual(review["verdict"], "approved")

        accepted = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_review",
                "review_id": review["review_id"],
                "composition_policy": "replace_source_audio_range",
            },
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        edit = accepted.json()["payload"]["accepted_dubbing"]
        self.assertTrue(edit["accepted_id"].startswith("dedit_"))
        self.assertEqual(edit["review_id"], review["review_id"])
        self.assertEqual(edit["take_id"], take["take_id"])
        self.assertEqual(edit["source_id"], self.source.id)
        self.assertEqual(edit["audio_id"], take["audio_id"])
        self.assertEqual(edit["target_start_us"], 1_000_000)
        self.assertEqual(edit["target_end_us"], 3_000_000)
        self.assertEqual(edit["composition_policy"], "replace_source_audio_range")

        state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(state.status_code, 200, state.text)
        self.assertEqual(state.json()["dubbing_reviews"][0]["review_id"], review["review_id"])
        self.assertEqual(state.json()["accepted_dubbing"][0]["accepted_id"], edit["accepted_id"])

    def test_approved_review_fails_when_true_peak_exceeds_policy(self) -> None:
        take = self._attach_take()
        self.loudness_true_peak = -0.2
        reviewed = self._review(take["take_id"])
        self.assertEqual(reviewed.status_code, 422, reviewed.text)
        self.assertEqual(DubbingReviewStore(self.store).load_reviews(self.project_id).reviews, ())

    def test_approved_review_fails_when_audio_overruns_target_but_needs_revision_is_stored(self) -> None:
        take = self._attach_take(duration_us=2_250_000)
        approved = self._review(take["take_id"])
        self.assertEqual(approved.status_code, 422, approved.text)

        needs_revision = self._review(
            take["take_id"], verdict="needs_revision", content=True, sync=False
        )
        self.assertEqual(needs_revision.status_code, 201, needs_revision.text)
        review = needs_revision.json()["payload"]["review"]
        self.assertFalse(review["timing_pass"])
        self.assertEqual(review["timing_delta_us"], 250_000)

        accepted = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_review",
                "review_id": review["review_id"],
                "composition_policy": "replace_source_audio_range",
            },
        )
        self.assertEqual(accepted.status_code, 422, accepted.text)

    def test_approved_review_requires_explicit_human_content_and_sync_confirmation(self) -> None:
        take = self._attach_take()
        for content, sync in ((False, True), (True, False), (False, False)):
            with self.subTest(content=content, sync=sync):
                response = self._review(take["take_id"], content=content, sync=sync)
                self.assertEqual(response.status_code, 422, response.text)

    def test_client_cannot_supply_loudness_hashes_or_target_timing(self) -> None:
        take = self._attach_take()
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "review_prepared_speech",
                "take_id": take["take_id"],
                "verdict": "approved",
                "content_fidelity_confirmed": True,
                "synchronization_confirmed": True,
                "loudness": {"true_peak_dbtp": -20},
                "audio_sha256": "f" * 64,
                "target_start_us": 0,
                "target_end_us": 999_000_000,
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(DubbingReviewStore(self.store).load_reviews(self.project_id).reviews, ())

    def test_same_review_or_take_cannot_be_accepted_twice(self) -> None:
        take = self._attach_take()
        reviewed = self._review(take["take_id"])
        self.assertEqual(reviewed.status_code, 201, reviewed.text)
        review_id = reviewed.json()["payload"]["review"]["review_id"]
        first = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_review",
                "review_id": review_id,
                "composition_policy": "replace_source_audio_range",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        second = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_review",
                "review_id": review_id,
                "composition_policy": "replace_source_audio_range",
            },
        )
        self.assertEqual(second.status_code, 422, second.text)


if __name__ == "__main__":
    unittest.main()
