"""Read-only Product Orchestrator projection for the preparation-only Story journey."""

from __future__ import annotations

from typing import Any

from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.projects.models import ProjectDocument
from uv_studio.projects.sequence_continuity import SequenceContinuityError, SequenceContinuityStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import Stage8WorkspaceError, get_stage8_workspace
from uv_studio.projects.store import ProjectStoreError
from uv_studio.recipes.models import RecipeDefinition

from .models import (
    ProjectWorkflowState,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
    WorkflowWorkspace,
)

STORY_RECIPE_ID = "story_video"
STORY_WORKSPACE_ID = "story_video"


def _grounded_metadata(project: ProjectDocument) -> dict[str, Any] | None:
    value = project.settings.get("grounded_metadata")
    return dict(value) if isinstance(value, dict) and value else None


def story_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project current Story preparation without inventing final render semantics."""

    del registry  # Story recovery is preparation-only and executes no capability.
    diagnostics: list[WorkflowDiagnostic] = []
    store = source_media.project_store

    try:
        workspace = get_stage8_workspace(store, project.project_id)
    except (Stage8WorkspaceError, ProjectStoreError) as exc:
        workspace = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="story_workspace_invalid",
                severity="error",
                message=(
                    "Story workspace не прошёл проверку текущих project-owned bytes: "
                    f"{exc}"
                ),
            )
        )

    grounded = _grounded_metadata(project)
    visual_count = (
        sum(1 for item in workspace.sources if item.kind in {"image", "video"})
        if workspace is not None
        else 0
    )

    try:
        continuity = SequenceContinuityStore(store).load(
            project.project_id,
            validate_current=True,
        )
        sequences = continuity.sequences
    except (SequenceContinuityError, ProjectStoreError) as exc:
        sequences = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="story_continuity_invalid",
                severity="warning",
                message=(
                    "Опциональное Sequence Continuity исключено из текущей Story-проекции, "
                    f"потому что его accepted state не прошёл проверку: {exc}"
                ),
            )
        )

    accepted_takes = tuple(
        take
        for sequence in sequences
        for take in sequence.takes
        if take.status == "accepted"
    )
    if sequences:
        diagnostics.append(
            WorkflowDiagnostic(
                code="story_continuity_available",
                severity="info",
                message=(
                    "Для Story доступно опциональное Sequence Continuity: "
                    f"последовательностей {len(sequences)}, принятых актуальных дублей {len(accepted_takes)}."
                ),
            )
        )
    if grounded is not None:
        diagnostics.append(
            WorkflowDiagnostic(
                code="story_grounded_metadata_available",
                severity="info",
                message=(
                    "Проект содержит grounded_metadata в канонических Project settings; "
                    "Product Orchestrator использует его только как существующую подготовительную привязку."
                ),
            )
        )

    diagnostics.append(
        WorkflowDiagnostic(
            code="story_final_render_not_authoritative",
            severity="info",
            message=(
                "Story Video восстановлен как подготовительный путь. В текущем продукте нет "
                "аудированного end-to-end Story render/export, поэтому Product Orchestrator "
                "не рекламирует render_story и не выдаёт подготовку за готовый фильм."
            ),
        )
    )

    workspace_ready = workspace is not None
    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="story.workspace",
            title="Story workspace",
            explanation=(
                "Нужен сохранённый Stage 8 brief с текущей SHA-привязкой выбранных "
                "project-owned материалов; script и материалы могут дополняться по мере подготовки."
            ),
            satisfied=workspace_ready,
            resolution=(
                None
                if workspace_ready
                else "Сохраните задачу Story и выбранные материалы в сюжетном рабочем пространстве."
            ),
        ),
    )

    if workspace_ready:
        readiness = WorkflowReadiness.READY
        summary = (
            "Story-подготовка сохранена и соответствует текущим project-owned входам. "
            "Это готовность подготовительного состояния, а не готовый финальный ролик."
        )
    else:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Сохраните Story brief и текущие материалы, чтобы зафиксировать подготовительное состояние."

    user_decisions = tuple(
        {
            "kind": "accepted_sequence_take",
            "sequence_id": sequence.sequence_id,
            "take_id": take.take_id,
            "shot_id": take.shot_id,
            "sha256": take.artifact_sha256,
        }
        for sequence in sequences
        for take in sequence.takes
        if take.status == "accepted"
    )

    workspace_description = (
        "Brief/script и точные project-owned Story materials"
        + (f" · визуальных привязок: {visual_count}" if workspace_ready else "")
        + (" · grounded metadata: есть" if grounded is not None else "")
        + (f" · continuity sequences: {len(sequences)}" if sequences else "")
        + ". Финальный Story render пока не является авторитетным продуктовым действием."
    )

    return ProjectWorkflowState(
        project_id=project.project_id,
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        readiness=readiness,
        summary=summary,
        current_outcome=None,
        prerequisites=prerequisites,
        relevant_workspaces=(
            WorkflowWorkspace(
                workspace_id=STORY_WORKSPACE_ID,
                title="Сюжетное рабочее пространство",
                description=workspace_description,
            ),
        ),
        next_actions=(),
        active_jobs=(),
        user_decisions=user_decisions,
        recent_artifacts=(),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "STORY_RECIPE_ID",
    "STORY_WORKSPACE_ID",
    "story_workflow_state",
]
