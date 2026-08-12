"""Product-owned semantic editor commands shared by GUI, scripts, AI and MCP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from uv_studio.projects.continuity_brief import (
    ContinuityConstraint,
    ContinuityEvidence,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReviewTarget,
)
from uv_studio.projects.media_ranges import MAX_CONTEXT_US, ProjectMediaRange, ResolvedProjectMediaRange
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.source_media import ProjectSourceMediaStore, SourceMediaError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

_MAX_CHANGE_REQUEST_LENGTH = 4000


class EditorCommandError(ProjectValidationError):
    """A semantic editor command is invalid for the canonical project state."""


def _change_request(value: Any) -> str:
    if not isinstance(value, str):
        raise EditorCommandError("change_request must be a string")
    normalized = value.strip()
    if not normalized:
        raise EditorCommandError("change_request must not be empty")
    if len(normalized) > _MAX_CHANGE_REQUEST_LENGTH:
        raise EditorCommandError(
            f"change_request must be <= {_MAX_CHANGE_REQUEST_LENGTH} characters"
        )
    return normalized


def _duration_from_source_metadata(metadata: dict[str, Any]) -> int:
    value = metadata.get("duration_us")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EditorCommandError(
            "registered source media is missing a valid positive duration_us"
        )
    return value


@dataclass(frozen=True)
class SelectRangeCommand:
    source_id: str
    start_us: int
    end_us: int
    change_request: str
    context_before_us: int = 5_000_000
    context_after_us: int = 5_000_000

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise EditorCommandError("source_id must be a non-empty string")
        object.__setattr__(self, "source_id", self.source_id.strip())
        object.__setattr__(self, "change_request", _change_request(self.change_request))
        for field_name in ("context_before_us", "context_after_us"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise EditorCommandError(f"{field_name} must be an integer microsecond value")
            if value < 0 or value > MAX_CONTEXT_US:
                raise EditorCommandError(
                    f"{field_name} must be between 0 and {MAX_CONTEXT_US}"
                )


@dataclass(frozen=True)
class SelectRangeResult:
    command: str
    source_id: str
    edit_id: str
    resolved_range: ResolvedProjectMediaRange
    brief: RangeContinuityBrief

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "source_id": self.source_id,
            "edit_id": self.edit_id,
            "resolved_range": self.resolved_range.to_dict(),
            "brief": self.brief.to_dict(),
        }


class EditorCommandService:
    """Single semantic mutation boundary for editor product callers."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.source_media = ProjectSourceMediaStore(project_store)
        self.briefs = RangeContinuityBriefStore(project_store)

    @staticmethod
    def _new_edit_id() -> str:
        return f"edit_{uuid.uuid4().hex}"

    def select_range(
        self,
        project_id: str,
        command: SelectRangeCommand,
    ) -> SelectRangeResult:
        if not isinstance(command, SelectRangeCommand):
            raise EditorCommandError("select_range requires SelectRangeCommand")
        try:
            source = self.source_media.get(project_id, command.source_id)
            source_duration_us = _duration_from_source_metadata(source.metadata)
            requested = ProjectMediaRange(
                source_path=source.path,
                start_us=command.start_us,
                end_us=command.end_us,
                context_before_us=command.context_before_us,
                context_after_us=command.context_after_us,
            )
            resolved = requested.resolve(source_duration_us)
        except (ProjectNotFound, SourceMediaError, ProjectStoreError, ProjectValidationError) as exc:
            if isinstance(exc, ProjectNotFound):
                raise
            raise EditorCommandError(str(exc)) from exc

        edit_id = self._new_edit_id()
        evidence: list[ContinuityEvidence] = [
            ContinuityEvidence(
                evidence_id="requested",
                role="requested",
                path=source.path,
                source_start_us=resolved.start_us,
                source_end_us=resolved.end_us,
            )
        ]
        context_evidence_ids: list[str] = []
        if resolved.context_start_us < resolved.start_us:
            evidence.append(
                ContinuityEvidence(
                    evidence_id="before",
                    role="before",
                    path=source.path,
                    source_start_us=resolved.context_start_us,
                    source_end_us=resolved.start_us,
                )
            )
            context_evidence_ids.append("before")
        if resolved.end_us < resolved.context_end_us:
            evidence.append(
                ContinuityEvidence(
                    evidence_id="after",
                    role="after",
                    path=source.path,
                    source_start_us=resolved.end_us,
                    source_end_us=resolved.context_end_us,
                )
            )
            context_evidence_ids.append("after")

        requested_evidence_ids = ("requested",)
        boundary_evidence_ids = tuple(context_evidence_ids) or requested_evidence_ids
        brief = RangeContinuityBrief(
            edit_id=edit_id,
            source_path=source.path,
            start_us=resolved.start_us,
            end_us=resolved.end_us,
            evidence=tuple(evidence),
            constraints=(
                ContinuityConstraint(
                    constraint_id="requested_change",
                    category="content",
                    requirement=command.change_request,
                    evidence_ids=requested_evidence_ids,
                ),
                ContinuityConstraint(
                    constraint_id="range_identity",
                    category="timing",
                    requirement=(
                        "Replacement must preserve the exact selected source interval and "
                        "must not alter media outside that interval."
                    ),
                    evidence_ids=requested_evidence_ids,
                ),
            ),
            review_targets=(
                ReviewTarget(
                    target_id="requested_change",
                    criterion=f"Replacement satisfies the requested change: {command.change_request}",
                    required=True,
                    evidence_ids=requested_evidence_ids,
                ),
                ReviewTarget(
                    target_id="boundary_continuity",
                    criterion=(
                        "Replacement joins the surrounding source context without an "
                        "unintended visual, motion, timing or audio discontinuity."
                    ),
                    required=True,
                    evidence_ids=boundary_evidence_ids,
                ),
            ),
        )
        try:
            self.briefs.upsert(project_id, brief)
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise EditorCommandError(str(exc)) from exc
        return SelectRangeResult(
            command="select_range",
            source_id=source.id,
            edit_id=edit_id,
            resolved_range=resolved,
            brief=brief,
        )
