"""Product-level workflow projections over canonical UV Studio state."""

from dataclasses import replace

from uv_studio.projects.dubbing import DubbingError, DubbingStore
from uv_studio.projects.dubbing_review import DubbingReviewError, DubbingReviewStore
from uv_studio.projects.dubbing_review_current import CurrentReviewError, CurrentReviewStore
from uv_studio.projects.models import compatibility_recipe_id
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.prepared_speech import PreparedSpeechError, PreparedSpeechStore
from uv_studio.projects.replacement_review import ReplacementReviewError, ReplacementReviewStore
from uv_studio.projects.store import ProjectStoreError

from .commercial import COMMERCIAL_PRODUCT_RECIPE_ID, commercial_product_workflow_state
from .dubbing import DUBBING_RECIPE_ID, dubbing_workflow_state
from .general_video import GENERAL_VIDEO_RECIPE_ID, general_video_workflow_state
from .models import (
    WORKFLOW_SCHEMA_VERSION,
    ProjectWorkflowState,
    WorkflowAction,
    WorkflowArtifact,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
    WorkflowWorkspace,
)
from .narrated import NARRATED_RECIPE_ID, narrated_workflow_state
from .project_workflow import project_workflow_state as _base_project_workflow_state
from .story import STORY_RECIPE_ID, story_workflow_state
from .targeted_edit import TARGETED_EDIT_RECIPE_ID, targeted_edit_workflow_state


def _current_targeted_outcome(state: ProjectWorkflowState) -> WorkflowArtifact | None:
    accepted_by_source: dict[str, list[str]] = {}
    for decision in state.user_decisions:
        if decision.get("kind") != "accepted_range_edit":
            continue
        source_path = decision.get("source_path")
        edit_id = decision.get("edit_id")
        if isinstance(source_path, str) and isinstance(edit_id, str):
            accepted_by_source.setdefault(source_path, []).append(edit_id)

    for artifact in state.recent_artifacts:
        if artifact.lifecycle != "render":
            continue
        source_path = artifact.metadata.get("source_path")
        edit_ids = artifact.metadata.get("edit_ids")
        expected = accepted_by_source.get(source_path) if isinstance(source_path, str) else None
        if expected and isinstance(edit_ids, (list, tuple)) and list(edit_ids) == expected:
            return artifact
    return None


def _without_consumed_accept_actions(
    state: ProjectWorkflowState,
    source_media,
) -> tuple[WorkflowAction, ...]:
    accepted_ids = {
        decision.get("edit_id")
        for decision in state.user_decisions
        if decision.get("kind") == "accepted_range_edit" and isinstance(decision.get("edit_id"), str)
    }
    if not accepted_ids:
        return state.next_actions

    try:
        reviews = {
            review.review_id: review
            for review in ReplacementReviewStore(source_media.project_store).load(state.project_id).reviews
        }
    except (ReplacementReviewError, ProjectStoreError):
        reviews = {}

    normalized: list[WorkflowAction] = []
    for action in state.next_actions:
        if action.action_id != "accept_replacement":
            normalized.append(action)
            continue
        properties = action.input_schema.get("properties")
        review_schema = properties.get("review_id") if isinstance(properties, dict) else None
        allowed = review_schema.get("enum") if isinstance(review_schema, dict) else None
        allowed_ids = tuple(value for value in allowed or () if isinstance(value, str))
        pending_ids = tuple(
            review_id
            for review_id in allowed_ids
            if (review := reviews.get(review_id)) is not None and review.edit_id not in accepted_ids
        )
        if not pending_ids:
            continue

        next_schema = dict(action.input_schema)
        next_properties = dict(properties) if isinstance(properties, dict) else {}
        next_review_schema = dict(review_schema) if isinstance(review_schema, dict) else {"type": "string"}
        next_review_schema["enum"] = pending_ids
        next_properties["review_id"] = next_review_schema
        next_schema["properties"] = next_properties
        normalized.append(
            replace(
                action,
                input_schema=next_schema,
                suggested_input={"review_id": pending_ids[0]},
            )
        )
    return tuple(normalized)


