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


def _general_registry() -> CapabilityRegistry:
    capability = CapabilityDefinition(
        "video.render_general",
        "General Video render",
        "Render verified General Video workspace",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.IMAGE, MediaKind.VIDEO, MediaKind.AUDIO),
        (MediaKind.VIDEO,),
    )
    adapter = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    offer = CapabilityOffer(
        "local_ffmpeg.video_render_general",
        capability.capability_id,
        adapter.adapter_id,
        "General Video render",
        OfferAvailability.AVAILABLE,
        "test runtime",
        LocalityClass.LOCAL,
        CostClass.FREE,
        False,
    )
    return CapabilityRegistry((capability,), (adapter,), (offer,))


class StubGeneralExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"artifact_id": "art_general", "path": "artifacts/art_general.mp4"},
        )


class GeneralVideoWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="General Video", recipe_id="general_video")
        self.registry = _general_registry()
        self.executor = StubGeneralExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = OneShotAuthorizationStore
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _add_source(self, name: str, kind: str, body: bytes) -> ProjectReference:
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project.project_id, name)
        allocation.absolute_path.write_bytes(body)
        updated = media.register(
            self.project.project_id,
            allocation,
            media_kind=kind,
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        return next(item for item in updated.sources if item.id == allocation.source_id)

    def _save_workspace(self, source_ids: list[str]) -> dict:
        response = self.client.put(
            f"/api/uv/projects/{self.project.project_id}/stage8/workspace",
            json={
                "brief": "Собрать демонстрационный ролик",
                "script": "Необязательный текст проекта",
                "source_ids": source_ids,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["workspace"]

    def _workflow(self) -> dict:
        response = self.client.get(f"/api/uv/projects/{self.project.project_id}/workflow")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_projection_and_semantic_action_use_exact_workspace_revision(self) -> None:
        image = self._add_source("frame.png", "image", b"general-image")
        workspace = self._save_workspace([image.id])

        state = self._workflow()
        self.assertEqual(state["recipe_id"], "general_video")
        self.assertEqual(state["readiness"], "ready")
        self.assertEqual(state["relevant_workspaces"][0]["workspace_id"], "general_video")
        action = state["next_actions"][0]
        self.assertEqual(action["action_id"], "render_general")
        self.assertTrue(action["enabled"])
        self.assertEqual(
            action["input_schema"]["properties"]["workspace_revision_sha256"]["enum"],
            [workspace["revision_sha256"]],
        )

        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/workflow/actions/render_general",
            json={"workspace_revision_sha256": workspace["revision_sha256"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["action_id"], "render_general")
        self.assertEqual(
            self.executor.calls,
            [
                (
                    self.project.project_id,
                    "local_ffmpeg.video_render_general",
                    {"workspace_revision_sha256": workspace["revision_sha256"]},
                )
            ],
        )

        rejected = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/workflow/actions/render_general",
            json={"workspace_revision_sha256": "0" * 64},
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["detail"]["code"], "workflow_action_input_rejected")
        self.assertEqual(len(self.executor.calls), 1)

    def test_multiple_audio_and_tampered_visual_fail_closed(self) -> None:
        image = self._add_source("frame.png", "image", b"general-image")
        audio_a = self._add_source("a.wav", "audio", b"audio-a")
        audio_b = self._add_source("b.wav", "audio", b"audio-b")
        workspace = self._save_workspace([image.id, audio_a.id, audio_b.id])

        state = self._workflow()
        self.assertEqual(state["readiness"], "setup_required")
        action = state["next_actions"][0]
        self.assertFalse(action["enabled"])
        self.assertIn("general.audio", action["blocked_by"])
        self.assertIn(
            "general_video_multiple_audio_tracks",
            {item["code"] for item in state["diagnostics"]},
        )

        blocked = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/workflow/actions/render_general",
            json={"workspace_revision_sha256": workspace["revision_sha256"]},
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
        state_after_tamper = self._workflow()
        self.assertFalse(state_after_tamper["next_actions"][0]["enabled"])
        self.assertIn(
            "general_video_workspace_invalid",
            {item["code"] for item in state_after_tamper["diagnostics"]},
        )

    def test_current_outcome_requires_exact_workspace_and_output_bytes(self) -> None:
        image = self._add_source("frame.png", "image", b"general-image")
        workspace = self._save_workspace([image.id])
        output_body = b"rendered-general-master"
        output_path = self.store.project_directory(self.project.project_id) / "artifacts" / "art_current.mp4"
        output_path.write_bytes(output_body)

        binding = workspace["sources"][0]
        artifact = ProjectReference(
            id="art_current",
            kind="video",
            path="artifacts/art_current.mp4",
            metadata={
                "lifecycle": "general_video_render",
                "workspace_revision_sha256": workspace["revision_sha256"],
                "visual_bindings": [
                    {
                        "source_id": binding["source_id"],
                        "kind": binding["kind"],
                        "path": binding["path"],
                        "sha256": binding["sha256"],
                        "size_bytes": binding["size_bytes"],
                        "duration_us": 2_000_000,
                        "embedded_audio_ignored": False,
                    }
                ],
                "audio_binding": None,
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
