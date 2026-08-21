"""Product-level semantic actions over the existing canonical Dubbing domains.

This service is deliberately not a workflow store. It translates Product Orchestrator
user actions into the D-034/D-035/D-037 command services that already own canonical
transcript, translation, PreparedSpeech, Review and AcceptedDubbing state.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from uv_studio.projects.store import ProjectStore

from .dubbing_commands import (
    AttachPreparedSpeechCommand,
    DubbingCommandService,
    ImportDubbingTranscriptCommand,
    ImportTranscriptSegmentInput,
    TranslationSegmentInput,
    UpsertDubbingTranslationCommand,
)
from .dubbing_review_commands import (
    AcceptDubbingReviewCommand,
    DubbingReviewCommandService,
    LoudnessMeasure,
    ReviewPreparedSpeechCommand,
)

SUPPORTED_COMPOSITION_POLICY = "replace_source_audio_range"


def _transcript_command(payload: Mapping[str, Any]) -> ImportDubbingTranscriptCommand:
    return ImportDubbingTranscriptCommand(
        source_id=str(payload["source_id"]),
        language=str(payload["language"]),
        start_us=int(payload["start_us"]),
        end_us=int(payload["end_us"]),
        dubbing_id=payload.get("dubbing_id"),
        segments=tuple(
            ImportTranscriptSegmentInput(
                segment_id=str(item["segment_id"]),
                start_us=int(item["start_us"]),
                end_us=int(item["end_us"]),
                text=str(item["text"]),
                speaker_label=item.get("speaker_label"),
                confidence=item.get("confidence"),
            )
            for item in payload["segments"]
        ),
    )


class DubbingWorkflowService:
    """Delegate Dubbing Product Orchestrator actions to canonical semantic services."""

    def __init__(self, project_store: ProjectStore, loudness_measure: LoudnessMeasure) -> None:
        self.commands = DubbingCommandService(project_store)
        self.reviews = DubbingReviewCommandService(project_store, loudness_measure)

    def import_transcript(self, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.commands.import_transcript(project_id, _transcript_command(payload)).to_dict()

    def accept_asr_transcript(self, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.commands.accept_asr_transcript(project_id, _transcript_command(payload)).to_dict()

    def save_translation(self, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        command = UpsertDubbingTranslationCommand(
            dubbing_id=str(payload["dubbing_id"]),
            target_language=str(payload["target_language"]),
            translation_id=payload.get("translation_id"),
            segments=tuple(
                TranslationSegmentInput(
                    segment_id=str(item["segment_id"]),
                    text=str(item["text"]),
                )
                for item in payload["segments"]
            ),
        )
        return self.commands.upsert_translation(project_id, command).to_dict()

    def attach_prepared_speech(self, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        command = AttachPreparedSpeechCommand(
            dubbing_id=str(payload["dubbing_id"]),
            audio_id=str(payload["audio_id"]),
            translation_id=payload.get("translation_id"),
            segment_id=payload.get("segment_id"),
            take_id=payload.get("take_id"),
        )
        return self.commands.attach_prepared_speech(project_id, command).to_dict()

    def review_prepared_speech(self, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        command = ReviewPreparedSpeechCommand(
            take_id=str(payload["take_id"]),
            verdict=str(payload["verdict"]),
            content_fidelity_confirmed=bool(payload["content_fidelity_confirmed"]),
            synchronization_confirmed=bool(payload["synchronization_confirmed"]),
            note=payload.get("note"),
            review_id=payload.get("review_id"),
        )
        return self.reviews.review_prepared_speech(project_id, command).to_dict()

    def accept_review(self, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        # D-036 has not promoted any background-preserving policy to a supported
        # production contract. The Product Orchestrator therefore never accepts a
        # caller-selected policy and pins the only currently executable one.
        command = AcceptDubbingReviewCommand(
            review_id=str(payload["review_id"]),
            composition_policy=SUPPORTED_COMPOSITION_POLICY,
            accepted_id=payload.get("accepted_id"),
        )
        return self.reviews.accept_dubbing_review(project_id, command).to_dict()


__all__ = ["DubbingWorkflowService", "SUPPORTED_COMPOSITION_POLICY"]