def _targeted_readiness(
    state: ProjectWorkflowState,
    current_outcome: WorkflowArtifact | None,
) -> tuple[WorkflowReadiness, str]:
    prerequisites = {item.prerequisite_id: item for item in state.prerequisites}
    render = prerequisites.get("capability.video.render_edits")
    source = prerequisites.get("source.video")
    brief = prerequisites.get("edit.brief")
    replacement = prerequisites.get("source.replacement_video")
    accepted = prerequisites.get("edit.accepted")

    if render is not None and not render.satisfied:
        hard_failure = any(
            diagnostic.code in {
                "targeted_edit_render_capability_unknown",
                "targeted_edit_render_capability_unavailable",
            }
            and diagnostic.severity == "error"
            for diagnostic in state.diagnostics
        )
        if hard_failure:
            return (
                WorkflowReadiness.UNAVAILABLE,
                "Точечное редактирование нельзя завершить в текущем runtime: локальная финальная сборка недоступна.",
            )
        return (
            WorkflowReadiness.SETUP_REQUIRED,
            "Завершите настройку локальной финальной сборки перед работой с этим сценарием.",
        )

    if source is not None and not source.satisfied:
        return (
            WorkflowReadiness.SETUP_REQUIRED,
            "Импортируйте исходное видео, чтобы начать точечное редактирование.",
        )

    if (
        brief is not None
        and brief.satisfied
        and replacement is not None
        and not replacement.satisfied
    ):
        return (
            WorkflowReadiness.SETUP_REQUIRED,
            "Задача изменения сохранена. Импортируйте отдельный видеоклип для замены выбранного фрагмента.",
        )

    if accepted is not None and accepted.satisfied and current_outcome is not None:
        return (
            WorkflowReadiness.READY,
            "Текущий мастер точно соответствует принятому состоянию правок.",
        )

    return state.readiness, state.summary


def _normalize_targeted_projection(
    state: ProjectWorkflowState,
    source_media,
) -> ProjectWorkflowState:
    """Keep read-only product truth aligned with current accepted/rendered revisions."""

    current_outcome = _current_targeted_outcome(state)
    readiness, summary = _targeted_readiness(state, current_outcome)
    return replace(
        state,
        readiness=readiness,
        summary=summary,
        current_outcome=current_outcome,
        next_actions=_without_consumed_accept_actions(state, source_media),
    )


def _dubbing_translation_action(dubbing_state) -> WorkflowAction:
    transcript_ids = tuple(item.dubbing_id for item in dubbing_state.transcripts)
    translation_ids = tuple(item.translation_id for item in dubbing_state.translations)
    return WorkflowAction(
        action_id="save_dubbing_translation",
        title="Сохранить проверенный перевод",
        explanation=(
            "Сохранить отредактированный перевод и привязать его к точной текущей ревизии transcript. "
            "Автоматический Argos-перевод остаётся только черновиком до этого действия."
        ),
        enabled=bool(transcript_ids),
        blocked_by=() if transcript_ids else ("dubbing.transcript",),
        prerequisite_ids=("dubbing.transcript",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["dubbing_id", "target_language", "segments"],
            "properties": {
                "dubbing_id": {"type": "string", "enum": transcript_ids},
                "target_language": {"type": "string", "minLength": 2, "maxLength": 64},
                "segments": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100000,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["segment_id", "text"],
                        "properties": {
                            "segment_id": {"type": "string", "minLength": 1, "maxLength": 128},
                            "text": {"type": "string", "minLength": 1, "maxLength": 8000},
                        },
                    },
                },
                "translation_id": {"type": "string", "enum": translation_ids},
            },
        },
        suggested_input={"dubbing_id": transcript_ids[0]} if transcript_ids else {},
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="dubbing_translation",
    )


