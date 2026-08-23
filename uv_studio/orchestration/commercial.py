"""Read-only Product Orchestrator projection for Commercial Product preparation."""

from __future__ import annotations

from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.projects.models import ProjectDocument
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

COMMERCIAL_PRODUCT_RECIPE_ID = "commercial_product"
COMMERCIAL_PRODUCT_WORKSPACE_ID = "commercial_product"


def commercial_product_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project verified Commercial preparation without inventing approval or render state."""

    del registry  # This recovery is preparation-only and executes no capability.
    diagnostics: list[WorkflowDiagnostic] = []
    store = source_media.project_store

    try:
        workspace = get_stage8_workspace(store, project.project_id)
    except (Stage8WorkspaceError, ProjectStoreError) as exc:
        workspace = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="commercial_workspace_invalid",
                severity="error",
                message=(
                    "Commercial Product workspace не прошёл проверку текущих project-owned bytes: "
                    f"{exc}"
                ),
            )
        )

    product_visuals = tuple(
        item for item in workspace.sources if item.kind in {"image", "video"}
    ) if workspace is not None else ()
    audio_count = sum(1 for item in workspace.sources if item.kind == "audio") if workspace else 0

    diagnostics.append(
        WorkflowDiagnostic(
            code="commercial_required_gates_not_authoritative",
            severity="info",
            message=(
                "Рецепт Commercial Product требует source review, direction, sample-first, plan и final review. "
                "Отдельного канонического Commercial approval-state для этих gates пока нет, поэтому "
                "Product Orchestrator не помечает их как пройденные и не скрывает это за Stage 8 brief."
            ),
        )
    )
    diagnostics.append(
        WorkflowDiagnostic(
            code="commercial_final_render_not_authoritative",
            severity="info",
            message=(
                "Commercial Product восстановлен как подготовительный путь. `timeline.assemble` в recipe "
                "не является доказательством аудированного end-to-end рекламного render/export, поэтому "
                "render_commercial и provider-backed generation здесь не рекламируются."
            ),
        )
    )

    workspace_ready = workspace is not None
    product_reference_ready = bool(product_visuals)
    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="commercial.workspace",
            title="Product brief",
            explanation=(
                "Нужен сохранённый Stage 8 brief/script с точной SHA-привязкой выбранных "
                "project-owned материалов."
            ),
            satisfied=workspace_ready,
            resolution=(
                None
                if workspace_ready
                else "Сохраните рекламную задачу и выбранные материалы в продуктовом рабочем пространстве."
            ),
        ),
        WorkflowPrerequisite(
            prerequisite_id="commercial.product_reference",
            title="Проверяемый продуктовый референс",
            explanation=(
                "Для product preparation нужен хотя бы один текущий project-owned image/video, "
                "чтобы идентичность продукта не существовала только в тексте brief."
            ),
            satisfied=product_reference_ready,
            resolution=(
                None
                if product_reference_ready
                else "Добавьте и выберите хотя бы одно фото или видео продукта."
            ),
        ),
    )

    if workspace_ready and product_reference_ready:
        readiness = WorkflowReadiness.READY
        summary = (
            "Commercial Product preparation сохранена и привязана к текущим project-owned product media. "
            "Это готовность подготовительного состояния, а не доказательство пройденных production gates "
            "или готового рекламного ролика."
        )
    else:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = (
            "Сохраните product brief и хотя бы один проверяемый фото/видео референс продукта, "
            "чтобы зафиксировать подготовительное состояние."
        )

    workspace_description = (
        "Brief/script и точные project-owned product materials"
        + (f" · продуктовых image/video: {len(product_visuals)}" if workspace_ready else "")
        + (f" · audio: {audio_count}" if workspace_ready and audio_count else "")
        + ". Обязательные production approval gates и финальный render пока не являются "
        "авторитетными действиями этого пути."
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
                workspace_id=COMMERCIAL_PRODUCT_WORKSPACE_ID,
                title="Продуктовое рабочее пространство",
                description=workspace_description,
            ),
        ),
        next_actions=(),
        active_jobs=(),
        user_decisions=(),
        recent_artifacts=(),
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "COMMERCIAL_PRODUCT_RECIPE_ID",
    "COMMERCIAL_PRODUCT_WORKSPACE_ID",
    "commercial_product_workflow_state",
]
