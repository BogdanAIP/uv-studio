from __future__ import annotations

import unittest
from pathlib import Path

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
from uv_studio.projects.source_media import SourceMediaError
from uv_studio.recipes import build_builtin_registry


def _registry(
    availability: OfferAvailability,
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
        locality,
        cost,
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


class StubSourceMedia:
    def __init__(self, *verified_source_ids: str) -> None:
        self.verified_source_ids = frozenset(verified_source_ids)

    def resolve_verified(self, project_id: str, source_id: str, *, expected_kind: str):
        del project_id, expected_kind
        if source_id not in self.verified_source_ids:
            raise SourceMediaError("registered source bytes are missing or corrupted")
        return (
            ProjectReference(id=source_id, kind="image", path=f"sources/{source_id}.png"),
            Path(f"sources/{source_id}.png"),
        )


class ProductOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recipes = build_builtin_registry()

    def test_photo_workflow_requires_project_images(self) -> None:
        state = project_workflow_state(
            _project(),
            self.recipes.get("photo_to_video"),
            _registry(OfferAvailability.AVAILABLE),
            StubSourceMedia(),
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
            StubSourceMedia("src_image"),
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
            StubSourceMedia(),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.UNAVAILABLE)
        self.assertEqual(
            state.next_actions[0].blocked_by,
            ("source.images", "capability.video.compose_photos"),
        )
        self.assertEqual(state.diagnostics[0].code, "capability_not_available")

    def test_readiness_uses_same_local_free_policy_as_execution(self) -> None:
        image = ProjectReference(
            id="src_image",
            kind="image",
            path="sources/image.png",
        )
        ineligible_offers = (
            {"locality": LocalityClass.REMOTE, "cost": CostClass.FREE},
            {"locality": LocalityClass.LOCAL, "cost": CostClass.PAID},
        )
        for offer_metadata in ineligible_offers:
            with self.subTest(**offer_metadata):
                state = project_workflow_state(
                    _project(sources=(image,)),
                    self.recipes.get("photo_to_video"),
                    _registry(OfferAvailability.AVAILABLE, **offer_metadata),
                    StubSourceMedia("src_image"),
                )
                self.assertEqual(state.readiness, WorkflowReadiness.UNAVAILABLE)
                self.assertFalse(state.next_actions[0].enabled)
                self.assertEqual(
                    state.next_actions[0].blocked_by,
                    ("capability.video.compose_photos",),
                )

    def test_referenced_image_requires_verified_project_media_bytes(self) -> None:
        verified_image = ProjectReference(
            id="src_image",
            kind="image",
            path="sources/image.png",
        )
        broken_image = ProjectReference(
            id="src_broken",
            kind="image",
            path="sources/broken.png",
        )
        state = project_workflow_state(
            _project(sources=(verified_image, broken_image)),
            self.recipes.get("photo_to_video"),
            _registry(OfferAvailability.AVAILABLE),
            StubSourceMedia("src_image"),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertFalse(state.next_actions[0].enabled)
        self.assertEqual(state.next_actions[0].blocked_by, ("source.images",))
        self.assertEqual(state.diagnostics[0].code, "source_media_unverified")
        self.assertIn("src_broken", state.diagnostics[0].message)
        self.assertIn("Повторно загрузите", state.prerequisites[0].resolution)

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
            StubSourceMedia(),
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
            StubSourceMedia(),
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
            StubSourceMedia(),
        )
        self.assertEqual(state.readiness, WorkflowReadiness.UNAVAILABLE)
        self.assertEqual(state.diagnostics[0].code, "recipe_unknown")


if __name__ == "__main__":
    unittest.main()