def _normalize_dubbing_projection(
    state: ProjectWorkflowState,
    source_media,
) -> ProjectWorkflowState:
    """Align Dubbing product truth with current bytes and explicit-current Review semantics."""

    store = source_media.project_store
    diagnostics = list(state.diagnostics)

    try:
        project = store.load_project(state.project_id)
        audio_store = ProjectPreparedAudioStore(store)
        verified_audio_ids: list[str] = []
        invalid_audio_ids: list[str] = []
        for reference in project.artifacts:
            if reference.kind != "audio" or reference.metadata.get("role") != "prepared-speech":
                continue
            try:
                audio_store.resolve_verified(state.project_id, reference.id)
            except (PreparedAudioError, ProjectStoreError):
                invalid_audio_ids.append(reference.id)
                continue
            verified_audio_ids.append(reference.id)
    except ProjectStoreError:
        verified_audio_ids = []
        invalid_audio_ids = []

    if invalid_audio_ids:
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_prepared_audio_unverified",
                severity="warning" if verified_audio_ids else "error",
                message=(
                    "PreparedAudio исключено из доступных вариантов, потому что текущие bytes не прошли "
                    "проверку: " + ", ".join(invalid_audio_ids)
                ),
            )
        )

    try:
        dubbing_state = DubbingStore(store).validate_project(state.project_id)
    except (DubbingError, ProjectStoreError):
        dubbing_state = None

    try:
        speech_state = PreparedSpeechStore(store).validate_project(state.project_id)
        takes = speech_state.takes
    except (PreparedSpeechError, ProjectStoreError):
        takes = ()

    review_store = DubbingReviewStore(store)
    current_store = CurrentReviewStore(store)
    try:
        history = review_store.load_reviews(state.project_id).reviews
        accepted = review_store.load_accepted(state.project_id, validate_current=True).edits
        accepted_review_ids = {item.review_id for item in accepted}
        current_approved_ids: list[str] = []
        for take in takes:
            try:
                current_id = current_store.resolve_current(state.project_id, take.take_id, history)
                if current_id is None:
                    continue
                review = review_store.validate_review(state.project_id, current_id)
            except (CurrentReviewError, DubbingReviewError):
                continue
            if review.verdict == "approved":
                current_approved_ids.append(review.review_id)
        pending_review_ids = tuple(
            review_id for review_id in current_approved_ids if review_id not in accepted_review_ids
        )
    except (DubbingReviewError, CurrentReviewError, ProjectStoreError):
        current_approved_ids = []
        pending_review_ids = ()

    transcribe_action = next(
        (item for item in state.next_actions if item.action_id == "transcribe_dubbing_source"),
        None,
    )
    asr_available = bool(
        transcribe_action is not None
        and "capability.speech.transcribe" not in transcribe_action.blocked_by
    )

    prerequisites: list[WorkflowPrerequisite] = []
    inserted_asr = False
    inserted_audio = False
    for prerequisite in state.prerequisites:
        if prerequisite.prerequisite_id == "dubbing.transcript" and not inserted_asr:
            prerequisites.append(
                WorkflowPrerequisite(
                    prerequisite_id="capability.speech.transcribe",
                    title="Локальное распознавание речи (необязательно)",
                    explanation=(
                        "ASR нужен только для автоматического черновика. Проверенный transcript можно "
                        "ввести вручную без этого capability."
                    ),
                    satisfied=asr_available,
                    resolution=(
                        None
                        if asr_available
                        else "Настройте локальный whisper.cpp только если нужен автоматический ASR-черновик."
                    ),
                )
            )
            inserted_asr = True
        if prerequisite.prerequisite_id == "dubbing.prepared_speech" and not inserted_audio:
            prerequisites.append(
                WorkflowPrerequisite(
                    prerequisite_id="source.prepared_audio",
                    title="Речевая дорожка",
                    explanation=(
                        "До привязки новая речь должна быть импортирована, записана или создана TTS "
                        "как проверенный project-owned PreparedAudio."
                    ),
                    satisfied=bool(verified_audio_ids),
                    resolution=(
                        None
                        if verified_audio_ids
                        else "Импортируйте речевую дорожку либо подготовьте её через TTS с явным D-017 согласием."
                    ),
                )
            )
            inserted_audio = True
        if prerequisite.prerequisite_id == "dubbing.review":
            prerequisites.append(
                replace(
                    prerequisite,
                    satisfied=bool(current_approved_ids),
                    resolution=(
                        None
                        if current_approved_ids
                        else "Создайте и одобрите актуальный Review выбранной подготовленной речи."
                    ),
                )
            )
        else:
            prerequisites.append(prerequisite)

    actions: list[WorkflowAction] = []
    translation_inserted = False
    for action in state.next_actions:
        if action.action_id == "transcribe_dubbing_source":
            properties = dict(action.input_schema.get("properties", {}))
            properties["start_us"] = {"type": "integer", "minimum": 0}
            properties["end_us"] = {"type": "integer", "minimum": 1}
            schema = dict(action.input_schema)
            schema["properties"] = properties
            actions.append(
                replace(
                    action,
                    prerequisite_ids=("source.video", "capability.speech.transcribe"),
                    input_schema=schema,
                )
            )
            continue
        if action.action_id == "attach_prepared_speech":
            properties = dict(action.input_schema.get("properties", {}))
            properties["audio_id"] = {
                "type": "string",
                "minLength": 1,
                "maxLength": 512,
                "enum": tuple(verified_audio_ids),
            }
            schema = dict(action.input_schema)
            schema["properties"] = properties
            transcript_ready = any(
                item.prerequisite_id == "dubbing.transcript" and item.satisfied
                for item in prerequisites
            )
            actions.append(
                replace(
                    action,
                    enabled=transcript_ready and bool(verified_audio_ids),
                    blocked_by=tuple(
                        item
                        for item, ready in (
                            ("dubbing.transcript", transcript_ready),
                            ("source.prepared_audio", bool(verified_audio_ids)),
                        )
                        if not ready
                    ),
                    prerequisite_ids=("dubbing.transcript", "source.prepared_audio"),
                    input_schema=schema,
                    suggested_input=(
                        {
                            **({"dubbing_id": next(iter(properties["dubbing_id"].get("enum", ())), "")} if properties.get("dubbing_id") else {}),
                            "audio_id": verified_audio_ids[0],
                        }
                        if verified_audio_ids
                        else {}
                    ),
                )
            )
            continue
        if action.action_id == "review_prepared_speech" and not translation_inserted:
            if dubbing_state is not None:
                actions.append(_dubbing_translation_action(dubbing_state))
            translation_inserted = True
        if action.action_id == "accept_dubbing_review":
            properties = dict(action.input_schema.get("properties", {}))
            properties["review_id"] = {
                "type": "string",
                "minLength": 1,
                "maxLength": 512,
                "enum": pending_review_ids,
            }
            schema = dict(action.input_schema)
            schema["properties"] = properties
            actions.append(
                replace(
                    action,
                    enabled=bool(pending_review_ids),
                    blocked_by=() if pending_review_ids else ("dubbing.review",),
                    input_schema=schema,
                    suggested_input={"review_id": pending_review_ids[0]} if pending_review_ids else {},
                )
            )
            continue
        actions.append(action)

    return replace(
        state,
        prerequisites=tuple(prerequisites),
        next_actions=tuple(actions),
        diagnostics=tuple(diagnostics),
    )


