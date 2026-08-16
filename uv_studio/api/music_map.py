"""Semantic API boundary for optional Stage 7 Music Map state."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.music_map import (
    MAX_LYRIC_PHRASES,
    MAX_MUSIC_MARKERS,
    MAX_MUSIC_SECTIONS,
    MusicExcerpt,
    MusicLyricPhrase,
    MusicMapError,
    MusicMapStore,
    MusicSection,
    MusicTimingMarker,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Music Map"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MusicExcerptPayload(_StrictModel):
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)


class MusicSectionPayload(_StrictModel):
    section_id: str = Field(min_length=1, max_length=128)
    kind: Literal[
        "intro", "verse", "pre_chorus", "chorus", "bridge", "drop",
        "breakdown", "outro", "instrumental", "other",
    ]
    label: str = Field(min_length=1, max_length=512)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)


class MusicTimingMarkerPayload(_StrictModel):
    marker_id: str = Field(min_length=1, max_length=128)
    kind: Literal["beat", "downbeat", "accent", "climax", "phrase_boundary", "cut_point"]
    time_us: int = Field(ge=0)


class MusicLyricPhrasePayload(_StrictModel):
    phrase_id: str = Field(min_length=1, max_length=128)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=4000)


class SetMusicMapPayload(_StrictModel):
    command: Literal["set_music_map"]
    song_reference_id: str = Field(min_length=1, max_length=128)
    excerpt: MusicExcerptPayload
    sections: list[MusicSectionPayload] = Field(default_factory=list, max_length=MAX_MUSIC_SECTIONS)
    markers: list[MusicTimingMarkerPayload] = Field(default_factory=list, max_length=MAX_MUSIC_MARKERS)
    lyric_phrases: list[MusicLyricPhrasePayload] = Field(
        default_factory=list, max_length=MAX_LYRIC_PHRASES
    )


class ClearMusicMapPayload(_StrictModel):
    command: Literal["clear_music_map"]


MusicMapCommandPayload = Annotated[
    Union[SetMusicMapPayload, ClearMusicMapPayload],
    Field(discriminator="command"),
]


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, (MusicMapError, ProjectValidationError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=500, detail="Music Map command failed")


@router.get("/{project_id}/music-map")
def get_music_map(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        state = MusicMapStore(store).load(project_id, validate_current=True)
        return {"music_map": None if state is None else state.to_dict()}
    except (ProjectNotFound, MusicMapError, ProjectValidationError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/music-map/commands", status_code=status.HTTP_201_CREATED)
def execute_music_map_command(
    project_id: str,
    payload: MusicMapCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    service = MusicMapStore(store)
    try:
        store.load_project(project_id)
        if isinstance(payload, SetMusicMapPayload):
            state = service.set_map(
                project_id,
                song_reference_id=payload.song_reference_id,
                excerpt=MusicExcerpt(
                    start_us=payload.excerpt.start_us,
                    end_us=payload.excerpt.end_us,
                ),
                sections=tuple(
                    MusicSection(
                        section_id=item.section_id,
                        kind=item.kind,
                        label=item.label,
                        start_us=item.start_us,
                        end_us=item.end_us,
                    )
                    for item in payload.sections
                ),
                markers=tuple(
                    MusicTimingMarker(marker_id=item.marker_id, kind=item.kind, time_us=item.time_us)
                    for item in payload.markers
                ),
                lyric_phrases=tuple(
                    MusicLyricPhrase(
                        phrase_id=item.phrase_id,
                        start_us=item.start_us,
                        end_us=item.end_us,
                        text=item.text,
                    )
                    for item in payload.lyric_phrases
                ),
            )
            return {"command": payload.command, "payload": state.to_dict()}
        if isinstance(payload, ClearMusicMapPayload):
            service.clear(project_id)
            return {"command": payload.command, "payload": None}
        raise MusicMapError("unsupported Music Map command")
    except (ProjectNotFound, MusicMapError, ProjectValidationError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
