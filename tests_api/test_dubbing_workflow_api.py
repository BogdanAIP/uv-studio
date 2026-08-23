from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
    get_whisper_cpp_adapter,
)
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityExecutionResult,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.projects.dubbing import DubbingStore
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class StubWhisperExecutor:
    adapter_id = "local_whisper_cpp"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "source_id": payload["source_id"],
                "source_sha256": "draft-only",
                "language": payload.get("language") or "en",
                "start_us": payload.get("start_us", 0),
                "end_us": payload.get("end_us", 2_000_000),
                "segments": [
                    {
                        "segment_id": "seg_asr_001",
                        "start_us": payload.get("start_us", 0),
                        "end_us": payload.get("end_us", 2_000_000),
                        "text": "Draft speech",
                        "speaker_label": None,
                        "confidence": 0.92,
                    }
                ],
            },
        )


class StubLocalFFmpegExecutor:
    adapter_id = "local_ffmpeg"

    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        if offer.offer_id == "local_ffmpeg.audio_measure_loudness":
            reference = next(
                item
                for item in self.store.load_project(project_id).artifacts
                if item.id == payload["audio_id"]
            )
            return CapabilityExecutionResult.from_offer(
                project_id=project_id,
                offer=offer,
                output={
                    "audio_id": reference.id,
                    "audio_sha256": reference.metadata["sha256"],
                    "duration_us": reference.metadata["duration_us"],
                    "measurable": True,
                    "integrated_lufs": -20.0,
                    "true_peak_dbtp": -2.5,
                    "loudness_range_lu": 3.0,
                    "threshold_lufs": -30.0,
                },
            )
        if offer.offer_id == "local_ffmpeg.video_render_dubbing":
            return CapabilityExecutionResult.from_offer(
                project_id=project_id,
                offer=offer,
                output={
                    "path": "artifacts/dubbing-master.mkv",
                    "source_id": payload["source_id"],
                    "visual_edit_ids": [],
                    "accepted_dubbing_ids": [],
                    "composition_mode": "replace_source_audio_range",
                    "time_mapping_mode": "identity",
                    "actual_output_video_duration_us": 8_000_000,
                    "actual_output_audio_duration_us": 8_000_000,
                },
            )
        raise AssertionError(f"unexpected FFmpeg offer {offer.offer_id}")


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
    transcribe = CapabilityDefinition(
        "speech.transcribe",
        "Transcribe speech",
        "Local speech transcription draft",
        OperationKind.SPEECH,
        (MediaKind.VIDEO, MediaKind.AUDIO),
        (MediaKind.TEXT, MediaKind.METADATA),
        asynchronous=True,
    )
    ffmpeg = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    whisper = AdapterDefinition(
        "local_whisper_cpp",
        "whisper.cpp",
        "local whisper runtime",
        AdapterKind.LOCAL,
    )
    offers = (
        CapabilityOffer(
            "local_ffmpeg.video_render_dubbing",
            render.capability_id,
            ffmpeg.adapter_id,
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
            ffmpeg.adapter_id,
            "Measure loudness",
            OfferAvailability.AVAILABLE,
            "test runtime",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        ),
        CapabilityOffer(
            "local_whisper_cpp.speech_transcribe",
            transcribe.capability_id,
            whisper.adapter_id,
            "Local transcription",
            OfferAvailability.AVAILABLE,
            "test runtime",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        ),
    )
    return CapabilityRegistry((render, loudness, transcribe), (ffmpeg, whisper), offers)


class DubbingWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Dedicated Dubbing", recipe_id="dubbing")
        self.registry = _registry()
        self.ffmpeg = StubLocalFFmpegExecutor(self.store)
        self.whisper = StubWhisperExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.ffmpeg
        app.dependency_overrides[get_whisper_cpp_adapter] = lambda: self.whisper
        app.dependency_overrides[get_execution_authorization_store] = lambda: OneShotAuthorizationStore()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self, suffix: str = "workflow") -> str:
        return f"/api/uv/projects/{self.project.project_id}/{suffix}"

    def _action(self, state: dict, action_id: str) -> dict:
        return next(item for item in state["next_actions"] if item["action_id"] == action_id)

    def _add_video(self) -> tuple[str, Path]:
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project.project_id, "source.mp4")
        body = b"verified-dubbing-source"
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
                "duration_us": 8_000_000,
                "has_audio": True,
                "width": 1280,
                "height": 720,
            },
        )
        reference = next(item for item in project.sources if item.id == allocation.source_id)
        return reference.id, allocation.absolute_path

    def _add_audio(self) -> tuple[str, Path]:
        audio_store = ProjectPreparedAudioStore(self.store)
        allocation = audio_store.allocate(self.project.project_id, "take.wav")
        body = b"verified-prepared-speech"
        allocation.absolute_path.write_bytes(body)
        project = audio_store.register(
            self.project.project_id,
            allocation,
            metadata={
                "original_name": "take.wav",
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 1_900_000,
                "has_audio": True,
                "has_video": False,
                "origin": "recorded",
            },
        )
        reference = next(item for item in project.artifacts if item.id == allocation.audio_id)
        return reference.id, allocation.absolute_path

    def _accept_asr(self, source_id: str) -> dict:
        draft_response = self.client.post(
            self._url("workflow/actions/transcribe_dubbing_source"),
            json={"source_id": source_id, "language": "en", "start_us": 1_000_000, "end_us": 3_000_000},
        )
        self.assertEqual(draft_response.status_code, 200, draft_response.text)
        draft = draft_response.json()["execution"]["result"]["output"]
        self.assertEqual(DubbingStore(self.store).load(self.project.project_id).transcripts, ())
        accepted = self.client.post(
            self._url("workflow/actions/accept_asr_transcript"),
            json={
                "source_id": draft["source_id"],
                "language": draft["language"],
                "start_us": draft["start_us"],
                "end_us": draft["end_us"],
                "segments": draft["segments"],
            },
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        return accepted.json()["result"]

    def _attach_take(self, source_id: str) -> dict:
        transcript_result = self._accept_asr(source_id)
        dubbing_id = transcript_result["dubbing_id"]
        audio_id, _path = self._add_audio()
        response = self.client.post(
            self._url("workflow/actions/attach_prepared_speech"),
            json={"dubbing_id": dubbing_id, "audio_id": audio_id, "segment_id": "seg_asr_001"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]["payload"]["prepared_speech"]

    def _review(self, take_id: str, *, verdict: str, content: bool, sync: bool) -> dict:
        response = self.client.post(
            self._url("workflow/actions/review_prepared_speech"),
            json={
                "take_id": take_id,
                "verdict": verdict,
                "content_fidelity_confirmed": content,
                "synchronization_confirmed": sync,
                "note": "Reviewed in dedicated Dubbing workflow",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]["payload"]["review"]

    def test_empty_project_has_only_dubbing_workspace_and_setup_gate(self) -> None:
        state = self.client.get(self._url()).json()
        self.assertEqual(state["recipe_id"], "dubbing")
        self.assertEqual(state["readiness"], "setup_required")
        self.assertEqual(
            [item["workspace_id"] for item in state["relevant_workspaces"]],
            ["dubbing"],
        )
        self.assertFalse(self._action(state, "transcribe_dubbing_source")["enabled"])
        self.assertFalse(self._action(state, "import_dubbing_transcript")["enabled"])

    def test_asr_is_draft_until_explicit_accept_and_source_tamper_fails_closed(self) -> None:
        source_id, source_path = self._add_video()
        ready = self.client.get(self._url()).json()
        self.assertTrue(self._action(ready, "transcribe_dubbing_source")["enabled"])
        result = self._accept_asr(source_id)
        self.assertEqual(result["payload"]["transcript"]["origin"], "asr")
        self.assertEqual(len(DubbingStore(self.store).load(self.project.project_id).transcripts), 1)

        source_path.write_bytes(b"tampered-after-accept")
        blocked = self.client.get(self._url()).json()
        self.assertEqual(blocked["readiness"], "setup_required")
        self.assertFalse(self._action(blocked, "transcribe_dubbing_source")["enabled"])
        self.assertTrue(any(item["code"] == "dubbing_source_unverified" for item in blocked["diagnostics"]))

    def test_tampered_prepared_audio_is_removed_from_attach_contract(self) -> None:
        source_id, _source_path = self._add_video()
        transcript = self._accept_asr(source_id)
        audio_id, audio_path = self._add_audio()
        state = self.client.get(self._url()).json()
        attach = self._action(state, "attach_prepared_speech")
        self.assertTrue(attach["enabled"])
        self.assertEqual(attach["input_schema"]["properties"]["audio_id"]["enum"], [audio_id])

        audio_path.write_bytes(b"tampered-prepared-audio")
        blocked = self.client.get(self._url()).json()
        attach = self._action(blocked, "attach_prepared_speech")
        self.assertFalse(attach["enabled"])
        self.assertEqual(attach["input_schema"]["properties"]["audio_id"]["enum"], [])
        rejected = self.client.post(
            self._url("workflow/actions/attach_prepared_speech"),
            json={"dubbing_id": transcript["dubbing_id"], "audio_id": audio_id},
        )
        self.assertEqual(rejected.status_code, 409, rejected.text)

    def test_only_current_approved_review_can_accept_and_policy_is_server_owned(self) -> None:
        source_id, _source_path = self._add_video()
        take = self._attach_take(source_id)
        first = self._review(take["take_id"], verdict="approved", content=True, sync=True)
        current = self.client.get(self._url()).json()
        self.assertEqual(
            self._action(current, "accept_dubbing_review")["input_schema"]["properties"]["review_id"]["enum"],
            [first["review_id"]],
        )

        self._review(take["take_id"], verdict="rejected", content=False, sync=False)
        superseded = self.client.get(self._url()).json()
        accept = self._action(superseded, "accept_dubbing_review")
        self.assertFalse(accept["enabled"])
        self.assertEqual(accept["input_schema"]["properties"]["review_id"]["enum"], [])

        approved = self._review(take["take_id"], verdict="approved", content=True, sync=True)
        forbidden_policy = self.client.post(
            self._url("workflow/actions/accept_dubbing_review"),
            json={
                "review_id": approved["review_id"],
                "composition_policy": "replace_dialogue_preserve_background",
            },
        )
        self.assertEqual(forbidden_policy.status_code, 422, forbidden_policy.text)

        accepted_id = "accepted_explicit_contract_id"
        accepted = self.client.post(
            self._url("workflow/actions/accept_dubbing_review"),
            json={"review_id": approved["review_id"], "accepted_id": accepted_id},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        decision = accepted.json()["result"]["payload"]["accepted_dubbing"]
        self.assertEqual(decision["accepted_id"], accepted_id)
        self.assertEqual(decision["composition_policy"], "replace_source_audio_range")

        render_state = self.client.get(self._url()).json()
        render = self._action(render_state, "render_accepted_dubbing")
        self.assertTrue(render["enabled"])
        self.assertEqual(render["input_schema"]["properties"]["source_id"]["enum"], [source_id])
        rendered = self.client.post(
            self._url("workflow/actions/render_accepted_dubbing"),
            json={"source_id": source_id},
        )
        self.assertEqual(rendered.status_code, 200, rendered.text)
        self.assertEqual(
            rendered.json()["execution"]["result"]["capability_id"],
            "video.render_dubbing",
        )


if __name__ == "__main__":
    unittest.main()