def project_workflow_state(project, recipe, registry, source_media) -> ProjectWorkflowState:
    """Dispatch supported Product Orchestrator projections without duplicating canonical state."""

    recipe_id = compatibility_recipe_id(project)
    if recipe is not None and recipe_id == TARGETED_EDIT_RECIPE_ID:
        state = targeted_edit_workflow_state(project, recipe, registry, source_media)
        return _normalize_targeted_projection(state, source_media)
    if recipe is not None and recipe_id == DUBBING_RECIPE_ID:
        state = dubbing_workflow_state(project, recipe, registry, source_media)
        return _normalize_dubbing_projection(state, source_media)
    if recipe is not None and recipe_id == GENERAL_VIDEO_RECIPE_ID:
        return general_video_workflow_state(project, recipe, registry, source_media)
    if recipe is not None and recipe_id == NARRATED_RECIPE_ID:
        return narrated_workflow_state(project, recipe, registry, source_media)
    if recipe is not None and recipe_id == STORY_RECIPE_ID:
        return story_workflow_state(project, recipe, registry, source_media)
    if recipe is not None and recipe_id == COMMERCIAL_PRODUCT_RECIPE_ID:
        return commercial_product_workflow_state(project, recipe, registry, source_media)
    return _base_project_workflow_state(project, recipe, registry, source_media)


__all__ = [
    "COMMERCIAL_PRODUCT_RECIPE_ID",
    "DUBBING_RECIPE_ID",
    "GENERAL_VIDEO_RECIPE_ID",
    "NARRATED_RECIPE_ID",
    "ProjectWorkflowState",
    "STORY_RECIPE_ID",
    "TARGETED_EDIT_RECIPE_ID",
    "WORKFLOW_SCHEMA_VERSION",
    "WorkflowAction",
    "WorkflowArtifact",
    "WorkflowDiagnostic",
    "WorkflowPrerequisite",
    "WorkflowReadiness",
    "WorkflowWorkspace",
    "commercial_product_workflow_state",
    "dubbing_workflow_state",
    "general_video_workflow_state",
    "narrated_workflow_state",
    "project_workflow_state",
    "story_workflow_state",
    "targeted_edit_workflow_state",
]
