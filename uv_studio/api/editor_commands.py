"""UV Studio-owned semantic editor command HTTP boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import get_local_ffmpeg_adapter
from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.capabilities import CapabilityRegistry
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import (
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.editor import MLTTimelineAdapter
from uv_studio.editor.commands import EditorCommandError, EditorCommandService, SelectRangeCommand
from uv_studio.editor.dubbing_alignment_commands import (
    AcceptDubbingAlignmentCommand,
    AlignmentMarkInput,
    DubbingAlignmentCommandError,
    DubbingAlignmentCommandService,
)
from uv_studio.editor.dubbing_commands import (
    AttachPreparedSpeechCommand,
    DubbingCommandError,
    DubbingCommandService,
    ImportDubbingTranscriptCommand,
    ImportTranscriptSegmentInput,
    TranslationSegmentInput,
    UpsertDubbingTranslationCommand,
)
from uv_studio.editor.dubbing_review_commands import (
    AcceptDubbingReviewCommand,
    DubbingReviewCommandError,
    DubbingReviewCommandService,
    LoudnessMeasure,
    ReviewPreparedSpeechCommand,
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
from uv_studio.projects.dubbing_alignment import (
    DubbingAlignmentError,
    DubbingAlignmentNotFound,
    DubbingAlignmentStore,
)
from uv_studio.projects.dubbing_review import (
    DubbingReviewError,
    DubbingReviewNotFound,
    DubbingReviewStore,
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
_AUDIO_LOUDNESS_OFFER_ID = "local_ffmpeg.audio_measure_loudness"


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


class AlignmentMarkCommandPayload(_StrictModel):
    mark_id: str = Field(min_length=1, max_length=128)
    unit: Literal["word", "token", "phoneme"]
    text: str = Field(min_length=1, max_length=512)
    audio_start_us: int = Field(ge=0)
    audio_end_us: int = Field(gt=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class AcceptDubbingAlignmentCommandPayload(_StrictModel):
    command: Literal["accept_dubbing_alignment"]
    take_id: str = Field(min_length=1, max_length=128)
    marks: list[AlignmentMarkCommandPayload] = Field(min_length=1, max_length=100_000)
    alignment_id: str | None = Field(default=None, min_length=1, max_length=128)


class ReviewPreparedSpeechCommandPayload(_StrictModel):
    command: Literal["review_prepared_speech"]
    take_id: str = Field(min_length=1, max_length=128)
    verdict: Literal["approved", "needs_revision", "rejected"]
    content_fidelity_confirmed: bool
    synchronization_confirmed: bool
    note: str | None = Field(default=None, max_length=4000)


class AcceptDubbingReviewCommandPayload(_StrictModel):
    command: Literal["accept_dubbing_review"]
    review_id: str = Field(min_length=1, max_length=128)
    composition_policy: Literal[
        "replace_source_audio_range",
        "duck_source_mix",
        "replace_dialogue_preserve_background",
    ]


EditorCommandPayload = Annotated[
    Union[
        SelectRangeCommandPayload,
        ImportDubbingTranscriptCommandPayload,
        AcceptAsrTranscriptCommandPayload,
        UpsertDubbingTranslationCommandPayload,
        AttachPreparedSpeechCommandPayload,
        AcceptDubbingAlignmentCommandPayload,
        ReviewPreparedSpeechCommandPayload,
        AcceptDubbingReviewCommandPayload,
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


class AcceptDubbingAlignmentResultPayload(_StrictModel):
    command: Literal["accept_dubbing_alignment"]
    payload: dict


class ReviewPreparedSpeechResultPayload(_StrictModel):
    command: Literal["review_prepared_speech"]
    payload: dict


class AcceptDubbingReviewResultPayload(_StrictModel):
    command: Literal["accept_dubbing_review"]
    payload: dict


EditorCommandResultPayload = Union[
    SelectRangeCommandResultPayload,
    ImportDubbingTranscriptResultPayload,
    AcceptAsrTranscriptResultPayload,
    UpsertDubbingTranslationResultPayload,
    AttachPreparedSpeechResultPayload,
    AcceptDubbingAlignmentResultPayload,
    ReviewPreparedSpeechResultPayload,
    AcceptDubbingReviewResultPayload,
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
    dubbing_alignments: dict
    dubbing_reviews: list[dict]
    accepted_dubbing: list[dict]
    engine: dict


def get_dubbing_loudness_measure(
    local_ffmpeg: LocalFFmpegAdapter = Depends(get_local_ffmpeg_adapter),
    registry: CapabilityRegistry = Depends(get_capability_registry),
) -> LoudnessMeasure:
    """Return a server-owned analyzer; callers never provide measured values."""

    def measure(project_id: str, audio_id: str) -> Mapping[str, Any]:
        offer = registry.get_offer(_AUDIO_LOUDNESS_OFFER_ID)
        result = local_ffmpeg.execute(
            project_id=project_id,
            offer=offer,
            payload={"audio_id": audio_id},
        )
        return dict(result.output)

    return measure


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
    if isinstance(exc, DubbingAlignmentNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dubbing alignment not found")
    if isinstance(exc, DubbingReviewNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dubbing review not found")
    if isinstance(exc, (CapabilityToolUnavailable, UnsupportedCapabilityExecution)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local audio review tooling is unavailable in this installation",
        )
    if isinstance(exc, CapabilityToolFailed):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Local audio review measurement failed",
        )
    if isinstance(exc, InvalidCapabilityInput):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(
        exc,
        (
            EditorCommandError,
            DubbingCommandError,
            DubbingAlignmentCommandError,
            DubbingReviewCommandError,
            DubbingError,
            DubbingAlignmentError,
            DubbingReviewError,
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
    loudness_measure: LoudnessMeasure = Depends(get_dubbing_loudness_measure),
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
        if isinstance(payload, AcceptDubbingAlignmentCommandPayload):
            result = DubbingAlignmentCommandService(store).accept_alignment(
                project_id,
                AcceptDubbingAlignmentCommand(
                    take_id=payload.take_id,
                    alignment_id=payload.alignment_id,
                    marks=tuple(
                        AlignmentMarkInput(
                            mark_id=item.mark_id,
                            unit=item.unit,
                            text=item.text,
                            audio_start_us=item.audio_start_us,
                            audio_end_us=item.audio_end_us,
                            confidence=item.confidence,
                        )
                        for item in payload.marks
                    ),
                ),
            )
            return AcceptDubbingAlignmentResultPayload.model_validate(result.to_dict())
        if isinstance(payload, ReviewPreparedSpeechCommandPayload):
            result = DubbingReviewCommandService(store, loudness_measure).review_prepared_speech(
                project_id,
                ReviewPreparedSpeechCommand(
                    take_id=payload.take_id,
                    verdict=payload.verdict,
                    content_fidelity_confirmed=payload.content_fidelity_confirmed,
                    synchronization_confirmed=payload.synchronization_confirmed,
                    note=payload.note,
                ),
            )
            return ReviewPreparedSpeechResultPayload.model_validate(result.to_dict())
        if isinstance(payload, AcceptDubbingReviewCommandPayload):
            result = DubbingReviewCommandService(store, loudness_measure).accept_dubbing_review(
                project_id,
                AcceptDubbingReviewCommand(
                    review_id=payload.review_id,
                    composition_policy=payload.composition_policy,
                ),
            )
            return AcceptDubbingReviewResultPayload.model_validate(result.to_dict())
        raise EditorCommandError("unsupported editor command")
    except (
        ProjectNotFound,
        SourceMediaNotFound,
        PreparedAudioNotFound,
        DubbingTranscriptNotFound,
        DubbingTranslationNotFound,
        PreparedSpeechTakeNotFound,
        DubbingAlignmentNotFound,
        DubbingReviewNotFound,
        CapabilityToolUnavailable,
        UnsupportedCapabilityExecution,
        CapabilityToolFailed,
        InvalidCapabilityInput,
        EditorCommandError,
        DubbingCommandError,
        DubbingAlignmentCommandError,
        DubbingReviewCommandError,
        DubbingError,
        DubbingAlignmentError,
        DubbingReviewError,
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
    """Return canonical state plus bounded derived engine/workflow summaries."""

    try:
        project = store.load_project(project_id)
        briefs = RangeContinuityBriefStore(store).load(project_id)
        plans = ReplacementPlanStore(store).load(project_id)
        candidates = ReplacementCandidateStore(store).load(project_id)
        reviews = ReplacementReviewStore(store).load(project_id)
        accepted = RangeEditStateStore(store).load(project_id)
        dubbing = DubbingStore(store).load(project_id, validate_current=True)
        prepared_speech = PreparedSpeechStore(store).load(project_id, validate_current=True)
        dubbing_alignments = DubbingAlignmentStore(store).load(project_id, validate_current=True)
        dubbing_review_store = DubbingReviewStore(store)
        dubbing_reviews = dubbing_review_store.load_reviews(project_id)
        accepted_dubbing = dubbing_review_store.load_accepted(project_id, validate_current=True)
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
            dubbing_alignments=dubbing_alignments.to_dict(),
            dubbing_reviews=[review.to_dict() for review in dubbing_reviews.reviews],
            accepted_dubbing=[edit.to_dict() for edit in accepted_dubbing.edits],
            engine=engine,
        )
    except (
        ProjectNotFound,
        DubbingError,
        DubbingAlignmentError,
        DubbingReviewError,
        PreparedSpeechError,
        ContinuityBriefError,
        EditStateError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
