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
    photo = CapabilityDefinition(
        "video.compose_photos",
        "Photo composition",
        "Compose photos",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.IMAGE, MediaKind.AUDIO),
        (MediaKind.VIDEO,),
    )
    visualizer = CapabilityDefinition(
        "audio.visualize",
        "Audio visualizer",
        "Render audio visualizer",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.AUDIO, MediaKind.IMAGE),
        (MediaKind.VIDEO,),
    )
    adapter = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    photo_offer = CapabilityOffer(
        "local_ffmpeg.video_compose_photos",
        photo.capability_id,
        adapter.adapter_id,
        "Photo composition",
        availability,
        "test runtime",
        locality,
        cost,
        False,
    )
    visualizer_offer = CapabilityOffer(
        "local_ffmpeg.audio_visualize",
        visualizer.capability_id,
        adapter.adapter_id,
        "Audio visualizer",
        availability,
        "test runtime",
        locality,
        cost,
        False,
    )
    return CapabilityRegistry(
        (photo, visualizer),
        (adapter,),
        (photo_offer, visualizer_offer),
    )


class StubLocalFFmpegExecutor:
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
        self.executor = StubLocalFFmpegExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = OneShotAuthorizationStore
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self, suffix: str = "workflow", *, project_id: str | None = None) -> str:
        resolved_project_id = project_id or self.project.project_id
        return f"/api/uv/projects/{resolved_project_id}/{suffix}"

    def _add_source(
        self,
        *,
        project_id: str,
        media_kind: str,
        filename: str,
        body: bytes,
    ) -> str:
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(project_id, filename)
        allocation.absolute_path.write_bytes(body)
        media.register(
            project_id,
            allocation,
            media_kind=media_kind,
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        return allocation.source_id

    def _add_image(self, *, project_id: str | None = None, body: bytes | None = None) -> str:
        return self._add_source(
            project_id=project_id or self.project.project_id,
            media_kind="image",
            filename="image.png",
            body=body or b"verified image fixture",
        )

    def _add_audio(self, project_id: str, *, body: bytes | None = None) -> str:
        return self._add_source(
            project_id=project_id,
            media_kind="audio",
            filename="audio.wav",
            body=body or b"verified audio fixture",
        )

    def _visualizer_project(self) -> str:
        return self.store.create_project(
            title="Visualizer workflow",
            recipe_id="visualizer",
        ).project_id

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

        replacement_id = self._add_image()
        recovered_response = self.client.get(self._url())
        self.assertEqual(recovered_response.status_code, 200, recovered_response.text)
        recovered = recovered_response.json()
        self.assertEqual(recovered["readiness"], "ready")
        self.assertTrue(recovered["next_actions"][0]["enabled"])
        self.assertEqual(
            recovered["next_actions"][0]["suggested_input"]["image_source_ids"],
            [replacement_id],
        )
        self.assertEqual(recovered["diagnostics"][0]["severity"], "warning")

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

    def test_visualizer_readiness_uses_verified_audio_and_projected_workspace(self) -> None:
        project_id = self._visualizer_project()

        initial = self.client.get(self._url(project_id=project_id))
        self.assertEqual(initial.status_code, 200, initial.text)
        initial_state = initial.json()
        self.assertEqual(initial_state["readiness"], "setup_required")
        self.assertEqual(
            [workspace["workspace_id"] for workspace in initial_state["relevant_workspaces"]],
            ["audio_visualizer"],
        )
        self.assertEqual(initial_state["next_actions"][0]["action_id"], "render_visualizer")
        self.assertEqual(initial_state["next_actions"][0]["blocked_by"], ["source.audio"])

        audio_id = self._add_audio(project_id)
        artwork_id = self._add_image(project_id=project_id, body=b"visualizer artwork")
        ready = self.client.get(self._url(project_id=project_id))
        self.assertEqual(ready.status_code, 200, ready.text)
        state = ready.json()
        self.assertEqual(state["readiness"], "ready")
        action = state["next_actions"][0]
        self.assertTrue(action["enabled"])
        self.assertEqual(action["capability_id"], "audio.visualize")
        self.assertEqual(action["suggested_input"], {"audio_source_id": audio_id})
        self.assertTrue(
            set(action["suggested_input"]).issubset(
                set(action["input_schema"]["properties"])
            )
        )
        self.assertIn(audio_id, action["input_schema"]["properties"]["audio_source_id"]["enum"])
        self.assertIn(
            artwork_id,
            action["input_schema"]["properties"]["artwork_source_id"]["enum"],
        )

    def test_visualizer_tampered_audio_blocks_workflow_action(self) -> None:
        project_id = self._visualizer_project()
        audio_id = self._add_audio(project_id)
        _reference, path = ProjectSourceMediaStore(self.store).resolve(
            project_id,
            audio_id,
            expected_kind="audio",
        )
        path.write_bytes(b"tampered audio")

        state_response = self.client.get(self._url(project_id=project_id))
        self.assertEqual(state_response.status_code, 200, state_response.text)
        state = state_response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertFalse(state["next_actions"][0]["enabled"])
        self.assertEqual(state["next_actions"][0]["blocked_by"], ["source.audio"])
        self.assertEqual(state["diagnostics"][0]["code"], "source_media_unverified")

        action_response = self.client.post(
            self._url("workflow/actions/render_visualizer", project_id=project_id),
            json={"audio_source_id": audio_id},
        )
        self.assertEqual(action_response.status_code, 409, action_response.text)
        self.assertEqual(self.executor.calls, [])

    def test_visualizer_action_delegates_to_existing_capability_boundary(self) -> None:
        project_id = self._visualizer_project()
        audio_id = self._add_audio(project_id)
        artwork_id = self._add_image(project_id=project_id, body=b"visualizer artwork")

        response = self.client.post(
            self._url("workflow/actions/render_visualizer", project_id=project_id),
            json={
                "audio_source_id": audio_id,
                "artwork_source_id": artwork_id,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["action_id"], "render_visualizer")
        self.assertEqual(
            payload["execution"]["selection"]["offer"]["offer_id"],
            "local_ffmpeg.audio_visualize",
        )
        self.assertEqual(
            self.executor.calls,
            [
                (
                    project_id,
                    "local_ffmpeg.audio_visualize",
                    {
                        "audio_source_id": audio_id,
                        "artwork_source_id": artwork_id,
                    },
                )
            ],
        )

    def test_visualizer_action_rejects_source_outside_current_projection(self) -> None:
        project_id = self._visualizer_project()
        valid_audio_id = self._add_audio(project_id, body=b"valid visualizer audio")
        damaged_audio_id = self._add_audio(project_id, body=b"damaged visualizer audio")
        _reference, damaged_path = ProjectSourceMediaStore(self.store).resolve(
            project_id,
            damaged_audio_id,
            expected_kind="audio",
        )
        damaged_path.write_bytes(b"tampered after registration")

        state_response = self.client.get(self._url(project_id=project_id))
        self.assertEqual(state_response.status_code, 200, state_response.text)
        action = state_response.json()["next_actions"][0]
        self.assertTrue(action["enabled"])
        self.assertEqual(
            action["input_schema"]["properties"]["audio_source_id"]["enum"],
            [valid_audio_id],
        )

        response = self.client.post(
            self._url("workflow/actions/render_visualizer", project_id=project_id),
            json={"audio_source_id": damaged_audio_id},
        )
        self.assertEqual(response.status_code, 422, response.text)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "workflow_action_input_rejected")
        self.assertEqual(detail["fields"], {"audio_source_id": damaged_audio_id})
        self.assertEqual(self.executor.calls, [])

    def test_visualizer_action_input_is_strict(self) -> None:
        project_id = self._visualizer_project()
        audio_id = self._add_audio(project_id)
        response = self.client.post(
            self._url("workflow/actions/render_visualizer", project_id=project_id),
            json={"audio_source_id": audio_id, "raw_ffmpeg": "-filter_complex attacker"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.executor.calls, [])

    def test_story_projection_exposes_only_verified_preparation_state(self) -> None:
        project_id = self.store.create_project(
            title="Story video",
            recipe_id="story_video",
        ).project_id
        initial = self.client.get(self._url(project_id=project_id))
        self.assertEqual(initial.status_code, 200, initial.text)
        initial_state = initial.json()
        self.assertEqual(initial_state["readiness"], "setup_required")
        self.assertEqual(
            [workspace["workspace_id"] for workspace in initial_state["relevant_workspaces"]],
            ["story_video"],
        )
        self.assertEqual(initial_state["next_actions"], [])
        self.assertIsNone(initial_state["current_outcome"])

        image_id = self._add_image(project_id=project_id, body=b"story-api-image")
        save_stage8_workspace(
            self.store,
            project_id,
            brief="Story API brief",
            script="Story API script",
            source_ids=[image_id],
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
