"""Semantic command/API boundary for optional Stage 6 sequence continuity."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.sequence_context import build_sequence_timeline_context
from uv_studio.projects.sequence_continuity import (
    SequenceContinuityError,
    SequenceContinuityRule,
    SequenceContinuityStore,
    SequenceNotFound,
    SequenceObservation,
    SequenceReviewNotFound,
    SequenceReviewResult,
    SequenceReviewTarget,
    SequenceShotNotFound,
    SequenceTakeNotFound,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Sequence Continuity"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SequenceRulePayload(_StrictModel):
    rule_id: str = Field(min_length=1, max_length=128)
    category: Literal["visual", "motion", "audio", "timing", "content", "technical", "style"]
    requirement: str = Field(min_length=1, max_length=4000)


class SequenceReviewTargetPayload(_StrictModel):
    target_id: str = Field(min_length=1, max_length=128)
    criterion: str = Field(min_length=1, max_length=4000)
    required: bool = True


class SequenceReviewResultPayload(_StrictModel):
    target_id: str = Field(min_length=1, max_length=128)
    outcome: Literal["pass", "fail", "uncertain"]
    note: str | None = Field(default=None, max_length=4000)


class SequenceObservationPayload(_StrictModel):
    observation_id: str = Field(min_length=1, max_length=128)
    kind: Literal["observation", "inference"]
    category: Literal["visual", "motion", "audio", "timing", "content", "technical", "style"]
    statement: str = Field(min_length=1, max_length=4000)
    confidence: Literal["low", "medium", "high"]


class CreateSequencePayload(_StrictModel):
    command: Literal["create_sequence"]
    title: str = Field(min_length=1, max_length=512)
    sequence_id: str | None = Field(default=None, min_length=1, max_length=128)


class UpsertSequenceShotPayload(_StrictModel):
    command: Literal["upsert_sequence_shot"]
    sequence_id: str = Field(min_length=1, max_length=128)
    shot_id: str = Field(min_length=1, max_length=128)
    order: int = Field(ge=0, le=100_000)
    intent: str = Field(min_length=1, max_length=4000)
    anchor_take_id: str | None = Field(default=None, min_length=1, max_length=128)
    locks: list[SequenceRulePayload] = Field(default_factory=list, max_length=64)
    allowed_changes: list[SequenceRulePayload] = Field(default_factory=list, max_length=64)
    review_targets: list[SequenceReviewTargetPayload] = Field(default_factory=list, max_length=64)


class RegisterSequenceTakePayload(_StrictModel):
    command: Literal["register_sequence_take"]
    sequence_id: str = Field(min_length=1, max_length=128)
    shot_id: str = Field(min_length=1, max_length=128)
    reference_id: str = Field(min_length=1, max_length=128)
    take_id: str | None = Field(default=None, min_length=1, max_length=128)


class ReviewSequenceTakePayload(_StrictModel):
    command: Literal["review_sequence_take"]
    sequence_id: str = Field(min_length=1, max_length=128)
    take_id: str = Field(min_length=1, max_length=128)
    verdict: Literal["approved", "needs_revision", "rejected"]
    results: list[SequenceReviewResultPayload] = Field(default_factory=list, max_length=64)
    observations: list[SequenceObservationPayload] = Field(default_factory=list, max_length=128)
    note: str | None = Field(default=None, max_length=4000)


class AcceptSequenceTakePayload(_StrictModel):
    command: Literal["accept_sequence_take"]
    sequence_id: str = Field(min_length=1, max_length=128)
    review_id: str = Field(min_length=1, max_length=128)


class ReanchorSequencePayload(_StrictModel):
    command: Literal["reanchor_sequence"]
    sequence_id: str = Field(min_length=1, max_length=128)
    take_id: str = Field(min_length=1, max_length=128)


SequenceCommandPayload = Annotated[
    Union[
        CreateSequencePayload,
        UpsertSequenceShotPayload,
        RegisterSequenceTakePayload,
        ReviewSequenceTakePayload,
        AcceptSequenceTakePayload,
        ReanchorSequencePayload,
    ],
    Field(discriminator="command"),
]


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
    if isinstance(exc, (SequenceContinuityError, ProjectValidationError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Sequence continuity command failed",
    )


def _rules(values: list[SequenceRulePayload]) -> tuple[SequenceContinuityRule, ...]:
    return tuple(
        SequenceContinuityRule(
            rule_id=item.rule_id,
            category=item.category,
            requirement=item.requirement,
        )
        for item in values
    )


@router.get("/{project_id}/sequence/state")
def get_sequence_state(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return SequenceContinuityStore(store).load(project_id).to_dict()
    except (
        ProjectNotFound,
        SequenceContinuityError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.post(
    "/{project_id}/sequence/commands",
    status_code=status.HTTP_201_CREATED,
)
def execute_sequence_command(
    project_id: str,
    payload: SequenceCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    service = SequenceContinuityStore(store)
    try:
        if isinstance(payload, CreateSequencePayload):
            value = service.create_sequence(
                project_id,
                title=payload.title,
                sequence_id=payload.sequence_id,
            )
            return {"command": payload.command, "payload": value.to_dict()}
        if isinstance(payload, UpsertSequenceShotPayload):
            value = service.upsert_plan(
                project_id,
                sequence_id=payload.sequence_id,
                shot_id=payload.shot_id,
                order=payload.order,
                intent=payload.intent,
                anchor_take_id=payload.anchor_take_id,
                locks=_rules(payload.locks),
                allowed_changes=_rules(payload.allowed_changes),
                review_targets=tuple(
                    SequenceReviewTarget(
                        target_id=item.target_id,
                        criterion=item.criterion,
                        required=item.required,
                    )
                    for item in payload.review_targets
                ),
            )
            return {"command": payload.command, "payload": value.to_dict()}
        if isinstance(payload, RegisterSequenceTakePayload):
            value = service.register_take(
                project_id,
                sequence_id=payload.sequence_id,
                shot_id=payload.shot_id,
                reference_id=payload.reference_id,
                take_id=payload.take_id,
            )
            return {"command": payload.command, "payload": value.to_dict()}
        if isinstance(payload, ReviewSequenceTakePayload):
            value = service.review_take(
                project_id,
                sequence_id=payload.sequence_id,
                take_id=payload.take_id,
                verdict=payload.verdict,
                results=tuple(
                    SequenceReviewResult(
                        target_id=item.target_id,
                        outcome=item.outcome,
                        note=item.note,
                    )
                    for item in payload.results
                ),
                observations=tuple(
                    SequenceObservation(
                        observation_id=item.observation_id,
                        kind=item.kind,
                        category=item.category,
                        statement=item.statement,
                        confidence=item.confidence,
                    )
                    for item in payload.observations
                ),
                note=payload.note,
            )
            return {"command": payload.command, "payload": value.to_dict()}
        if isinstance(payload, AcceptSequenceTakePayload):
            value = service.accept_take(
                project_id,
                sequence_id=payload.sequence_id,
                review_id=payload.review_id,
            )
            return {"command": payload.command, "payload": value.to_dict()}
        if isinstance(payload, ReanchorSequencePayload):
            value = service.reanchor(
                project_id,
                sequence_id=payload.sequence_id,
                take_id=payload.take_id,
            )
            return {"command": payload.command, "payload": value.to_dict()}
        raise SequenceContinuityError("unsupported sequence command")
    except (
        ProjectNotFound,
        SequenceNotFound,
        SequenceShotNotFound,
        SequenceTakeNotFound,
        SequenceReviewNotFound,
        SequenceContinuityError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/sequence/{sequence_id}/takes/{take_id}/context")
def get_sequence_timeline_context(
    project_id: str,
    sequence_id: str,
    take_id: str,
    window_us: int = Query(default=1_500_000, ge=1, le=10_000_000),
    samples: int = Query(default=3, ge=1, le=8),
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        return build_sequence_timeline_context(
            SequenceContinuityStore(store),
            project_id,
            sequence_id=sequence_id,
            take_id=take_id,
            window_us=window_us,
            samples=samples,
        )
    except (
        ProjectNotFound,
        SequenceNotFound,
        SequenceShotNotFound,
        SequenceTakeNotFound,
        SequenceContinuityError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
