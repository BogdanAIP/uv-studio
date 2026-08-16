"""Ephemeral provider-neutral Music Analysis Assist API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from uv_studio.api.projects import get_project_store
from uv_studio.projects.music_analysis_assist import (
    MusicAnalysisAssistError,
    build_music_analysis_assist,
    normalize_music_analysis_suggestion,
)
from uv_studio.projects.music_map import MusicMapError
from uv_studio.projects.source_media import SourceMediaError, SourceMediaNotFound
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Music Analysis Assist"])


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, (ProjectNotFound, SourceMediaNotFound)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (MusicAnalysisAssistError, MusicMapError, SourceMediaError)):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="Music Analysis Assist failed")


@router.get("/{project_id}/music-analysis-assist")
def get_music_analysis_assist(
    project_id: str,
    song_reference_id: str = Query(min_length=1, max_length=128),
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        return build_music_analysis_assist(
            store, project_id, song_reference_id=song_reference_id
        ).to_dict()
    except (ProjectNotFound, SourceMediaNotFound, MusicAnalysisAssistError, MusicMapError, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/music-analysis-assist/normalize")
def normalize_music_analysis(
    project_id: str,
    song_reference_id: str = Query(min_length=1, max_length=128),
    payload: dict[str, Any] = Body(...),
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        return normalize_music_analysis_suggestion(
            store,
            project_id,
            song_reference_id=song_reference_id,
            payload=payload,
        )
    except (ProjectNotFound, SourceMediaNotFound, MusicAnalysisAssistError, MusicMapError, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
