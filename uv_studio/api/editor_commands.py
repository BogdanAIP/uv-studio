"""UV Studio-owned semantic editor command HTTP boundary."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.editor import MLTTimelineAdapter
from uv_studio.editor.commands import EditorCommandError, EditorCommandService, SelectRangeCommand
from uv_studio.editor.dubbing_commands import (
    AttachPreparedSpeechCommand,
    DubbingCommandError,
    DubbingCommandService,
    ImportDubbingTranscriptCommand,
    ImportTranscriptSegmentInput,
    TranslationSegmentInput,
    UpsertDubbingTranslationCommand,
)
from uv_studio.projects.continuity_brief import (
    ContinuityBriefError,
    RangeContinuityBriefStore,
)
from uv_studio.projects.dubbing import (
    DubbingError,
    DubbingStore,
    DubbingTranscriptNotFound,
    DubbingTranslationNotFound,
)
from uv_studio.projects.edit_state import EditStateError, RangeEditStateStore
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.prepared_audio import PreparedAudioError, PreparedAudioNotFound
from uv_studio.projects.prepared_speech import (
    PreparedSpeechError,
    PreparedSpeechStore,
    PreparedSpeechTakeNotFound,
)
from uv_studio.projects.replacement_candidate import ReplacementCandidateStore
from uv_studio.projects.replacement_plan import ReplacementPlanStore
from uv_studio.projects.replacement_review import ReplacementReviewStore
from uv_studio.projects.source_media import SourceMediaError, SourceMediaNotFound
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Editor"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SelectRangeCommandPayload(_StrictModel):
    command: Literal["select_range"]
    source_id: str = Field(min_length=1, max_length=128)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    change_request: str = Field(min_length=1, max_length=4000)
    context_before_us: int = Field(default=5_000_000, ge=0, le=30_000_000)
    context_after_us: int = Field(default=5_000_000, ge=0, le=30_000_000)


class TranscriptSegmentCommandPayload(_StrictModel):
    segment_id: str = Field(min_length=1, max_length=128)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=8000)
    speaker_label: str | None = Field(default=None, min_length=1, max_length=128)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ImportDubbingTranscriptCommandPayload(_StrictModel):
    command: Literal["import_dubbing_transcript"]
    source_id: str = Field(min_length=1, max_length=128)
    language: str = Field(min_length=2, max_length=64)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    segments: list[TranscriptSegmentCommandPayload] = Field(min_length=1, max_length=100_000)
    dubbing_id: str | None = Field(default=None, min_length=1, max_length=128)


class AcceptAsrTranscriptCommandPayload(_StrictModel):
    command: Literal["accept_asr_transcript"]
    source_id: str = Field(min_length=1, max_length=128)
    language: str = Field(min_length=2, max_length=64)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    segments: list[TranscriptSegmentCommandPayload] = Field(min_length=1, max_length=100_000)
    dubbing_id: str | None = Field(default=None, min_length=1, max_length=128)


class TranslationSegmentCommandPayload(_StrictModel):
    segment_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=8000)


class UpsertDubbingTranslationCommandPayload(_StrictModel):
    command: Literal["upsert_dubbing_translation"]
    dubbing_id: str = Field(min_length=1, max_length=128)
    target_language: str = Field(min_length=2, max_length=64)
    segments: list[TranslationSegmentCommandPayload] = Field(min_length=1, max_length=100_000)
    translation_id: str | None = Field(default=None, min_length=1, max_length=128)


class AttachPreparedSpeechCommandPayload(_StrictModel):
    command: Literal["attach_prepared_speech"]
    dubbing_id: str = Field(min_length=1, max_length=128)
    audio_id: str = Field(min_length=1, max_length=128)
    translation_id: str | None = Field(default=None, min_length=1, max_length=128)
    segment_id: str | None = Field(default=None, min_length=1, max_length=128)
    take_id: str | None = Field(default=None, min_length=1, max_length=128)


EditorCommandPayload = Annotated[
    Union[
        SelectRangeCommandPayload,
        ImportDubbingTranscriptCommandPayload,
        AcceptAsrTranscriptCommandPayload,
        UpsertDubbingTranslationCommandPayload,
        AttachPreparedSpeechCommandPayload,
    ],
    Field(discriminator="command"),
]


class SelectRangeCommandResultPayload(_StrictModel):
    command: Literal["select_range"]
    source_id: str
    edit_id: str
    resolved_range: dict
    brief: dict


class ImportDubbingTranscriptResultPayload(_StrictModel):
    command: Literal["import_dubbing_transcript"]
    dubbing_id: str
    payload: dict


class AcceptAsrTranscriptResultPayload(_StrictModel):
    command: Literal["accept_asr_transcript"]
    dubbing_id: str
    payload: dict


class UpsertDubbingTranslationResultPayload(_StrictModel):
    command: Literal["upsert_dubbing_translation"]
    dubbing_id: str
    payload: dict


class AttachPreparedSpeechResultPayload(_StrictModel):
    command: Literal["attach_prepared_speech"]
    dubbing_id: str
    payload: dict


EditorCommandResultPayload = Union[
    SelectRangeCommandResultPayload,
    ImportDubbingTranscriptResultPayload,
    AcceptAsrTranscriptResultPayload,
    UpsertDubbingTranslationResultPayload,
    AttachPreparedSpeechResultPayload,
]


class EditorStatePayload(_StrictModel):
    sources: list[ProjectReferencePayload]
    artifacts: list[ProjectReferencePayload]
    prepared_audio: list[ProjectReferencePayload]
    briefs: list[dict]
    replacement_plans: list[dict]
    replacement_candidates: list[dict]
    sample_approvals: list[dict]
    replacement_reviews: list[dict]
    accepted_edits: list[dict]
    dubbing: dict
    prepared_speech: dict
    engine: dict


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, SourceMediaNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source media not found")
    if isinstance(exc, PreparedAudioNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prepared audio not found")
    if isinstance(exc, DubbingTranscriptNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dubbing transcript not found")
    if isinstance(exc, DubbingTranslationNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dubbing translation not found")
    if isinstance(exc, PreparedSpeechTakeNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prepared speech take not found")
    if isinstance(
        exc,
        (
            EditorCommandError,
            DubbingCommandError,
            DubbingError,
            PreparedAudioError,
            PreparedSpeechError,
            SourceMediaError,
            ContinuityBriefError,
            EditStateError,
            ProjectValidationError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Editor command failed",
    )


def _transcript_command(
    payload: ImportDubbingTranscriptCommandPayload | AcceptAsrTranscriptCommandPayload,
) -> ImportDubbingTranscriptCommand:
    return ImportDubbingTranscriptCommand(
        source_id=payload.source_id,
        language=payload.language,
        start_us=payload.start_us,
        end_us=payload.end_us,
        dubbing_id=payload.dubbing_id,
        segments=tuple(
            ImportTranscriptSegmentInput(
                segment_id=item.segment_id,
                start_us=item.start_us,
                end_us=item.end_us,
                text=item.text,
                speaker_label=item.speaker_label,
                confidence=item.confidence,
            )
            for item in payload.segments
        ),
    )


@router.post(
    "/{project_id}/editor/commands",
    response_model=EditorCommandResultPayload,
    status_code=status.HTTP_201_CREATED,
)
def execute_editor_command(
    project_id: str,
    payload: EditorCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> EditorCommandResultPayload:
    """Execute one semantic editor mutation through the shared product boundary."""

    try:
        if isinstance(payload, SelectRangeCommandPayload):
            result = EditorCommandService(store).select_range(
                project_id,
                SelectRangeCommand(
                    source_id=payload.source_id,
                    start_us=payload.start_us,
                    end_us=payload.end_us,
                    change_request=payload.change_request,
                    context_before_us=payload.context_before_us,
                    context_after_us=payload.context_after_us,
                ),
            )
            return SelectRangeCommandResultPayload.model_validate(result.to_dict())
        if isinstance(payload, ImportDubbingTranscriptCommandPayload):
            result = DubbingCommandService(store).import_transcript(
                project_id,
                _transcript_command(payload),
            )
            return ImportDubbingTranscriptResultPayload.model_validate(result.to_dict())
        if isinstance(payload, AcceptAsrTranscriptCommandPayload):
            result = DubbingCommandService(store).accept_asr_transcript(
                project_id,
                _transcript_command(payload),
            )
            return AcceptAsrTranscriptResultPayload.model_validate(result.to_dict())
        if isinstance(payload, UpsertDubbingTranslationCommandPayload):
            result = DubbingCommandService(store).upsert_translation(
                project_id,
                UpsertDubbingTranslationCommand(
                    dubbing_id=payload.dubbing_id,
                    target_language=payload.target_language,
                    translation_id=payload.translation_id,
                    segments=tuple(
                        TranslationSegmentInput(segment_id=item.segment_id, text=item.text)
                        for item in payload.segments
                    ),
                ),
            )
            return UpsertDubbingTranslationResultPayload.model_validate(result.to_dict())
        if isinstance(payload, AttachPreparedSpeechCommandPayload):
            result = DubbingCommandService(store).attach_prepared_speech(
                project_id,
                AttachPreparedSpeechCommand(
                    dubbing_id=payload.dubbing_id,
                    audio_id=payload.audio_id,
                    translation_id=payload.translation_id,
                    segment_id=payload.segment_id,
                    take_id=payload.take_id,
                ),
            )
            return AttachPreparedSpeechResultPayload.model_validate(result.to_dict())
        raise EditorCommandError("unsupported editor command")
    except (
        ProjectNotFound,
        SourceMediaNotFound,
        PreparedAudioNotFound,
        DubbingTranscriptNotFound,
        DubbingTranslationNotFound,
        PreparedSpeechTakeNotFound,
        EditorCommandError,
        DubbingCommandError,
        DubbingError,
        PreparedAudioError,
        PreparedSpeechError,
        SourceMediaError,
        ContinuityBriefError,
        EditStateError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/editor/state", response_model=EditorStatePayload)
def get_editor_state(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> EditorStatePayload:
    """Return canonical state plus a bounded MLT-derived projection summary.

    Raw MLT XML and resolved host paths never leave the adapter. Mutations still
    go through their original Command/Plan/Candidate/Review/Accept boundaries so
    the engine cannot become a second canonical project model.
    """

    try:
        project = store.load_project(project_id)
        briefs = RangeContinuityBriefStore(store).load(project_id)
        plans = ReplacementPlanStore(store).load(project_id)
        candidates = ReplacementCandidateStore(store).load(project_id)
        reviews = ReplacementReviewStore(store).load(project_id)
        accepted = RangeEditStateStore(store).load(project_id)
        dubbing = DubbingStore(store).load(project_id, validate_current=True)
        prepared_speech = PreparedSpeechStore(store).load(project_id, validate_current=True)
        engine = MLTTimelineAdapter(store).project_summary(project_id)
        return EditorStatePayload(
            sources=[
                ProjectReferencePayload.model_validate(reference.to_dict())
                for reference in project.sources
                if reference.kind == "video"
            ],
            artifacts=[
                ProjectReferencePayload.model_validate(reference.to_dict())
                for reference in project.artifacts
                if reference.kind == "video"
            ],
            prepared_audio=[
                ProjectReferencePayload.model_validate(reference.to_dict())
                for reference in project.artifacts
                if reference.kind == "audio"
                and reference.metadata.get("role") == "prepared-speech"
            ],
            briefs=[brief.to_dict() for brief in briefs.briefs],
            replacement_plans=[plan.to_dict() for plan in plans.plans],
            replacement_candidates=[candidate.to_dict() for candidate in candidates.candidates],
            sample_approvals=[approval.to_dict() for approval in candidates.sample_approvals],
            replacement_reviews=[review.to_dict() for review in reviews.reviews],
            accepted_edits=[edit.to_dict() for edit in accepted.edits],
            dubbing=dubbing.to_dict(),
            prepared_speech=prepared_speech.to_dict(),
            engine=engine,
        )
    except (
        ProjectNotFound,
        DubbingError,
        PreparedSpeechError,
        ContinuityBriefError,
        EditStateError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
