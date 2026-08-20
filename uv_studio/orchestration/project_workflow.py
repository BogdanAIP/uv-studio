"""Project workflow projection for the first Product Orchestrator journey."""

from __future__ import annotations

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.models import ProjectDocument, ProjectReference
from uv_studio.recipes.models import RecipeDefinition

from .models import (
    ProjectWorkflowState,
    WorkflowAction,
    WorkflowArtifact,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
    WorkflowWorkspace,
)

_PHOTO_RECIPE_ID = "photo_to_video"
_PHOTO_CAPABILITY_ID = "video.compose_photos"
_PHOTO_LIFECYCLE = "photo_to_video_render"


def _artifact(reference: ProjectReference) -> WorkflowArtifact:
    return WorkflowArtifact(
        artifact_id=reference.id,
        kind=reference.kind,
        path=reference.path,
        lifecycle=str(reference.metadata.get("lifecycle", "")),
        metadata=dict(reference.metadata),
    )


def _unsupported_recipe(
    project: ProjectDocument,
    recipe: RecipeDefinition,
) -> ProjectWorkflowState:
    return ProjectWorkflowState(
        project_id=project.project_id,
        recipe_id=project.recipe_id,
        recipe_title=recipe.title,
        readiness=WorkflowReadiness.PARTIAL,
        summary="Этот сценарий ещё не перенесён в Product Orchestrator.",
        current_outcome=None,
        prerequisites=(),
        relevant_workspaces=(),
        next_actions=(),
        active_jobs=(),
        user_decisions=(),
        recent_artifacts=(),
        diagnostics=(
            WorkflowDiagnostic(
                code="workflow_not_migrated",
                severity="info",
                message=(
                    f"Recipe {project.recipe_id!r} сохраняет канонический проект, "
                    "но пока не имеет продуктовой workflow-проекции."
                ),
            ),
        ),
    )


def _photo_workflow(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
) -> ProjectWorkflowState:
    image_sources = tuple(source for source in project.sources if source.kind == "image")
    images_ready = bool(image_sources)
    capability_known = True
    capability_ready = False
    capability_configurable = False
    diagnostics: list[WorkflowDiagnostic] = []
    try:
        select_offer(
            registry,
            _PHOTO_CAPABILITY_ID,
            policy=SelectionPolicy.LOCAL_FREE_FIRST,
        )
        capability_ready = True
    except UnknownCapability:
        capability_known = False
        diagnostics.append(
            WorkflowDiagnostic(
                code="capability_unknown",
                severity="error",
                message=f"Capability {_PHOTO_CAPABILITY_ID!r} отсутствует в текущем runtime.",
            )
        )
    except NoEligibleOffer:
        capability_configurable = any(
            offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
            and offer.cost_class is CostClass.FREE
            and offer.locality is LocalityClass.LOCAL
            for offer in registry.offers_for(_PHOTO_CAPABILITY_ID)
        )

    if not capability_ready and capability_known:
        diagnostics.append(
            WorkflowDiagnostic(
                code="capability_not_available",
                severity="warning" if capability_configurable else "error",
                message=(
                    "Локальная сборка требует настройки runtime."
                    if capability_configurable
                    else "В текущем runtime нет доступного адаптера для сборки фото в видео."
                ),
            )
        )

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="source.images",
            title="Фотографии",
            explanation="Нужна хотя бы одна фотография из этого проекта.",
            satisfied=images_ready,
            resolution=None if images_ready else "Загрузите одну или несколько фотографий.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.video.compose_photos",
            title="Локальная сборка видео",
            explanation="UV Studio собирает ролик локально через зарегистрированный capability.",
            satisfied=capability_ready,
            resolution=(
                None
                if capability_ready
                else (
                    "Завершите настройку локального runtime."
                    if capability_configurable
                    else "Установите FFmpeg и FFprobe и перезапустите UV Studio."
                )
            ),
        ),
    )
    blocked_by = tuple(
        prerequisite.prerequisite_id
        for prerequisite in prerequisites
        if not prerequisite.satisfied
    )
    action = WorkflowAction(
        action_id="compose_photos",
        title="Собрать видео из фотографий",
        explanation=(
            "Собрать выбранные project-owned изображения в локальный H.264 MP4, "
            "опционально с готовой аудиодорожкой."
        ),
        enabled=not blocked_by,
        blocked_by=blocked_by,
        prerequisite_ids=tuple(item.prerequisite_id for item in prerequisites),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["image_source_ids"],
            "properties": {
                "image_source_ids": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 1,
                    "maxItems": 100,
                    "uniqueItems": True,
                },
                "duration_per_image_us": {
                    "type": "integer",
                    "minimum": 250_000,
                    "maximum": 30_000_000,
                    "default": 2_000_000,
                },
                "audio_source_id": {"type": "string", "minLength": 1},
            },
        },
        execution_class="local_deterministic",
        authorization_class="d017_exact_one_shot_if_required",
        capability_id=_PHOTO_CAPABILITY_ID,
        expected_result="video_artifact",
    )
    artifacts = tuple(
        _artifact(reference)
        for reference in reversed(project.artifacts)
        if reference.metadata.get("lifecycle") == _PHOTO_LIFECYCLE
    )

    if not capability_known or (not capability_ready and not capability_configurable):
        readiness = WorkflowReadiness.UNAVAILABLE
        summary = "Сборка фото в видео недоступна в текущем runtime."
    elif not capability_ready or not images_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = (
            "Добавьте фотографии, чтобы начать сборку."
            if capability_ready
            else "Завершите настройку локальной сборки видео."
        )
    else:
        readiness = WorkflowReadiness.READY
        summary = "Фотографии и локальная сборка готовы. Можно создать видео."

    return ProjectWorkflowState(
        project_id=project.project_id,
        recipe_id=project.recipe_id,
        recipe_title=recipe.title,
        readiness=readiness,
        summary=summary,
        current_outcome=artifacts[0] if artifacts else None,
        prerequisites=prerequisites,
        relevant_workspaces=(
            WorkflowWorkspace(
                workspace_id="photo_composition",
                title="Фотографии → видео",
                description="Порядок кадров, длительность, аудио и локальная сборка.",
            ),
        ),
        next_actions=(action,),
        active_jobs=(),
        user_decisions=(),
        recent_artifacts=artifacts[:10],
        diagnostics=tuple(diagnostics),
    )


def project_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition | None,
    registry: CapabilityRegistry,
) -> ProjectWorkflowState:
    """Project user intent into truthful readiness and semantic next actions."""

    if recipe is None:
        return ProjectWorkflowState(
            project_id=project.project_id,
            recipe_id=project.recipe_id,
            recipe_title=project.recipe_id,
            readiness=WorkflowReadiness.UNAVAILABLE,
            summary="Сценарий проекта отсутствует в текущей версии UV Studio.",
            current_outcome=None,
            prerequisites=(),
            relevant_workspaces=(),
            next_actions=(),
            active_jobs=(),
            user_decisions=(),
            recent_artifacts=(),
            diagnostics=(
                WorkflowDiagnostic(
                    code="recipe_unknown",
                    severity="error",
                    message=f"Recipe {project.recipe_id!r} не зарегистрирован в текущем runtime.",
                ),
            ),
        )
    if project.recipe_id != recipe.recipe_id:
        raise ValueError("project and recipe identifiers do not match")
    if project.recipe_id == _PHOTO_RECIPE_ID:
        return _photo_workflow(project, recipe, registry)
    return _unsupported_recipe(project, recipe)
