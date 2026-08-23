from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import save_stage8_workspace
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


def _registry(
    availability: OfferAvailability = OfferAvailability.AVAILABLE,
    *,
    locality: LocalityClass = LocalityClass.LOCAL,
    cost: CostClass = CostClass.FREE,
) -> CapabilityRegistry:
    capabilities = (
        CapabilityDefinition(
            "video.compose_photos",
            "Photo composition",
            "Compose photos",
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.IMAGE, MediaKind.AUDIO),
            (MediaKind.VIDEO,),
        ),
        CapabilityDefinition(
            "audio.visualize",
            "Audio visualizer",
            "Render audio visualizer",
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.AUDIO, MediaKind.IMAGE),
            (MediaKind.VIDEO,),
        ),
    )
    adapter = AdapterDefinition(
        "local_ffmpeg",
        "Local FFmpeg",
        "Local deterministic media adapter",
        AdapterKind.LOCAL,
    )
    offers = tuple(
        CapabilityOffer(
            f"local_ffmpeg.{capability.capability_id.replace('.', '_')}",
            capability.capability_id,
            adapter.adapter_id,
            capability.name,
            availability,
            "test runtime",
            locality,
            cost,
            False,
        )
        for capability in capabilities
    )
    return CapabilityRegistry(capabilities, (adapter,), offers)


class ProjectWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Workflow", recipe_id="photo_to_video")
        self.registry = _registry()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        self.client = TestClient(app)
        self.media = ProjectSourceMediaStore(self.store)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self, *, project_id: str | None = None) -> str:
        return f"/api/uv/projects/{project_id or self.project.project_id}/workflow"

    def _add_source(self, *, project_id: str | None = None, kind: str, name: str, body: bytes):
        target_project_id = project_id or self.project.project_id
        allocation = self.media.allocate(target_project_id, name)
        allocation.absolute_path.write_bytes(body)
        updated = self.media.register(
            target_project_id,
            allocation,
            media_kind=kind,
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        reference = next(item for item in updated.sources if item.id == allocation.source_id)
        return reference, allocation.absolute_path

    def test_get_projects_truthful_readiness_and_semantic_action(self) -> None:
        initial = self.client.get(self._url())
        self.assertEqual(initial.status_code, 200, initial.text)
        state = initial.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertEqual(state["relevant_workspaces"][0]["workspace_id"], "photo_composition")
        self.assertFalse(state["next_actions"][0]["enabled"])

        image, _ = self._add_source(kind="image", name="frame.png", body=b"image")
        ready = self.client.get(self._url())
        self.assertEqual(ready.status_code, 200, ready.text)
        ready_state = ready.json()
        self.assertEqual(ready_state["readiness"], "ready")
        action = ready_state["next_actions"][0]
        self.assertTrue(action["enabled"])
        self.assertEqual(action["action_id"], "compose_photos")
        self.assertEqual(action["suggested_input"]["image_source_ids"], [image.id])

    def test_blocked_action_does_not_reach_capability_execution(self) -> None:
        with patch("uv_studio.api.project_workflow.execute_capability") as execute:
            response = self.client.post(
                f"{self._url()}/actions/compose_photos",
                json={"input": {"image_source_ids": ["missing"]}},
            )
        self.assertEqual(response.status_code, 409, response.text)
        execute.assert_not_called()

    def test_unknown_action_fails_closed(self) -> None:
        response = self.client.post(
            f"{self._url()}/actions/not_real",
            json={"input": {}},
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_action_input_is_bounded_before_execution(self) -> None:
        image, _ = self._add_source(kind="image", name="frame.png", body=b"image")
        with patch("uv_studio.api.project_workflow.execute_capability") as execute:
            response = self.client.post(
                f"{self._url()}/actions/compose_photos",
                json={
                    "input": {
                        "image_source_ids": [image.id],
                        "duration_per_image_us": 2_000_000,
                        "unexpected": True,
                    }
                },
            )
        self.assertEqual(response.status_code, 422, response.text)
        execute.assert_not_called()

    def test_semantic_action_delegates_to_existing_capability_boundary(self) -> None:
        image, _ = self._add_source(kind="image", name="frame.png", body=b"image")
        expected = {"status": "executed"}
        with patch("uv_studio.api.project_workflow.execute_capability", return_value=expected) as execute:
            response = self.client.post(
                f"{self._url()}/actions/compose_photos",
                json={
                    "input": {
                        "image_source_ids": [image.id],
                        "duration_per_image_us": 3_000_000,
                    }
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), expected)
        execute.assert_called_once()
        request = execute.call_args.args[0]
        self.assertEqual(request.capability_id, "video.compose_photos")
        self.assertEqual(request.input_payload["image_source_ids"], [image.id])

    def test_missing_registered_image_does_not_advertise_readiness(self) -> None:
        image, path = self._add_source(kind="image", name="frame.png", body=b"image")
        path.unlink()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertIn(image.id, state["diagnostics"][0]["message"])

    def test_hash_mismatched_image_does_not_advertise_readiness(self) -> None:
        image, path = self._add_source(kind="image", name="frame.png", body=b"image")
        path.write_bytes(b"changed")
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertIn(image.id, state["diagnostics"][0]["message"])

    def test_remote_available_offer_does_not_enable_local_free_action(self) -> None:
        image, _ = self._add_source(kind="image", name="frame.png", body=b"image")
        self.registry = _registry(locality=LocalityClass.REMOTE)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "unavailable")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertEqual(state["next_actions"][0]["blocked_by"], ["capability.video.compose_photos"])
        self.assertEqual(state["next_actions"][0]["suggested_input"]["image_source_ids"], [image.id])

    def test_visualizer_readiness_uses_verified_audio_and_projected_workspace(self) -> None:
        project_id = self.store.create_project(title="Visualizer", recipe_id="visualizer").project_id
        initial = self.client.get(self._url(project_id=project_id))
        self.assertEqual(initial.status_code, 200, initial.text)
        initial_state = initial.json()
        self.assertEqual(initial_state["readiness"], "setup_required")
        self.assertEqual(initial_state["relevant_workspaces"][0]["workspace_id"], "audio_visualizer")
        self.assertFalse(initial_state["next_actions"][0]["enabled"])

        audio, _ = self._add_source(
            project_id=project_id,
            kind="audio",
            name="song.wav",
            body=b"audio",
        )
        ready = self.client.get(self._url(project_id=project_id))
        self.assertEqual(ready.status_code, 200, ready.text)
        ready_state = ready.json()
        self.assertEqual(ready_state["readiness"], "ready")
        self.assertEqual(ready_state["next_actions"][0]["action_id"], "render_visualizer")
        self.assertEqual(ready_state["next_actions"][0]["suggested_input"]["audio_source_id"], audio.id)

    def test_visualizer_tampered_audio_blocks_workflow_action(self) -> None:
        project_id = self.store.create_project(title="Visualizer", recipe_id="visualizer").project_id
        audio, path = self._add_source(
            project_id=project_id,
            kind="audio",
            name="song.wav",
            body=b"audio",
        )
        path.write_bytes(b"changed")
        response = self.client.get(self._url(project_id=project_id))
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertIn(audio.id, state["diagnostics"][0]["message"])

    def test_visualizer_action_delegates_to_existing_capability_boundary(self) -> None:
        project_id = self.store.create_project(title="Visualizer", recipe_id="visualizer").project_id
        audio, _ = self._add_source(
            project_id=project_id,
            kind="audio",
            name="song.wav",
            body=b"audio",
        )
        expected = {"status": "executed"}
        with patch("uv_studio.api.project_workflow.execute_capability", return_value=expected) as execute:
            response = self.client.post(
                f"{self._url(project_id=project_id)}/actions/render_visualizer",
                json={"input": {"audio_source_id": audio.id}},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), expected)
        execute.assert_called_once()
        request = execute.call_args.args[0]
        self.assertEqual(request.capability_id, "audio.visualize")
        self.assertEqual(request.input_payload["audio_source_id"], audio.id)

    def test_visualizer_action_input_is_strict(self) -> None:
        project_id = self.store.create_project(title="Visualizer", recipe_id="visualizer").project_id
        audio, _ = self._add_source(
            project_id=project_id,
            kind="audio",
            name="song.wav",
            body=b"audio",
        )
        with patch("uv_studio.api.project_workflow.execute_capability") as execute:
            response = self.client.post(
                f"{self._url(project_id=project_id)}/actions/render_visualizer",
                json={"input": {"audio_source_id": audio.id, "raw_path": "/tmp/song.wav"}},
            )
        self.assertEqual(response.status_code, 422, response.text)
        execute.assert_not_called()

    def test_visualizer_action_rejects_source_outside_current_projection(self) -> None:
        project_id = self.store.create_project(title="Visualizer", recipe_id="visualizer").project_id
        audio, _ = self._add_source(
            project_id=project_id,
            kind="audio",
            name="song.wav",
            body=b"audio",
        )
        other, _ = self._add_source(
            project_id=project_id,
            kind="image",
            name="cover.png",
            body=b"image",
        )
        with patch("uv_studio.api.project_workflow.execute_capability") as execute:
            response = self.client.post(
                f"{self._url(project_id=project_id)}/actions/render_visualizer",
                json={"input": {"audio_source_id": other.id}},
            )
        self.assertEqual(response.status_code, 422, response.text)
        execute.assert_not_called()
        self.assertNotEqual(audio.id, other.id)

    def test_story_projection_exposes_only_verified_preparation_state(self) -> None:
        project_id = self.store.create_project(title="Story", recipe_id="story_video").project_id
        initial = self.client.get(self._url(project_id=project_id))
        self.assertEqual(initial.status_code, 200, initial.text)
        initial_state = initial.json()
        self.assertEqual(initial_state["readiness"], "setup_required")
        self.assertEqual(
            [item["workspace_id"] for item in initial_state["relevant_workspaces"]],
            ["story_video", "sequence_continuity"],
        )
        self.assertEqual(initial_state["next_actions"], [])
        self.assertIsNone(initial_state["current_outcome"])

        image, _ = self._add_source(
            project_id=project_id,
            kind="image",
            name="story.png",
            body=b"story-image",
        )
        save_stage8_workspace(
            self.store,
            project_id,
            brief="Story API brief",
            script="Story API script",
            source_ids=[image.id],
        )
        ready = self.client.get(self._url(project_id=project_id))
        self.assertEqual(ready.status_code, 200, ready.text)
        ready_state = ready.json()
        self.assertEqual(ready_state["readiness"], "ready")
        self.assertEqual(ready_state["next_actions"], [])
        self.assertIsNone(ready_state["current_outcome"])
        self.assertNotIn(
            "workflow_not_migrated",
            {item["code"] for item in ready_state["diagnostics"]},
        )

    def test_non_migrated_recipe_remains_partial_without_workspaces_or_actions(self) -> None:
        project_id = self.store.create_project(
            title="Action transfer",
            recipe_id="action_transfer",
        ).project_id
        response = self.client.get(self._url(project_id=project_id))
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "partial")
        self.assertEqual(state["relevant_workspaces"], [])
        self.assertEqual(state["next_actions"], [])
        self.assertEqual(state["diagnostics"][0]["code"], "workflow_not_migrated")


if __name__ == "__main__":
    unittest.main()
