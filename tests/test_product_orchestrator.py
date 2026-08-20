from __future__ import annotations

import unittest

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
from uv_studio.orchestration import WorkflowReadiness, project_workflow_state
from uv_studio.projects.models import ProjectDocument, ProjectReference
from uv_studio.recipes import build_builtin_registry


def _registry(availability: OfferAvailability) -> CapabilityRegistry:
    capability = CapabilityDefinition(
        "video.compose_photos",
        "Photo composition",
        "Compose photos",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.IMAGE, MediaKind.AUDIO),
        (MediaKind.VIDEO,),
    )
    adapter = AdapterDefinition(
        "local_ffmpeg",
        "Local FFmpeg",
        "Local deterministic media adapter",
        AdapterKind.LOCAL,
    )
    offer = CapabilityOffer(
        "local_ffmpeg.video_compose_photos",
        capability.capability_id,
        adapter.adapter_id,
        "Local photo composition",
        availability,
        "test runtime",
        LocalityClass.LOCAL,
        CostClass.FREE,
        False,
    )
    return CapabilityRegistry((capability,), (adapter,), (offer,))


def _project(*, sources=(), artifacts=(), recipe_id: str = "photo_to_video") -> ProjectDocument:
    return ProjectDocument(
        project_id="prj_workflow",
        title="Workflow",
        recipe_id=recipe_id,
        created_at="2026-08-20T00:00:00Z",
        updated_at="2026-08-20T00:00:00Z",
        sources=tuple(sources),
        artifacts=tuple(artifacts),
    )


class ProductOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recipes = build_builtin_registry()

    def test_photo_workflow_requires_project_images(self) -> None:
        state = project_workflow_state(
            _project(),
            self.recipes.get("photo_to_video"),
            _registry(OfferAvailability.AVAILABLE),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertEqual(state.relevant_workspaces[0].workspace_id, "photo_composition")
        action = state.next_actions[0]
        self.assertFalse(action.enabled)
        self.assertEqual(action.blocked_by, ("source.images",))

    def test_photo_workflow_is_ready_with_images_and_available_capability(self) -> None:
        image = ProjectReference(
            id="src_image",
            kind="image",
            path="sources/image.png",
        )
        state = project_workflow_state(
            _project(sources=(image,)),
            self.recipes.get("photo_to_video"),
            _registry(OfferAvailability.AVAILABLE),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.READY)
        self.assertTrue(state.next_actions[0].enabled)
        self.assertEqual(state.next_actions[0].capability_id, "video.compose_photos")
        self.assertEqual(state.next_actions[0].execution_class, "local_deterministic")

    def test_runtime_unavailability_is_separate_from_missing_inputs(self) -> None:
        state = project_workflow_state(
            _project(),
            self.recipes.get("photo_to_video"),
            _registry(OfferAvailability.UNAVAILABLE),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.UNAVAILABLE)
        self.assertEqual(
            state.next_actions[0].blocked_by,
            ("source.images", "capability.video.compose_photos"),
        )
        self.assertEqual(state.diagnostics[0].code, "capability_not_available")

    def test_latest_photo_artifact_becomes_current_outcome(self) -> None:
        old = ProjectReference(
            id="art_old",
            kind="video",
            path="artifacts/old.mp4",
            metadata={"lifecycle": "photo_to_video_render"},
        )
        newest = ProjectReference(
            id="art_new",
            kind="video",
            path="artifacts/new.mp4",
            metadata={"lifecycle": "photo_to_video_render"},
        )
        state = project_workflow_state(
            _project(artifacts=(old, newest)),
            self.recipes.get("photo_to_video"),
            _registry(OfferAvailability.AVAILABLE),
        )
        self.assertEqual(state.current_outcome.artifact_id, "art_new")
        self.assertEqual(
            [item.artifact_id for item in state.recent_artifacts],
            ["art_new", "art_old"],
        )

    def test_unmigrated_recipe_fails_closed_without_irrelevant_workspaces(self) -> None:
        project = _project(recipe_id="general_video")
        state = project_workflow_state(
            project,
            self.recipes.get("general_video"),
            _registry(OfferAvailability.AVAILABLE),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.PARTIAL)
        self.assertEqual(state.relevant_workspaces, ())
        self.assertEqual(state.next_actions, ())
        self.assertEqual(state.diagnostics[0].code, "workflow_not_migrated")

    def test_unknown_recipe_is_recoverable_but_unavailable(self) -> None:
        state = project_workflow_state(
            _project(recipe_id="future_recipe"),
            None,
            _registry(OfferAvailability.AVAILABLE),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.UNAVAILABLE)
        self.assertEqual(state.diagnostics[0].code, "recipe_unknown")


if __name__ == "__main__":
    unittest.main()
