"""Stable product-orchestration response contracts.

These values are read projections. They deliberately contain no mutable
workflow authority; Project Store and the coherent domain stores remain
canonical.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

WORKFLOW_SCHEMA_VERSION = 1


class WorkflowReadiness(str, Enum):
    READY = "ready"
    SETUP_REQUIRED = "setup_required"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class WorkflowPrerequisite:
    prerequisite_id: str
    title: str
    explanation: str
    satisfied: bool
    resolution: str | None = None


@dataclass(frozen=True)
class WorkflowWorkspace:
    workspace_id: str
    title: str
    description: str


@dataclass(frozen=True)
class WorkflowAction:
    action_id: str
    title: str
    explanation: str
    enabled: bool
    blocked_by: tuple[str, ...]
    prerequisite_ids: tuple[str, ...]
    input_schema: dict[str, Any]
    suggested_input: dict[str, Any]
    execution_class: str
    authorization_class: str
    capability_id: str
    expected_result: str


@dataclass(frozen=True)
class WorkflowArtifact:
    artifact_id: str
    kind: str
    path: str
    lifecycle: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class WorkflowDiagnostic:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class ProjectWorkflowState:
    project_id: str
    recipe_id: str
    recipe_title: str
    readiness: WorkflowReadiness
    summary: str
    current_outcome: WorkflowArtifact | None
    prerequisites: tuple[WorkflowPrerequisite, ...]
    relevant_workspaces: tuple[WorkflowWorkspace, ...]
    next_actions: tuple[WorkflowAction, ...]
    active_jobs: tuple[dict[str, Any], ...]
    user_decisions: tuple[dict[str, Any], ...]
    recent_artifacts: tuple[WorkflowArtifact, ...]
    diagnostics: tuple[WorkflowDiagnostic, ...]
    schema_version: int = WORKFLOW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["readiness"] = self.readiness.value
        return payload
