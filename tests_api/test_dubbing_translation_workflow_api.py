from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.projects.dubbing import DubbingStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


def _registry() -> CapabilityRegistry:
    render = CapabilityDefinition(
        "video.render_dubbing",
        "Render accepted dubbing",
        "Materialize accepted Dubbing edits",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.VIDEO,),
        (MediaKind.VIDEO,),
    )
    loudness = CapabilityDefinition(
        "audio.measure_loudness",
        "Measure loudness",
        "Measure project-owned prepared audio",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.AUDIO,),
        (MediaKind.METADATA,),
    )
    adapter = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    offers = (
        CapabilityOffer(
            "local_ffmpeg.video_render_dubbing",
            render.capability_id,
            adapter.adapter_id,
            "Render Dubbing",
            OfferAvailability.AVAILABLE,
            "test runtime",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        ),
        CapabilityOffer(
            "local_ffmpeg.audio_measure_loudness",
            loudness.capability_id,
            adapter.adapter_id,
            "Measure loudness",
            OfferAvailability.AVAILABLE,
            "test runtime",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        ),
    )
    return CapabilityRegistry((render, loudness), (adapter,), offers)


class DubbingTranslationWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Dubbing translation", recipe_id="dubbing")
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = _registry
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self, suffix: str = "workflow") -> str:
        return f"/api/uv/projects/{self.project.project_id}/{suffix}"

    def _action(self, state: dict, action_id: str) -> dict:
        return next(item for item in state["next_actions"] if item["action_id"] == action_id)

    def _add_video(self) -> str:
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project.project_id, "source.mp4")
        body = b"verified-dubbing-translation-source"
        allocation.absolute_path.write_bytes(body)
        project = media.register(
            self.project.project_id,
            allocation,
            media_kind="video",
            metadata={
                "original_name": "source.mp4",
                "content_type": "video/mp4",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 5_000_000,
                "has_audio": True,
                "width": 1280,
                "height": 720,
            },
        )
        return next(item.id for item in project.sources if item.id == allocation.source_id)

    def test_save_translation_is_projected_and_round_trips_through_orchestrator(self) -> None:
        source_id = self._add_video()
        transcript = self.client.post(
            self._url("workflow/actions/import_dubbing_transcript"),
            json={
                "source_id": source_id,
                "language": "en",
                "start_us": 1_000_000,
                "end_us": 3_000_000,
                "segments": [
                    {
                        "segment_id": "seg_001",
                        "start_us": 1_000_000,
                        "end_us": 3_000_000,
                        "text": "hello world",
                        "speaker_label": None,
                        "confidence": None,
                    }
                ],
            },
        )
        self.assertEqual(transcript.status_code, 200, transcript.text)
        dubbing_id = transcript.json()["result"]["dubbing_id"]

        state = self.client.get(self._url()).json()
        action = self._action(state, "save_dubbing_translation")
        self.assertTrue(action["enabled"])
        self.assertEqual(action["input_schema"]["properties"]["dubbing_id"]["enum"], [dubbing_id])

        saved = self.client.post(
            self._url("workflow/actions/save_dubbing_translation"),
            json={
                "dubbing_id": dubbing_id,
                "target_language": "ru",
                "segments": [{"segment_id": "seg_001", "text": "привет мир"}],
            },
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        result = saved.json()["result"]
        self.assertEqual(result["command"], "upsert_dubbing_translation")
        translation = result["payload"]["translation"]
        translation_id = translation["translation_id"]
        self.assertEqual(translation["dubbing_id"], dubbing_id)
        self.assertEqual(translation["target_language"], "ru")
        self.assertEqual(translation["segments"], [{"segment_id": "seg_001", "text": "привет мир"}])

        projected = self.client.get(self._url()).json()
        update_action = self._action(projected, "save_dubbing_translation")
        self.assertEqual(
            update_action["input_schema"]["properties"]["translation_id"]["enum"],
            [translation_id],
        )

        updated = self.client.post(
            self._url("workflow/actions/save_dubbing_translation"),
            json={
                "dubbing_id": dubbing_id,
                "translation_id": translation_id,
                "target_language": "ru",
                "segments": [{"segment_id": "seg_001", "text": "привет, мир"}],
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        current = DubbingStore(self.store).validate_project(self.project.project_id)
        self.assertEqual(len(current.translations), 1)
        self.assertEqual(current.translations[0].translation_id, translation_id)
        self.assertEqual(current.translations[0].segments[0].text, "привет, мир")

        rejected = self.client.post(
            self._url("workflow/actions/save_dubbing_translation"),
            json={
                "dubbing_id": "dub_missing",
                "target_language": "ru",
                "segments": [{"segment_id": "seg_001", "text": "не должно сохраниться"}],
            },
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["detail"]["code"], "workflow_action_input_rejected")


if __name__ == "__main__":
    unittest.main()
