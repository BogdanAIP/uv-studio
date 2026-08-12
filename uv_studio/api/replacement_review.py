"""UV-owned HTTP API for evidence-based replacement review and acceptance."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr

from uv_studio.api.edit_state import RangeEditStatePayload
from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ProjectStore,
    ReplacementReview,
    ReplacementReviewAssessment,
    ReplacementReviewError,
    ReplacementReviewNotFound,
    ReplacementReviewObservation,
    ReplacementReviewState,
    ReplacementReviewStore,
    ReviewEvidenceReference,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Replacement Review"])


class ReviewEvidenceReferencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: StrictStr
    ref_id: StrictStr


class ReplacementReviewObservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: StrictStr
    kind: StrictStr
    statement: StrictStr
    confidence: StrictStr
    evidence: list[ReviewEvidenceReferencePayload]


class ReplacementReviewAssessmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: StrictStr
    outcome: StrictStr
    observation_ids: list[StrictStr]


class ReplacementReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    review_id: str
    candidate_id: str
    edit_id: str
    source_path: str
    start_us: int
    end_us: int
    plan_sha256: str
    candidate_sha256: str
    verdict: str
    observations: list[ReplacementReviewObservationPayload]
    assessments: list[ReplacementReviewAssessmentPayload]


class ReplacementReviewStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    reviews: list[ReplacementReviewPayload]


class CreateReplacementReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: StrictStr
    verdict: StrictStr
    observations: list[ReplacementReviewObservationPayload]
    assessments: list[ReplacementReviewAssessmentPayload]


class ReplacementReviewValidationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: StrictBool
    review: ReplacementReviewPayload


def _store(project_store: ProjectStore) -> ReplacementReviewStore:
    return ReplacementReviewStore(project_store)


def _review_payload(review: ReplacementReview) -> ReplacementReviewPayload:
    return ReplacementReviewPayload.model_validate(review.to_dict())


def _state_payload(state: ReplacementReviewState) -> ReplacementReviewStatePayload:
    return ReplacementReviewStatePayload.model_validate(state.to_dict())


def _not_found_or_server(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=404, detail="Project not found")
    if isinstance(exc, ReplacementReviewNotFound):
        return HTTPException(status_code=404, detail="Replacement review not found")
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="Replacement review operation failed")


def _domain_observations(
    values: list[ReplacementReviewObservationPayload],
) -> tuple[ReplacementReviewObservation, ...]:
    return tuple(
        ReplacementReviewObservation(
            observation_id=item.observation_id,
            kind=item.kind,
            statement=item.statement,
            confidence=item.confidence,
            evidence=tuple(
                ReviewEvidenceReference(kind=ref.kind, ref_id=ref.ref_id)
                for ref in item.evidence
            ),
        )
        for item in values
    )


def _domain_assessments(
    values: list[ReplacementReviewAssessmentPayload],
) -> tuple[ReplacementReviewAssessment, ...]:
    return tuple(
        ReplacementReviewAssessment(
            target_id=item.target_id,
            outcome=item.outcome,
            observation_ids=tuple(item.observation_ids),
        )
        for item in values
    )


@router.get("/{project_id}/replacement-reviews", response_model=ReplacementReviewStatePayload)
def list_replacement_reviews(
    project_id: str,
    project_store: ProjectStore = Depends(get_project_store),
) -> ReplacementReviewStatePayload:
    try:
        project_store.load_project(project_id)
        return _state_payload(_store(project_store).load(project_id))
    except (ProjectNotFound, ReplacementReviewError, ProjectStoreError) as exc:
        if isinstance(exc, ReplacementReviewError):
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise _not_found_or_server(exc) from exc


@router.get(
    "/{project_id}/replacement-reviews/{review_id}",
    response_model=ReplacementReviewPayload,
)
def get_replacement_review(
    project_id: str,
    review_id: str,
    project_store: ProjectStore = Depends(get_project_store),
) -> ReplacementReviewPayload:
    try:
        project_store.load_project(project_id)
        return _review_payload(_store(project_store).load(project_id).get(review_id))
    except (ProjectNotFound, ReplacementReviewNotFound, ReplacementReviewError, ProjectStoreError) as exc:
        if isinstance(exc, ReplacementReviewError) and not isinstance(exc, ReplacementReviewNotFound):
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise _not_found_or_server(exc) from exc


@router.get(
    "/{project_id}/replacement-reviews/{review_id}/validation",
    response_model=ReplacementReviewValidationPayload,
)
def validate_replacement_review(
    project_id: str,
    review_id: str,
    project_store: ProjectStore = Depends(get_project_store),
) -> ReplacementReviewValidationPayload:
    try:
        project_store.load_project(project_id)
        review = _store(project_store).validate_review(project_id, review_id)
        return ReplacementReviewValidationPayload(current=True, review=_review_payload(review))
    except (ProjectNotFound, ReplacementReviewNotFound, ProjectStoreError) as exc:
        raise _not_found_or_server(exc) from exc
    except ReplacementReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "replacement_review_stale", "message": str(exc)},
        ) from exc


@router.post(
    "/{project_id}/replacement-reviews",
    response_model=ReplacementReviewPayload,
    status_code=status.HTTP_201_CREATED,
)
def create_replacement_review(
    project_id: str,
    request: CreateReplacementReviewRequest,
    project_store: ProjectStore = Depends(get_project_store),
) -> ReplacementReviewPayload:
    review_id = f"review_{uuid.uuid4().hex}"
    try:
        project_store.load_project(project_id)
        state = _store(project_store).create_review(
            project_id,
            review_id=review_id,
            candidate_id=request.candidate_id,
            verdict=request.verdict,
            observations=_domain_observations(request.observations),
            assessments=_domain_assessments(request.assessments),
        )
        return _review_payload(state.get(review_id))
    except (ProjectNotFound, ProjectStoreError) as exc:
        raise _not_found_or_server(exc) from exc
    except ReplacementReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{project_id}/replacement-reviews/{review_id}/accept",
    response_model=RangeEditStatePayload,
    status_code=status.HTTP_201_CREATED,
)
def accept_replacement_review(
    project_id: str,
    review_id: str,
    project_store: ProjectStore = Depends(get_project_store),
) -> RangeEditStatePayload:
    try:
        project_store.load_project(project_id)
        state = _store(project_store).accept_review(project_id, review_id)
        return RangeEditStatePayload.model_validate(state.to_dict())
    except (ProjectNotFound, ReplacementReviewNotFound, ProjectStoreError) as exc:
        raise _not_found_or_server(exc) from exc
    except ReplacementReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "replacement_review_not_acceptable", "message": str(exc)},
        ) from exc
