"""Read-only Product Orchestrator projection for the Narrated video journey."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.media_integrity import MediaIntegrityError, verify_registered_media_bytes
from uv_studio.projects.models import ProjectDocument, ProjectReference, ProjectValidationError
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import Stage8RecipeWorkspace, Stage8WorkspaceError, get_stage8_workspace
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

NARRATED_RECIPE_ID = "narrated_video"
NARRATED_WORKSPACE_ID = "narrated_video"
_RENDER_CAPABILITY_ID = "video.render_narrated"
_RENDER_LIFECYCLE = "narrated_video_render"


def _artifact(reference: ProjectReference) -> WorkflowArtifact:
    return WorkflowArtifact(
        artifact_id=reference.id,
        kind=reference.kind,
        path=reference.path,
        lifecycle=str(reference.metadata.get("lifecycle", "")),
        metadata=dict(reference.metadata),
    )


def _enum_property(values: Iterable[str], *, max_length: int = 512) -> dict[str, Any]:
    values = tuple(values)
    result: dict[str, Any] = {
        "type": "string",
        "minLength": 1,
        "maxLength": max_length,
    }
    if values:
        result["enum"] = values
    return result


def _local_free_status(
    registry: CapabilityRegistry,
    capability_id: str,
) -> tuple[bool, bool, str | None]:
    try:
        decision = select_offer(
            registry,
            capability_id,
            policy=SelectionPolicy.LOCAL_FREE_FIRST,
        )
        return True, False, decision.reason
    except UnknownCapability:
        return False, False, "capability отсутствует в текущем runtime"
    except NoEligibleOffer:
        try:
            offers = registry.offers_for(capability_id)
        except UnknownCapability:
            return False, False, "capability отсутствует в текущем runtime"
        configurable = any(
            offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
            and offer.cost_class is CostClass.FREE
            and offer.locality is LocalityClass.LOCAL
            for offer in offers
        )
        reasons = [offer.reason for offer in offers if offer.reason]
        return False, configurable, reasons[0] if reasons else "нет доступного local/free offer"


def _verified_prepared_audio(
    project: ProjectDocument,
    source_media: ProjectSourceMediaStore,
) -> tuple[tuple[ProjectReference, ...], tuple[str, ...]]:
    audio_store = ProjectPreparedAudioStore(source_media.project_store)
    verified: list[ProjectReference] = []
    invalid: list[str] = []
    for reference in project.artifacts:
        if reference.kind != "audio" or reference.metadata.get("role") != "prepared-speech":
            continue
        try:
            current, _path = audio_store.resolve_verified(project.project_id, reference.id)
        except (PreparedAudioError, ProjectStoreError):
            invalid.append(reference.id)
            continue
        verified.append(current)
    return tuple(verified), tuple(invalid)


def _current_outcome(
    project: ProjectDocument,
    workspace: Stage8RecipeWorkspace | None,
    prepared_audio: tuple[ProjectReference, ...],
    source_media: ProjectSourceMediaStore,
) -> WorkflowArtifact | None:
    if workspace is None:
        return None
    current_images = tuple(item for item in workspace.sources if item.kind == "image")
    if not current_images:
        return None
    audio_by_id = {item.id: item for item in prepared_audio}
    store = source_media.project_store

    expected_images = [
        {
            "source_id": item.source_id,
            "path": item.path,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
        }
        for item in current_images
    ]
    for reference in reversed(project.artifacts):
        if reference.kind != "video" or reference.metadata.get("lifecycle") != _RENDER_LIFECYCLE:
            continue
        if reference.metadata.get("workspace_revision_sha256") != workspace.revision_sha256:
            continue
        if reference.metadata.get("image_bindings") != expected_images:
            continue
        raw_audio = reference.metadata.get("audio_binding")
        if not isinstance(raw_audio, dict):
            continue
        audio_id = raw_audio.get("audio_id")
        current_audio = audio_by_id.get(audio_id) if isinstance(audio_id, str) else None
        if current_audio is None:
            continue
        if (
            raw_audio.get("path") != current_audio.path
            or raw_audio.get("sha256") != current_audio.metadata.get("sha256")
            or raw_audio.get("size_bytes") != current_audio.metadata.get("size_bytes")
            or raw_audio.get("duration_us") != current_audio.metadata.get("duration_us")
        ):
            continue
        try:
            output = store.resolve_project_file(
                project.project_id,
                reference.path,
                must_exist=True,
                allowed_roots=("artifacts",),
            )
            verify_registered_media_bytes(output, reference.metadata)
        except (ProjectValidationError, ProjectStoreError, MediaIntegrityError):
            continue
        return _artifact(reference)
    return None


def narrated_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project Narrated state without owning any durable workflow data."""

    diagnostics: list[WorkflowDiagnostic] = []
    store = source_media.project_store

    try:
        workspace = get_stage8_workspace(store, project.project_id)
    except (Stage8WorkspaceError, ProjectStoreError) as exc:
        workspace = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="narrated_workspace_invalid",
                severity="error",
                message=f"Narrated workspace не прошёл проверку текущих project-owned bytes: {exc}",
            )
        )

    prepared_audio, invalid_audio_ids = _verified_prepared_audio(project, source_media)
    if invalid_audio_ids:
        diagnostics.append(
            WorkflowDiagnostic(
                code="narrated_prepared_audio_unverified",
                severity="warning" if prepared_audio else "error",
                message=(
                    "Речевые дорожки исключены из Narrated, потому что их текущие bytes не прошли "
                    "проверку: " + ", ".join(invalid_audio_ids)
                ),
            )
        )

    image_bindings = tuple(
        item for item in workspace.sources if item.kind == "image"
    ) if workspace is not None else ()
    video_bindings = tuple(
        item for item in workspace.sources if item.kind == "video"
    ) if workspace is not None else ()
    if video_bindings:
        diagnostics.append(
            WorkflowDiagnostic(
                code="narrated_video_bindings_not_rendered",
                severity="info",
                message=(
                    "Видео сохранено в Narrated workspace, но текущий deterministic render использует "
                    "только изображения. Видео не будет молча включено в мастер."
                ),
            )
        )

    render_ready, render_configurable, render_reason = _local_free_status(
        registry,
        _RENDER_CAPABILITY_ID,
    )
    if not render_ready:
        diagnostics.append(
            WorkflowDiagnostic(
                code="narrated_render_runtime_unavailable",
                severity="warning" if render_configurable else "error",
                message=(
                    "Локальный Narrated render требует настройки FFmpeg runtime."
                    if render_configurable
                    else f"Локальный Narrated render недоступен: {render_reason}"
                ),
            )
        )

    workspace_ready = workspace is not None
    script_ready = bool(workspace is not None and workspace.script)
    images_ready = bool(image_bindings)
    audio_ready = bool(prepared_audio)
    current_outcome = _current_outcome(
        project,
        workspace,
        prepared_audio,
        source_media,
    )

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="narrated.workspace",
            title="Задача и рабочее пространство",
            explanation="Narrated использует сохранённый Stage 8 brief/script с точной SHA-привязкой материалов.",
            satisfied=workspace_ready,
            resolution=None if workspace_ready else "Сохраните задачу, текст диктора и выбранные материалы.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="narrated.script",
            title="Текст диктора",
            explanation="Финальный Narrated render выполняется только для явно сохранённого непустого текста.",
            satisfied=script_ready,
            resolution=None if script_ready else "Введите и сохраните текст дикторской дорожки.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="narrated.images",
            title="Изображения для визуального ряда",
            explanation="Текущий deterministic render использует SHA-проверенные изображения из Narrated workspace.",
            satisfied=images_ready,
            resolution=None if images_ready else "Добавьте хотя бы одно изображение и сохраните workspace.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="narrated.prepared_audio",
            title="Подготовленная дикторская дорожка",
            explanation="Нужен verified project-owned PreparedAudio: импортированный, записанный или TTS-promoted.",
            satisfied=audio_ready,
            resolution=(
                None
                if audio_ready
                else "Импортируйте/запишите речь либо подготовьте TTS через существующий D-017 consent flow."
            ),
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.video.render_narrated",
            title="Локальный Narrated render",
            explanation="Мастер собирается bounded local/free FFmpeg capability без клиентских путей и raw flags.",
            satisfied=render_ready,
            resolution=None if render_ready else "Настройте локальные FFmpeg/FFprobe инструменты.",
        ),
    )

    audio_ids = tuple(item.id for item in prepared_audio)
    revision_values = (workspace.revision_sha256,) if workspace is not None else ()
    action_enabled = workspace_ready and script_ready and images_ready and audio_ready and render_ready
    render_action = WorkflowAction(
        action_id="render_narrated",
        title="Собрать видео с дикторской дорожкой",
        explanation=(
            "Собрать текущую SHA-привязанную последовательность изображений под выбранный verified "
            "PreparedAudio и записать новый project-owned мастер."
        ),
        enabled=action_enabled,
        blocked_by=tuple(
            item
            for item, ready in (
                ("narrated.workspace", workspace_ready),
                ("narrated.script", script_ready),
                ("narrated.images", images_ready),
                ("narrated.prepared_audio", audio_ready),
                ("capability.video.render_narrated", render_ready),
            )
            if not ready
        ),
        prerequisite_ids=(
            "narrated.workspace",
            "narrated.script",
            "narrated.images",
            "narrated.prepared_audio",
            "capability.video.render_narrated",
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["workspace_revision_sha256", "audio_id"],
            "properties": {
                "workspace_revision_sha256": _enum_property(
                    revision_values,
                    max_length=64,
                ),
                "audio_id": _enum_property(audio_ids, max_length=128),
            },
        },
        suggested_input=(
            {
                "workspace_revision_sha256": workspace.revision_sha256,
                "audio_id": audio_ids[0],
            }
            if workspace is not None and audio_ids
            else {}
        ),
        execution_class="capability",
        authorization_class="none",
        capability_id=_RENDER_CAPABILITY_ID,
        expected_result="video",
    )

    if not render_ready and not render_configurable:
        readiness = WorkflowReadiness.UNAVAILABLE
        summary = "Narrated нельзя завершить в текущем runtime: локальный финальный рендер недоступен."
    elif not workspace_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Сохраните задачу, текст диктора и материалы Narrated workspace."
    elif not script_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Добавьте и сохраните текст дикторской дорожки."
    elif not images_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Добавьте изображения для визуального ряда и сохраните workspace."
    elif not audio_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Добавьте подготовленную project-owned дикторскую дорожку."
    elif current_outcome is not None:
        readiness = WorkflowReadiness.READY
        summary = "Текущий Narrated мастер точно соответствует workspace, изображениям и дикторской дорожке."
    else:
        readiness = WorkflowReadiness.READY
        summary = "Narrated готов к локальной сборке текущего мастера."

    recent_artifacts = tuple(
        _artifact(reference)
        for reference in project.artifacts
        if reference.kind in {"audio", "video"}
        and (
            reference.metadata.get("role") == "prepared-speech"
            or reference.metadata.get("lifecycle") == _RENDER_LIFECYCLE
        )
    )

    return ProjectWorkflowState(
        project_id=project.project_id,
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        readiness=readiness,
        summary=summary,
        current_outcome=current_outcome,
        prerequisites=prerequisites,
        relevant_workspaces=(
            WorkflowWorkspace(
                workspace_id=NARRATED_WORKSPACE_ID,
                title="Видео с дикторской дорожкой",
                description="Задача и текст → project-owned визуалы → PreparedAudio → локальный мастер.",
            ),
        ),
        next_actions=(render_action,),
        active_jobs=(),
        user_decisions=(),
        recent_artifacts=recent_artifacts,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "NARRATED_RECIPE_ID",
    "NARRATED_WORKSPACE_ID",
    "narrated_workflow_state",
]
