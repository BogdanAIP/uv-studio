"""Product-level workflow projections over canonical UV Studio state."""

from dataclasses import replace

from uv_studio.projects.replacement_review import ReplacementReviewError, ReplacementReviewStore
from uv_studio.projects.store import ProjectStoreError

from .models import (
    WORKFLOW_SCHEMA_VERSION,
    ProjectWorkflowState,
    WorkflowAction,
    WorkflowArtifact,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
    WorkflowWorkspace,
)
from .project_workflow import project_workflow_state as _base_project_workflow_state
from .targeted_edit import TARGETED_EDIT_RECIPE_ID, targeted_edit_workflow_state


def _current_targeted_outcome(state: ProjectWorkflowState) -> WorkflowArtifact | None:
    accepted_by_source: dict[str, list[str]] = {}
    for decision in state.user_decisions:
        if decision.get("kind") != "accepted_range_edit":
            continue
        source_path = decision.get("source_path")
        edit_id = decision.get("edit_id")
        if isinstance(source_path, str) and isinstance(edit_id, str):
            accepted_by_source.setdefault(source_path, []).append(edit_id)

    for artifact in state.recent_artifacts:
        if artifact.lifecycle != "render":
            continue
        source_path = artifact.metadata.get("source_path")
        edit_ids = artifact.metadata.get("edit_ids")
        expected = accepted_by_source.get(source_path) if isinstance(source_path, str) else None
        if expected and isinstance(edit_ids, (list, tuple)) and list(edit_ids) == expected:
            return artifact
    return None


def _without_consumed_accept_actions(
    state: ProjectWorkflowState,
    source_media,
) -> tuple[WorkflowAction, ...]:
    accepted_ids = {
        decision.get("edit_id")
        for decision in state.user_decisions
        if decision.get("kind") == "accepted_range_edit" and isinstance(decision.get("edit_id"), str)
    }
    if not accepted_ids:
        return state.next_actions

    try:
        reviews = {
            review.review_id: review
            for review in ReplacementReviewStore(source_media.project_store).load(state.project_id).reviews
        }
    except (ReplacementReviewError, ProjectStoreError):
        reviews = {}

    normalized: list[WorkflowAction] = []
    for action in state.next_actions:
        if action.action_id != "accept_replacement":
            normalized.append(action)
            continue
        properties = action.input_schema.get("properties")
        review_schema = properties.get("review_id") if isinstance(properties, dict) else None
        allowed = review_schema.get("enum") if isinstance(review_schema, dict) else None
        allowed_ids = tuple(value for value in allowed or () if isinstance(value, str))
        pending_ids = tuple(
            review_id
            for review_id in allowed_ids
            if (review := reviews.get(review_id)) is not None and review.edit_id not in accepted_ids
        )
        if not pending_ids:
            continue

        next_schema = dict(action.input_schema)
        next_properties = dict(properties) if isinstance(properties, dict) else {}
        next_review_schema = dict(review_schema) if isinstance(review_schema, dict) else {"type": "string"}
        next_review_schema["enum"] = pending_ids
        next_properties["review_id"] = next_review_schema
        next_schema["properties"] = next_properties
        normalized.append(
            replace(
                action,
                input_schema=next_schema,
                suggested_input={"review_id": pending_ids[0]},
            )
        )
    return tuple(normalized)


def _targeted_readiness(
    state: ProjectWorkflowState,
    current_outcome: WorkflowArtifact | None,
) -> tuple[WorkflowReadiness, str]:
    prerequisites = {item.prerequisite_id: item for item in state.prerequisites}
    render = prerequisites.get("capability.video.render_edits")
    source = prerequisites.get("source.video")
    brief = prerequisites.get("edit.brief")
    replacement = prerequisites.get("source.replacement_video")
    accepted = prerequisites.get("edit.accepted")

    if render is not None and not render.satisfied:
        hard_failure = any(
            diagnostic.code in {
                "targeted_edit_render_capability_unknown",
                "targeted_edit_render_capability_unavailable",
            }
            and diagnostic.severity == "error"
            for diagnostic in state.diagnostics
        )
        if hard_failure:
            return (
                WorkflowReadiness.UNAVAILABLE,
                "Точечное редактирование нельзя завершить в текущем runtime: локальная финальная сборка недоступна.",
            )
        return (
            WorkflowReadiness.SETUP_REQUIRED,
            "Завершите настройку локальной финальной сборки перед работой с этим сценарием.",
        )

    if source is not None and not source.satisfied:
        return (
            WorkflowReadiness.SETUP_REQUIRED,
            "Импортируйте исходное видео, чтобы начать точечное редактирование.",
        )

    if (
        brief is not None
        and brief.satisfied
        and replacement is not None
        and not replacement.satisfied
    ):
        return (
            WorkflowReadiness.SETUP_REQUIRED,
            "Задача изменения сохранена. Импортируйте отдельный видеоклип для замены выбранного фрагмента.",
        )

    if accepted is not None and accepted.satisfied and current_outcome is not None:
        return (
            WorkflowReadiness.READY,
            "Текущий мастер точно соответствует принятому состоянию правок.",
        )

    return state.readiness, state.summary


def _normalize_targeted_projection(
    state: ProjectWorkflowState,
    source_media,
) -> ProjectWorkflowState:
    """Keep read-only product truth aligned with current accepted/rendered revisions."""

    current_outcome = _current_targeted_outcome(state)
    readiness, summary = _targeted_readiness(state, current_outcome)
    return replace(
        state,
        readiness=readiness,
        summary=summary,
        current_outcome=current_outcome,
        next_actions=_without_consumed_accept_actions(state, source_media),
    )


def project_workflow_state(project, recipe, registry, source_media) -> ProjectWorkflowState:
    """Dispatch supported Product Orchestrator projections without duplicating canonical state."""

    if recipe is not None and project.recipe_id == TARGETED_EDIT_RECIPE_ID:
        state = targeted_edit_workflow_state(project, recipe, registry, source_media)
        return _normalize_targeted_projection(state, source_media)
    return _base_project_workflow_state(project, recipe, registry, source_media)


__all__ = [
    "ProjectWorkflowState",
    "TARGETED_EDIT_RECIPE_ID",
    "WORKFLOW_SCHEMA_VERSION",
    "WorkflowAction",
    "WorkflowArtifact",
    "WorkflowDiagnostic",
    "WorkflowPrerequisite",
    "WorkflowReadiness",
    "WorkflowWorkspace",
    "project_workflow_state",
    "targeted_edit_workflow_state",
]
