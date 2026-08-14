"""Ephemeral API boundary for optional Stage 6 VLM review assistance."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.sequence_continuity import (
    SequenceContinuityError,
    SequenceNotFound,
    SequenceReviewNotFound,
    SequenceShotNotFound,
    SequenceTakeNotFound,
    SequenceContinuityStore,
)
from uv_studio.projects.sequence_review_assist import (
    SequenceReviewAssistError,
    build_sequence_review_assist,
    normalize_sequence_review_suggestion,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Sequence Review Assist"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SequenceReviewAssistBindingPayload(_StrictModel):
    sequence_id: str = Field(min_length=1, max_length=128)
    shot_id: str = Field(min_length=1, max_length=128)
    take_id: str = Field(min_length=1, max_length=128)
    plan_revision_sha256: str = Field(min_length=64, max_length=64)
    take_sha256: str = Field(min_length=64, max_length=64)
    anchor_take_id: str | None = Field(default=None, min_length=1, max_length=128)
    anchor_take_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class SequenceReviewAssistResultPayload(_StrictModel):
    target_id: str = Field(min_length=1, max_length=128)
    outcome: Literal["pass", "fail", "uncertain"]
    note: str | None = Field(default=None, max_length=4000)


class SequenceReviewAssistObservationPayload(_StrictModel):
    observation_id: str = Field(min_length=1, max_length=128)
    kind: Literal["observation", "inference"]
    category: Literal["visual", "motion", "audio", "timing", "content", "technical", "style"]
    statement: str = Field(min_length=1, max_length=4000)
    confidence: Literal["low", "medium", "high"]


class SequenceReviewAssistSuggestionPayload(_StrictModel):
    binding: SequenceReviewAssistBindingPayload
    verdict: Literal["approved", "needs_revision", "rejected"]
    results: list[SequenceReviewAssistResultPayload] = Field(default_factory=list, max_length=64)
    observations: list[SequenceReviewAssistObservationPayload] = Field(
        default_factory=list, max_length=128
    )
    note: str | None = Field(default=None, max_length=4000)


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, SequenceNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    if isinstance(exc, SequenceShotNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence shot not found")
    if isinstance(exc, SequenceTakeNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence take not found")
    if isinstance(exc, SequenceReviewNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence review not found")
    if isinstance(exc, (SequenceReviewAssistError, SequenceContinuityError, ProjectValidationError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Sequence review assist failed",
    )


@router.get("/{project_id}/sequence/{sequence_id}/takes/{take_id}/review-assist")
def get_sequence_review_assist(
    project_id: str,
    sequence_id: str,
    take_id: str,
    window_us: int = Query(default=1_500_000, ge=1, le=10_000_000),
    samples: int = Query(default=3, ge=1, le=8),
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return build_sequence_review_assist(
            SequenceContinuityStore(store),
            project_id,
            sequence_id=sequence_id,
            take_id=take_id,
            window_us=window_us,
            samples=samples,
        ).to_dict()
    except (
        ProjectNotFound,
        SequenceNotFound,
        SequenceShotNotFound,
        SequenceTakeNotFound,
        SequenceReviewNotFound,
        SequenceReviewAssistError,
        SequenceContinuityError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/sequence/{sequence_id}/takes/{take_id}/review-assist/normalize")
def normalize_sequence_review_assist(
    project_id: str,
    sequence_id: str,
    take_id: str,
    payload: SequenceReviewAssistSuggestionPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return normalize_sequence_review_suggestion(
            SequenceContinuityStore(store),
            project_id,
            sequence_id=sequence_id,
            take_id=take_id,
            payload=payload.model_dump(),
        ).to_dict()
    except (
        ProjectNotFound,
        SequenceNotFound,
        SequenceShotNotFound,
        SequenceTakeNotFound,
        SequenceReviewNotFound,
        SequenceReviewAssistError,
        SequenceContinuityError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
