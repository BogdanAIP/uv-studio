from __future__ import annotations

import tempfile
import unittest
import hashlib
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
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


def _registry(
    availability: OfferAvailability = OfferAvailability.AVAILABLE,
    *,
    locality: LocalityClass = LocalityClass.LOCAL,
    cost: CostClass = CostClass.FREE,
) -> CapabilityRegistry:
    capability = CapabilityDefinition(
        "video.compose_photos",
        "Photo composition",
        "Compose photos",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.IMAGE, MediaKind.AUDIO),
        (MediaKind.VIDEO,),
    )
    adapter = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    offer = CapabilityOffer(
        "local_ffmpeg.video_compose_photos",
        capability.capability_id,
        adapter.adapter_id,
        "Photo composition",
        availability,
        "test runtime",
        locality,
        cost,
        False,
    )
    return CapabilityRegistry((capability,), (adapter,), (offer,))


class StubPhotoExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"artifact_id": "art_test", "path": "artifacts/art_test.mp4"},
        )


class ProjectWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Photo workflow",
            recipe_id="photo_to_video",
        )
        self.registry = _registry()
        self.executor = StubPhotoExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = OneShotAuthorizationStore
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self, suffix: str = "workflow") -> str:
        return f"/api/uv/projects/{self.project.project_id}/{suffix}"

    def _add_image(self) -> str:
        body = b"verified image fixture"
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project.project_id, "image.png")
        allocation.absolute_path.write_bytes(body)
        media.register(
            self.project.project_id,
            allocation,
            media_kind="image",
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        return allocation.source_id

    def test_get_projects_truthful_readiness_and_semantic_action(self) -> None:
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["readiness"], "setup_required")
        self.assertEqual(state["relevant_workspaces"][0]["workspace_id"], "photo_composition")
        self.assertEqual(state["next_actions"][0]["action_id"], "compose_photos")
        self.assertFalse(state["next_actions"][0]["enabled"])

    def test_blocked_action_does_not_reach_capability_execution(self) -> None:
        response = self.client.post(
            self._url("workflow/actions/compose_photos"),
            json={"image_source_ids": ["src_image"]},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "workflow_action_blocked")
        self.assertEqual(self.executor.calls, [])

    def test_remote_available_offer_does_not_enable_local_free_action(self) -> None:
        self.registry = _registry(locality=LocalityClass.REMOTE)
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        source_id = self._add_image()

        state_response = self.client.get(self._url())
        self.assertEqual(state_response.status_code, 200, state_response.text)
        self.assertEqual(state_response.json()["readiness"], "unavailable")
        self.assertFalse(state_response.json()["next_actions"][0]["enabled"])

        action_response = self.client.post(
            self._url("workflow/actions/compose_photos"),
            json={"image_source_ids": [source_id]},
        )
        self.assertEqual(action_response.status_code, 409, action_response.text)
        self.assertEqual(action_response.json()["detail"]["code"], "workflow_action_blocked")
        self.assertEqual(self.executor.calls, [])

    def test_missing_registered_image_does_not_advertise_readiness(self) -> None:
        source_id = self._add_image()
        _reference, path = ProjectSourceMediaStore(self.store).resolve(
            self.project.project_id,
            source_id,
            expected_kind="image",
        )
        path.unlink()

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertEqual(state["next_actions"][0]["blocked_by"], ["source.images"])
        self.assertEqual(state["diagnostics"][0]["code"], "source_media_unverified")

    def test_hash_mismatched_image_does_not_advertise_readiness(self) -> None:
        source_id = self._add_image()
        _reference, path = ProjectSourceMediaStore(self.store).resolve(
            self.project.project_id,
            source_id,
            expected_kind="image",
        )
        path.write_bytes(b"tampered image fixture")

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertEqual(state["diagnostics"][0]["code"], "source_media_unverified")

    def test_semantic_action_delegates_to_existing_capability_boundary(self) -> None:
        source_id = self._add_image()
        response = self.client.post(
            self._url("workflow/actions/compose_photos"),
            json={
                "image_source_ids": [source_id],
                "duration_per_image_us": 3_000_000,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["action_id"], "compose_photos")
        self.assertEqual(
            payload["execution"]["selection"]["offer"]["offer_id"],
            "local_ffmpeg.video_compose_photos",
        )
        self.assertEqual(
            self.executor.calls,
            [
                (
                    self.project.project_id,
                    "local_ffmpeg.video_compose_photos",
                    {
                        "image_source_ids": [source_id],
                        "duration_per_image_us": 3_000_000,
                    },
                )
            ],
        )

    def test_action_input_is_bounded_before_execution(self) -> None:
        source_id = self._add_image()
        response = self.client.post(
            self._url("workflow/actions/compose_photos"),
            json={"image_source_ids": [source_id, source_id]},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.executor.calls, [])

    def test_unknown_action_fails_closed(self) -> None:
        source_id = self._add_image()
        response = self.client.post(
            self._url("workflow/actions/legacy_pipeline"),
            json={"image_source_ids": [source_id]},
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.executor.calls, [])


if __name__ == "__main__":
    unittest.main()
