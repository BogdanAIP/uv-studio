"""Evidence-bound final Music Video review API."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.music_assembly import MusicAssemblyError
from uv_studio.projects.music_direction import MusicDirectionError
from uv_studio.projects.music_map import MusicMapError
from uv_studio.projects.music_video_review import MusicVideoReviewError, MusicVideoReviewStore
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Music Video Review"])


class MusicVideoReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_id: str = Field(min_length=1, max_length=128)
    verdict: Literal["approved", "needs_revision", "rejected"]
    transition_outcome: Literal["pass", "fail", "uncertain"]
    note: str | None = Field(default=None, max_length=4000)


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=404, detail="Project not found")
    if isinstance(exc, (MusicVideoReviewError, MusicAssemblyError, MusicDirectionError, MusicMapError)):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="Music Video review failed")


@router.get("/{project_id}/music-video-review")
def get_music_video_review(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        review = MusicVideoReviewStore(store).load(project_id, validate_current=True)
        return {"music_video_review": None if review is None else review.to_dict()}
    except (ProjectNotFound, MusicVideoReviewError, MusicAssemblyError, MusicDirectionError, MusicMapError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/music-video-review", status_code=status.HTTP_201_CREATED)
def review_music_video(
    project_id: str,
    payload: MusicVideoReviewPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        review = MusicVideoReviewStore(store).review(
            project_id,
            artifact_id=payload.artifact_id,
            verdict=payload.verdict,
            transition_outcome=payload.transition_outcome,
            note=payload.note,
        )
        return {"music_video_review": review.to_dict()}
    except (ProjectNotFound, MusicVideoReviewError, MusicAssemblyError, MusicDirectionError, MusicMapError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
