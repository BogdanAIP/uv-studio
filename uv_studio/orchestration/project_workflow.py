"""Product workflow projection over canonical project and capability state."""

from __future__ import annotations

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.models import ProjectDocument, ProjectReference
from uv_studio.projects.source_media import (
    ProjectSourceMediaStore,
    SourceMediaError,
    SourceMediaNotFound,
)
from uv_studio.projects.store import ProjectStoreError
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
_VISUALIZER_RECIPE_ID = "visualizer"
_VISUALIZER_CAPABILITY_ID = "audio.visualize"
_VISUALIZER_LIFECYCLE = "audio_visualizer_render"


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
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    image_sources = tuple(source for source in project.sources if source.kind == "image")
    verified_image_ids: list[str] = []
    unverified_image_ids: list[str] = []
    for source in image_sources:
        try:
            source_media.resolve_verified(
                project.project_id,
                source.id,
                expected_kind="image",
            )
        except (SourceMediaError, SourceMediaNotFound, ProjectStoreError):
            unverified_image_ids.append(source.id)
            continue
        verified_image_ids.append(source.id)
    images_ready = bool(verified_image_ids)
    capability_known = True
    capability_ready = False
    capability_configurable = False
    diagnostics: list[WorkflowDiagnostic] = []
    if unverified_image_ids:
        diagnostics.append(
            WorkflowDiagnostic(
                code="source_media_unverified",
                severity="warning" if images_ready else "error",
                message=(
                    "Image source исключены из сборки, потому что не прошли проверку "
                    "project-owned bytes: "
                    + ", ".join(unverified_image_ids)
                ),
            )
        )
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

    if images_ready:
        image_resolution = (
            "Повреждённые ссылки исключены из сборки; загрузите новую копию, если этот кадр нужен."
            if unverified_image_ids
            else None
        )
    elif image_sources:
        image_resolution = (
            "Загрузите новую копию фотографии: зарегистрированные файлы отсутствуют или повреждены."
        )
    else:
        image_resolution = "Загрузите одну или несколько фотографий."

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="source.images",
            title="Фотографии",
            explanation=(
                "Нужна хотя бы одна фотография, прошедшая проверку project-owned bytes."
            ),
            satisfied=images_ready,
            resolution=image_resolution,
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
        suggested_input={
            "image_source_ids": tuple(verified_image_ids),
            "duration_per_image_us": 2_000_000,
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


def _visualizer_workflow(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    audio_sources = tuple(source for source in project.sources if source.kind == "audio")
    artwork_sources = tuple(source for source in project.sources if source.kind == "image")
    verified_audio_ids: list[str] = []
    unverified_audio_ids: list[str] = []
    verified_artwork_ids: list[str] = []
    unverified_artwork_ids: list[str] = []

    for source in audio_sources:
        try:
            source_media.resolve_verified(
                project.project_id,
                source.id,
                expected_kind="audio",
            )
        except (SourceMediaError, SourceMediaNotFound, ProjectStoreError):
            unverified_audio_ids.append(source.id)
            continue
        verified_audio_ids.append(source.id)

    for source in artwork_sources:
        try:
            source_media.resolve_verified(
                project.project_id,
                source.id,
                expected_kind="image",
            )
        except (SourceMediaError, SourceMediaNotFound, ProjectStoreError):
            unverified_artwork_ids.append(source.id)
            continue
        verified_artwork_ids.append(source.id)

    audio_ready = bool(verified_audio_ids)
    capability_known = True
    capability_ready = False
    capability_configurable = False
    diagnostics: list[WorkflowDiagnostic] = []

    if unverified_audio_ids:
        diagnostics.append(
            WorkflowDiagnostic(
                code="source_media_unverified",
                severity="warning" if audio_ready else "error",
                message=(
                    "Audio source исключены из визуализатора, потому что не прошли "
                    "проверку project-owned bytes: "
                    + ", ".join(unverified_audio_ids)
                ),
            )
        )
    if unverified_artwork_ids:
        diagnostics.append(
            WorkflowDiagnostic(
                code="optional_source_media_unverified",
                severity="warning",
                message=(
                    "Повреждённые или отсутствующие изображения не предлагаются как обложка: "
                    + ", ".join(unverified_artwork_ids)
                ),
            )
        )

    try:
        select_offer(
            registry,
            _VISUALIZER_CAPABILITY_ID,
            policy=SelectionPolicy.LOCAL_FREE_FIRST,
        )
        capability_ready = True
    except UnknownCapability:
        capability_known = False
        diagnostics.append(
            WorkflowDiagnostic(
                code="capability_unknown",
                severity="error",
                message=f"Capability {_VISUALIZER_CAPABILITY_ID!r} отсутствует в текущем runtime.",
            )
        )
    except NoEligibleOffer:
        capability_configurable = any(
            offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
            and offer.cost_class is CostClass.FREE
            and offer.locality is LocalityClass.LOCAL
            for offer in registry.offers_for(_VISUALIZER_CAPABILITY_ID)
        )

    if not capability_ready and capability_known:
        diagnostics.append(
            WorkflowDiagnostic(
                code="capability_not_available",
                severity="warning" if capability_configurable else "error",
                message=(
                    "Локальный аудиовизуализатор требует настройки runtime."
                    if capability_configurable
                    else "В текущем runtime нет доступного local/free аудиовизуализатора."
                ),
            )
        )

    if audio_ready:
        audio_resolution = (
            "Повреждённые аудиоссылки исключены; выберите проверенную дорожку или загрузите новую копию."
            if unverified_audio_ids
            else None
        )
    elif audio_sources:
        audio_resolution = (
            "Загрузите новую копию аудио: зарегистрированные файлы отсутствуют или повреждены."
        )
    else:
        audio_resolution = "Загрузите master-аудио для визуализатора."

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="source.audio",
            title="Master-аудио",
            explanation="Нужна аудиодорожка, прошедшая проверку project-owned bytes.",
            satisfied=audio_ready,
            resolution=audio_resolution,
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.audio.visualize",
            title="Локальный аудиовизуализатор",
            explanation=(
                "UV Studio строит waveform-видео локально через зарегистрированный capability."
            ),
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

    audio_property: dict[str, object] = {
        "type": "string",
        "minLength": 1,
        "maxLength": 128,
    }
    if verified_audio_ids:
        audio_property["enum"] = tuple(verified_audio_ids)
    artwork_property: dict[str, object] = {
        "type": "string",
        "minLength": 1,
        "maxLength": 128,
    }
    if verified_artwork_ids:
        artwork_property["enum"] = tuple(verified_artwork_ids)

    suggested_input: dict[str, object] = {}
    if verified_audio_ids:
        suggested_input["audio_source_id"] = verified_audio_ids[0]

    action = WorkflowAction(
        action_id="render_visualizer",
        title="Собрать аудиовизуализатор",
        explanation=(
            "Построить локальный waveform-видеоряд из проверенного master-аудио, "
            "опционально используя проверенную project-owned обложку."
        ),
        enabled=not blocked_by,
        blocked_by=blocked_by,
        prerequisite_ids=tuple(item.prerequisite_id for item in prerequisites),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["audio_source_id"],
            "properties": {
                "audio_source_id": audio_property,
                "artwork_source_id": artwork_property,
            },
        },
        suggested_input=suggested_input,
        execution_class="local_deterministic",
        authorization_class="d017_exact_one_shot_if_required",
        capability_id=_VISUALIZER_CAPABILITY_ID,
        expected_result="video_artifact",
    )
    artifacts = tuple(
        _artifact(reference)
        for reference in reversed(project.artifacts)
        if reference.metadata.get("lifecycle") == _VISUALIZER_LIFECYCLE
    )

    if not capability_known or (not capability_ready and not capability_configurable):
        readiness = WorkflowReadiness.UNAVAILABLE
        summary = "Аудиовизуализатор недоступен в текущем runtime."
    elif not capability_ready or not audio_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = (
            "Добавьте master-аудио, чтобы собрать визуализатор."
            if capability_ready
            else "Завершите настройку локального аудиовизуализатора."
        )
    else:
        readiness = WorkflowReadiness.READY
        summary = "Master-аудио и локальный визуализатор готовы. Можно создать видео."

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
                workspace_id="audio_visualizer",
                title="Аудио → визуализатор",
                description="Master-аудио, необязательная обложка и локальная waveform-сборка.",
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
    source_media: ProjectSourceMediaStore,
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
        return _photo_workflow(project, recipe, registry, source_media)
    if project.recipe_id == _VISUALIZER_RECIPE_ID:
        return _visualizer_workflow(project, recipe, registry, source_media)
    if project.recipe_id == "music_video":
        from .music import music_workflow_state

        return music_workflow_state(project, recipe, registry, source_media)
    return _unsupported_recipe(project, recipe)