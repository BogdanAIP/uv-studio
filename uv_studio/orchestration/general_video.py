"""Read-only Product Orchestrator projection for the General Video journey."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.media_integrity import MediaIntegrityError, verify_registered_media_bytes
from uv_studio.projects.models import ProjectDocument, ProjectReference, ProjectValidationError
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

GENERAL_VIDEO_RECIPE_ID = "general_video"
GENERAL_VIDEO_WORKSPACE_ID = "general_video"
_RENDER_CAPABILITY_ID = "video.render_general"
_RENDER_LIFECYCLE = "general_video_render"


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


def _expected_binding(binding) -> dict[str, Any]:
    return {
        "source_id": binding.source_id,
        "kind": binding.kind,
        "path": binding.path,
        "sha256": binding.sha256,
        "size_bytes": binding.size_bytes,
    }


def _current_outcome(
    project: ProjectDocument,
    workspace: Stage8RecipeWorkspace | None,
    source_media: ProjectSourceMediaStore,
) -> WorkflowArtifact | None:
    if workspace is None:
        return None
    visual_bindings = tuple(item for item in workspace.sources if item.kind in {"image", "video"})
    audio_bindings = tuple(item for item in workspace.sources if item.kind == "audio")
    if not visual_bindings or len(audio_bindings) > 1:
        return None

    expected_visuals = [_expected_binding(item) for item in visual_bindings]
    expected_audio = (
        {
            "source_id": audio_bindings[0].source_id,
            "path": audio_bindings[0].path,
            "sha256": audio_bindings[0].sha256,
            "size_bytes": audio_bindings[0].size_bytes,
        }
        if audio_bindings
        else None
    )
    store = source_media.project_store

    for reference in reversed(project.artifacts):
        if reference.kind != "video" or reference.metadata.get("lifecycle") != _RENDER_LIFECYCLE:
            continue
        if reference.metadata.get("workspace_revision_sha256") != workspace.revision_sha256:
            continue
        raw_visuals = reference.metadata.get("visual_bindings")
        if not isinstance(raw_visuals, list) or len(raw_visuals) != len(expected_visuals):
            continue
        projected_visuals = [
            {
                "source_id": item.get("source_id"),
                "kind": item.get("kind"),
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "size_bytes": item.get("size_bytes"),
            }
            for item in raw_visuals
            if isinstance(item, dict)
        ]
        if projected_visuals != expected_visuals:
            continue
        if reference.metadata.get("audio_binding") != expected_audio:
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


def general_video_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project General Video truth without introducing another durable workflow store."""

    diagnostics: list[WorkflowDiagnostic] = []
    store = source_media.project_store

    try:
        workspace = get_stage8_workspace(store, project.project_id)
    except (Stage8WorkspaceError, ProjectStoreError) as exc:
        workspace = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="general_video_workspace_invalid",
                severity="error",
                message=(
                    "General Video workspace не прошёл проверку текущих project-owned bytes: "
                    f"{exc}"
                ),
            )
        )

    visual_bindings = tuple(
        item for item in workspace.sources if item.kind in {"image", "video"}
    ) if workspace is not None else ()
    video_bindings = tuple(
        item for item in workspace.sources if item.kind == "video"
    ) if workspace is not None else ()
    audio_bindings = tuple(
        item for item in workspace.sources if item.kind == "audio"
    ) if workspace is not None else ()

    if video_bindings:
        diagnostics.append(
            WorkflowDiagnostic(
                code="general_video_embedded_audio_ignored",
                severity="info",
                message=(
                    "Текущий deterministic General Video render использует видеоклипы как визуальный ряд. "
                    "Их встроенный звук не переносится; для master-аудио выберите одну отдельную "
                    "project-owned аудиодорожку в workspace."
                ),
            )
        )
    if len(audio_bindings) > 1:
        diagnostics.append(
            WorkflowDiagnostic(
                code="general_video_multiple_audio_tracks",
                severity="warning",
                message=(
                    "Выбрано несколько аудиодорожек. Первый bounded General Video render допускает "
                    "не более одной явной master-аудиодорожки."
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
                code="general_video_render_runtime_unavailable",
                severity="warning" if render_configurable else "error",
                message=(
                    "Локальный General Video render требует настройки FFmpeg runtime."
                    if render_configurable
                    else f"Локальный General Video render недоступен: {render_reason}"
                ),
            )
        )

    workspace_ready = workspace is not None
    visuals_ready = bool(visual_bindings)
    audio_ready = len(audio_bindings) <= 1
    current_outcome = _current_outcome(project, workspace, source_media)

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="general.workspace",
            title="Задача и рабочее пространство",
            explanation=(
                "General Video использует сохранённый Stage 8 brief/script и точный порядок "
                "SHA-привязанных project-owned материалов."
            ),
            satisfied=workspace_ready,
            resolution=None if workspace_ready else "Сохраните задачу и выбранные материалы рабочего пространства.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="general.visuals",
            title="Визуальный ряд",
            explanation=(
                "Нужно хотя бы одно проверенное изображение или видео. Порядок выбранных материалов "
                "задаёт порядок первого deterministic master."
            ),
            satisfied=visuals_ready,
            resolution=None if visuals_ready else "Добавьте изображение или видео и сохраните workspace.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="general.audio",
            title="Master-аудио (необязательно)",
            explanation=(
                "Можно собрать ролик без аудио либо выбрать одну отдельную project-owned дорожку. "
                "Встроенный звук видео в этом bounded render не используется."
            ),
            satisfied=audio_ready,
            resolution=(
                None
                if audio_ready
                else "Оставьте выбранной не более одной аудиодорожки и снова сохраните workspace."
            ),
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.video.render_general",
            title="Локальный General Video render",
            explanation=(
                "Мастер собирается bounded local/free FFmpeg capability без клиентских путей, "
                "raw flags и параллельного timeline-store."
            ),
            satisfied=render_ready,
            resolution=None if render_ready else "Настройте локальные FFmpeg/FFprobe инструменты.",
        ),
    )

    revision_values = (workspace.revision_sha256,) if workspace is not None else ()
    action_enabled = workspace_ready and visuals_ready and audio_ready and render_ready
    render_action = WorkflowAction(
        action_id="render_general",
        title="Собрать обычный видеоролик",
        explanation=(
            "Нормализовать и последовательно собрать текущие SHA-привязанные изображения/видео; "
            "при наличии одной выбранной аудиодорожки добавить её в итоговый H.264/AAC master."
        ),
        enabled=action_enabled,
        blocked_by=tuple(
            item
            for item, ready in (
                ("general.workspace", workspace_ready),
                ("general.visuals", visuals_ready),
                ("general.audio", audio_ready),
                ("capability.video.render_general", render_ready),
            )
            if not ready
        ),
        prerequisite_ids=(
            "general.workspace",
            "general.visuals",
            "general.audio",
            "capability.video.render_general",
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["workspace_revision_sha256"],
            "properties": {
                "workspace_revision_sha256": _enum_property(
                    revision_values,
                    max_length=64,
                ),
            },
        },
        suggested_input=(
            {"workspace_revision_sha256": workspace.revision_sha256}
            if workspace is not None
            else {}
        ),
        execution_class="capability",
        authorization_class="none",
        capability_id=_RENDER_CAPABILITY_ID,
        expected_result="video",
    )

    if not render_ready and not render_configurable:
        readiness = WorkflowReadiness.UNAVAILABLE
        summary = "General Video нельзя завершить в текущем runtime: локальный финальный рендер недоступен."
    elif not workspace_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Сохраните задачу и материалы General Video workspace."
    elif not visuals_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Добавьте хотя бы одно изображение или видео для визуального ряда."
    elif not audio_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Оставьте не более одной выбранной master-аудиодорожки."
    elif current_outcome is not None:
        readiness = WorkflowReadiness.READY
        summary = "Текущий General Video мастер точно соответствует сохранённому workspace и его материалам."
    else:
        readiness = WorkflowReadiness.READY
        summary = "General Video готов к локальной deterministic сборке текущего мастера."

    recent_artifacts = tuple(
        _artifact(reference)
        for reference in project.artifacts
        if reference.kind == "video" and reference.metadata.get("lifecycle") == _RENDER_LIFECYCLE
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
                workspace_id=GENERAL_VIDEO_WORKSPACE_ID,
                title="Обычный видеоролик",
                description=(
                    "Задача → упорядоченные project-owned изображения/видео → необязательное "
                    "master-аудио → локальный мастер."
                ),
            ),
        ),
        next_actions=(render_action,),
        active_jobs=(),
        user_decisions=(),
        recent_artifacts=recent_artifacts,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "GENERAL_VIDEO_RECIPE_ID",
    "GENERAL_VIDEO_WORKSPACE_ID",
    "general_video_workflow_state",
]
