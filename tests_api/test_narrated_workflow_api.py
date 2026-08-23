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
)
from uv_studio.api.prepared_audio import get_prepared_audio_probe
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
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


def _narrated_registry() -> CapabilityRegistry:
    capability = CapabilityDefinition(
        "video.render_narrated",
        "Narrated video render",
        "Render verified narrated workspace",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.IMAGE, MediaKind.AUDIO),
        (MediaKind.VIDEO,),
    )
    adapter = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    offer = CapabilityOffer(
        "local_ffmpeg.video_render_narrated",
        capability.capability_id,
        adapter.adapter_id,
        "Narrated render",
        OfferAvailability.AVAILABLE,
        "test runtime",
        LocalityClass.LOCAL,
        CostClass.FREE,
        False,
    )
    return CapabilityRegistry((capability,), (adapter,), (offer,))


class StubNarratedExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"artifact_id": "art_narrated", "path": "artifacts/art_narrated.mp4"},
        )


class NarratedWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Narrated", recipe_id="narrated_video")
        self.registry = _narrated_registry()
        self.executor = StubNarratedExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = OneShotAuthorizationStore
        app.dependency_overrides[get_prepared_audio_probe] = lambda: self._probe_audio
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _probe_audio(_store, _project_id, relative_path):
        return {
            "path": relative_path,
            "duration_us": 3_000_000,
            "format_name": "wav",
            "has_video": False,
            "has_audio": True,
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "pcm_s16le",
                    "sample_fmt": "s16",
                    "sample_rate": "48000",
                    "channels": 1,
                    "channel_layout": "mono",
                }
            ],
        }

    def _add_image(self, body: bytes = b"narrated-image") -> ProjectReference:
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project.project_id, "frame.png")
        allocation.absolute_path.write_bytes(body)
        return media.register(
            self.project.project_id,
            allocation,
            media_kind="image",
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )

    def _save_workspace(self, source_id: str) -> dict:
        response = self.client.put(
            f"/api/uv/projects/{self.project.project_id}/stage8/workspace",
            json={
                "brief": "Показать процесс",
                "script": "Проверенный текст диктора.",
                "source_ids": [source_id],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["workspace"]

    def _add_prepared_audio(self, body: bytes = b"RIFF-narration") -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/prepared-audio",
            params={"filename": "narration.wav", "origin": "imported"},
            content=body,
            headers={"content-type": "audio/wav"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _workflow(self) -> dict:
        response = self.client.get(f"/api/uv/projects/{self.project.project_id}/workflow")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_projection_and_semantic_action_use_exact_current_inputs(self) -> None:
        image = self._add_image()
        workspace = self._save_workspace(image.id)
        audio = self._add_prepared_audio()

        state = self._workflow()
        self.assertEqual(state["recipe_id"], "narrated_video")
        self.assertEqual(state["readiness"], "ready")
        self.assertEqual(state["relevant_workspaces"][0]["workspace_id"], "narrated_video")
        action = state["next_actions"][0]
        self.assertEqual(action["action_id"], "render_narrated")
        self.assertTrue(action["enabled"])
        self.assertEqual(
            action["input_schema"]["properties"]["workspace_revision_sha256"]["enum"],
            [workspace["revision_sha256"]],
        )
        self.assertEqual(action["input_schema"]["properties"]["audio_id"]["enum"], [audio["id"]])

        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/workflow/actions/render_narrated",
            json={
                "workspace_revision_sha256": workspace["revision_sha256"],
                "audio_id": audio["id"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["action_id"], "render_narrated")
        self.assertEqual(
            self.executor.calls,
            [
                (
                    self.project.project_id,
                    "local_ffmpeg.video_render_narrated",
                    {
                        "workspace_revision_sha256": workspace["revision_sha256"],
                        "audio_id": audio["id"],
                    },
                )
            ],
        )

        rejected = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/workflow/actions/render_narrated",
            json={
                "workspace_revision_sha256": workspace["revision_sha256"],
                "audio_id": "aud_not_current",
            },
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["detail"]["code"], "workflow_action_input_rejected")
        self.assertEqual(len(self.executor.calls), 1)

    def test_tampered_inputs_fail_closed_before_execution(self) -> None:
        image = self._add_image()
        self._save_workspace(image.id)
        audio = self._add_prepared_audio()

        audio_path = self.store.resolve_project_file(
            self.project.project_id,
            audio["path"],
            must_exist=True,
            allowed_roots=("assets",),
        )
        audio_path.write_bytes(b"tampered-audio")
        state = self._workflow()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertEqual(state["next_actions"][0]["blocked_by"], ["narrated.prepared_audio"])
        self.assertIn(
            "narrated_prepared_audio_unverified",
            {item["code"] for item in state["diagnostics"]},
        )

        blocked = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/workflow/actions/render_narrated",
            json={"workspace_revision_sha256": "0" * 64, "audio_id": audio["id"]},
        )
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(self.executor.calls, [])

        image_reference, image_path = ProjectSourceMediaStore(self.store).resolve(
            self.project.project_id,
            image.id,
            expected_kind="image",
        )
        self.assertEqual(image_reference.id, image.id)
        image_path.write_bytes(b"tampered-image")
        state_after_image_tamper = self._workflow()
        self.assertFalse(state_after_image_tamper["next_actions"][0]["enabled"])
        self.assertIn(
            "narrated_workspace_invalid",
            {item["code"] for item in state_after_image_tamper["diagnostics"]},
        )

    def test_current_outcome_requires_current_output_bytes(self) -> None:
        image = self._add_image()
        workspace = self._save_workspace(image.id)
        audio = self._add_prepared_audio()
        output_body = b"rendered-narrated-master"
        output_path = self.store.project_directory(self.project.project_id) / "artifacts" / "art_current.mp4"
        output_path.write_bytes(output_body)

        image_binding = workspace["sources"][0]
        artifact = ProjectReference(
            id="art_current",
            kind="video",
            path="artifacts/art_current.mp4",
            metadata={
                "lifecycle": "narrated_video_render",
                "workspace_revision_sha256": workspace["revision_sha256"],
                "image_bindings": [
                    {
                        "source_id": image_binding["source_id"],
                        "path": image_binding["path"],
                        "sha256": image_binding["sha256"],
                        "size_bytes": image_binding["size_bytes"],
                    }
                ],
                "audio_binding": {
                    "audio_id": audio["id"],
                    "path": audio["path"],
                    "sha256": audio["metadata"]["sha256"],
                    "size_bytes": audio["metadata"]["size_bytes"],
                    "duration_us": audio["metadata"]["duration_us"],
                },
                "sha256": hashlib.sha256(output_body).hexdigest(),
                "size_bytes": len(output_body),
            },
        )
        current = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*current.artifacts, artifact),
        )

        state = self._workflow()
        self.assertEqual(state["current_outcome"]["artifact_id"], "art_current")
        output_path.write_bytes(b"substituted-master")
        stale = self._workflow()
        self.assertIsNone(stale["current_outcome"])


if __name__ == "__main__":
    unittest.main()
