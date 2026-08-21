"""Product-level workflow projections over canonical UV Studio state."""

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


def project_workflow_state(project, recipe, registry, source_media) -> ProjectWorkflowState:
    """Dispatch supported Product Orchestrator projections without duplicating canonical state."""

    if recipe is not None and project.recipe_id == TARGETED_EDIT_RECIPE_ID:
        return targeted_edit_workflow_state(project, recipe, registry, source_media)
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
