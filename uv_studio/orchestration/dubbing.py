"""Read-only Product Orchestrator projection for the permanent Dubbing journey."""

from __future__ import annotations

from collections.abc import Iterable

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.dubbing import DubbingError, DubbingStore
from uv_studio.projects.dubbing_review import DubbingReviewError, DubbingReviewStore
from uv_studio.projects.models import ProjectDocument, ProjectReference
from uv_studio.projects.prepared_speech import PreparedSpeechError, PreparedSpeechStore
from uv_studio.projects.source_media import (
    ProjectSourceMediaStore,
    SourceMediaError,
    SourceMediaNotFound,
)
from uv_studio.projects.store import ProjectStoreError
from uv_studio.recipes.models import RecipeDefinition

from .models import (
    ProjectWorkflowState,
    WorkflowAction,
    WorkflowArtifact,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
    WorkflowWorkspace,
)

DUBBING_RECIPE_ID = "dubbing"
DUBBING_WORKSPACE_ID = "dubbing"
_RENDER_CAPABILITY_ID = "video.render_dubbing"
_LOUDNESS_CAPABILITY_ID = "audio.measure_loudness"
_ASR_CAPABILITY_ID = "speech.transcribe"
_SUPPORTED_COMPOSITION_POLICY = "replace_source_audio_range"


def _artifact(reference: ProjectReference) -> WorkflowArtifact:
    return WorkflowArtifact(
        artifact_id=reference.id,
        kind=reference.kind,
        path=reference.path,
        lifecycle=str(reference.metadata.get("lifecycle", "")),
        metadata=dict(reference.metadata),
    )


def _enum_property(values: Iterable[str]) -> dict[str, object]:
    values = tuple(values)
    result: dict[str, object] = {"type": "string", "minLength": 1, "maxLength": 512}
    if values:
        result["enum"] = values
    return result


def _local_free_status(
    registry: CapabilityRegistry,
    capability_id: str,
) -> tuple[bool, bool, str | None]:
    """Return available/configurable/reason without widening to remote providers."""

    try:
        decision = select_offer(
            registry,
            capability_id,
            policy=SelectionPolicy.LOCAL_FREE_FIRST,
        )
        return True, False, decision.reason
    except UnknownCapability:
        return False, False, "capability отсутствует в текущем runtime"
    except NoEligibleOffer:
        try:
            offers = registry.offers_for(capability_id)
        except UnknownCapability:
            return False, False, "capability отсутствует в текущем runtime"
        configurable = any(
            offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
            and offer.cost_class is CostClass.FREE
            and offer.locality is LocalityClass.LOCAL
            for offer in offers
        )
        reasons = [offer.reason for offer in offers if offer.reason]
        return False, configurable, reasons[0] if reasons else "нет доступного local/free offer"


def _current_outcome(
    project: ProjectDocument,
    accepted_by_source: dict[str, tuple[str, ...]],
) -> WorkflowArtifact | None:
    for reference in reversed(project.artifacts):
        if reference.kind != "video" or reference.metadata.get("lifecycle") != "dubbing_render":
            continue
        source_id = reference.metadata.get("source_id")
        accepted_ids = reference.metadata.get("accepted_dubbing_ids")
        expected = accepted_by_source.get(source_id) if isinstance(source_id, str) else None
        if expected and isinstance(accepted_ids, (list, tuple)) and tuple(accepted_ids) == expected:
            return _artifact(reference)
    return None


def dubbing_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project Dubbing state without owning any durable workflow data."""

    store = source_media.project_store
    diagnostics: list[WorkflowDiagnostic] = []

    verified_videos: list[ProjectReference] = []
    invalid_video_ids: list[str] = []
    for source in project.sources:
        if source.kind != "video":
            continue
        try:
            reference, _path = source_media.resolve_verified(
                project.project_id,
                source.id,
                expected_kind="video",
            )
        except (SourceMediaError, SourceMediaNotFound, ProjectStoreError):
            invalid_video_ids.append(source.id)
            continue
        verified_videos.append(reference)
    if invalid_video_ids:
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_source_unverified",
                severity="warning" if verified_videos else "error",
                message=(
                    "Видео исключены из Dubbing, потому что project-owned bytes отсутствуют или "
                    "изменились: " + ", ".join(invalid_video_ids)
                ),
            )
        )

    try:
        dubbing_state = DubbingStore(store).validate_project(project.project_id)
        transcripts = dubbing_state.transcripts
        translations = dubbing_state.translations
    except (DubbingError, ProjectStoreError) as exc:
        transcripts = ()
        translations = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_state_invalid",
                severity="error",
                message=f"Каноническое состояние текста дубляжа не прошло проверку: {exc}",
            )
        )

    try:
        speech_state = PreparedSpeechStore(store).validate_project(project.project_id)
        takes = speech_state.takes
    except (PreparedSpeechError, ProjectStoreError) as exc:
        takes = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_prepared_speech_invalid",
                severity="error",
                message=f"Подготовленная речь не прошла текущую проверку: {exc}",
            )
        )

    review_store = DubbingReviewStore(store)
    try:
        review_history = review_store.load_reviews(project.project_id).reviews
    except (DubbingReviewError, ProjectStoreError) as exc:
        review_history = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_review_history_invalid",
                severity="warning",
                message=f"Историю Dubbing Review не удалось прочитать: {exc}",
            )
        )

    current_reviews = []
    for review in review_history:
        try:
            current_reviews.append(review_store.validate_review(project.project_id, review.review_id))
        except DubbingReviewError:
            continue
    approved_reviews = tuple(item for item in current_reviews if item.verdict == "approved")

    try:
        accepted = review_store.load_accepted(project.project_id, validate_current=True).edits
    except (DubbingReviewError, ProjectStoreError) as exc:
        accepted = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_accepted_state_invalid",
                severity="error",
                message=f"Принятый дубляж не прошёл текущую проверку: {exc}",
            )
        )

    accepted_review_ids = {item.review_id for item in accepted}
    pending_approved_reviews = tuple(
        item for item in approved_reviews if item.review_id not in accepted_review_ids
    )

    prepared_audio = tuple(
        reference
        for reference in project.artifacts
        if reference.kind == "audio" and reference.metadata.get("role") == "prepared-speech"
    )

    render_ready, render_configurable, render_reason = _local_free_status(
        registry, _RENDER_CAPABILITY_ID
    )
    loudness_ready, loudness_configurable, loudness_reason = _local_free_status(
        registry, _LOUDNESS_CAPABILITY_ID
    )
    asr_ready, asr_configurable, asr_reason = _local_free_status(registry, _ASR_CAPABILITY_ID)

    if not render_ready:
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_render_runtime_unavailable",
                severity="warning" if render_configurable else "error",
                message=(
                    "Локальный финальный рендер требует настройки runtime."
                    if render_configurable
                    else f"Локальный финальный рендер недоступен: {render_reason}"
                ),
            )
        )
    if not loudness_ready:
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_review_runtime_unavailable",
                severity="warning" if loudness_configurable else "error",
                message=(
                    "Проверка громкости требует настройки локального runtime."
                    if loudness_configurable
                    else f"Локальная проверка громкости недоступна: {loudness_reason}"
                ),
            )
        )
    if not asr_ready:
        diagnostics.append(
            WorkflowDiagnostic(
                code="dubbing_asr_optional_unavailable",
                severity="info",
                message=(
                    "Локальное распознавание речи требует настройки; текст можно импортировать вручную."
                    if asr_configurable
                    else f"Локальное распознавание речи сейчас недоступно; текст можно импортировать вручную. {asr_reason or ''}".strip()
                ),
            )
        )

    source_ready = bool(verified_videos)
    transcript_ready = bool(transcripts)
    take_ready = bool(takes)
    review_ready = bool(approved_reviews)
    accepted_ready = bool(accepted)

    accepted_by_source: dict[str, tuple[str, ...]] = {}
    for source in verified_videos:
        accepted_by_source[source.id] = tuple(
            item.accepted_id
            for item in sorted(
                (edit for edit in accepted if edit.source_id == source.id),
                key=lambda edit: (edit.target_start_us, edit.target_end_us, edit.accepted_id),
            )
        )
    accepted_by_source = {key: value for key, value in accepted_by_source.items() if value}
    current_outcome = _current_outcome(project, accepted_by_source)

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="source.video",
            title="Видео для дубляжа",
            explanation="Нужно проверенное project-owned видео с исходной речью.",
            satisfied=source_ready,
            resolution=None if source_ready else "Импортируйте видео для дубляжа.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="dubbing.transcript",
            title="Проверенный текст речи",
            explanation="ASR остаётся черновиком, пока текст явно не принят в проект.",
            satisfied=transcript_ready,
            resolution=(
                None
                if transcript_ready
                else "Импортируйте текст вручную или выполните локальное распознавание и примите результат."
            ),
        ),
        WorkflowPrerequisite(
            prerequisite_id="dubbing.prepared_speech",
            title="Подготовленная новая речь",
            explanation="Речь должна быть project-owned и привязана к текущей ревизии текста.",
            satisfied=take_ready,
            resolution=None if take_ready else "Импортируйте/подготовьте речь и привяжите её к тексту.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.audio.measure_loudness",
            title="Локальная проверка аудио",
            explanation="Review измеряет громкость и true peak серверным FFmpeg-инструментом.",
            satisfied=loudness_ready,
            resolution=(
                None
                if loudness_ready
                else "Настройте локальный FFmpeg runtime перед Review."
            ),
        ),
        WorkflowPrerequisite(
            prerequisite_id="dubbing.review",
            title="Одобренный Review",
            explanation="До принятия нужны измеримые проверки и явное подтверждение содержания/синхронизации.",
            satisfied=review_ready,
            resolution=None if review_ready else "Проверьте подготовленную речь и одобрите актуальный Review.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="dubbing.accepted",
            title="Принятый дубляж",
            explanation="Финальный рендер материализует только явно принятые Dubbing edits.",
            satisfied=accepted_ready,
            resolution=None if accepted_ready else "Примите одобренный актуальный Review.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.video.render_dubbing",
            title="Локальный финальный рендер",
            explanation="Мастер собирается существующим local/free `video.render_dubbing` capability.",
            satisfied=render_ready,
            resolution=None if render_ready else "Настройте локальные FFmpeg/FFprobe инструменты.",
        ),
    )

    source_ids = tuple(item.id for item in verified_videos)
    dubbing_ids = tuple(item.dubbing_id for item in transcripts)
    audio_ids = tuple(item.id for item in prepared_audio)
    take_ids = tuple(item.take_id for item in takes)
    pending_review_ids = tuple(item.review_id for item in pending_approved_reviews)
    accepted_source_ids = tuple(accepted_by_source)

    import_transcript = WorkflowAction(
        action_id="import_dubbing_transcript",
        title="Сохранить проверенный текст речи",
        explanation="Создать/обновить канонический transcript из явно введённого пользователем текста.",
        enabled=source_ready,
        blocked_by=() if source_ready else ("source.video",),
        prerequisite_ids=("source.video",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["source_id", "language", "start_us", "end_us", "segments"],
            "properties": {
                "source_id": _enum_property(source_ids),
                "language": {"type": "string", "minLength": 2, "maxLength": 64},
                "start_us": {"type": "integer", "minimum": 0},
                "end_us": {"type": "integer", "minimum": 1},
                "dubbing_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "segments": {"type": "array", "minItems": 1, "maxItems": 100000},
            },
        },
        suggested_input={"source_id": source_ids[0], "language": "ru"} if source_ids else {},
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="dubbing_transcript",
    )

    transcribe = WorkflowAction(
        action_id="transcribe_dubbing_source",
        title="Распознать речь локально",
        explanation="Получить ASR-черновик через configured local/free whisper.cpp; результат ещё не становится каноническим текстом.",
        enabled=source_ready and asr_ready,
        blocked_by=tuple(
            item
            for item, ready in (("source.video", source_ready), ("capability.speech.transcribe", asr_ready))
            if not ready
        ),
        prerequisite_ids=("source.video",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["source_id"],
            "properties": {
                "source_id": _enum_property(source_ids),
                "language": {"type": "string", "minLength": 2, "maxLength": 64},
            },
        },
        suggested_input={"source_id": source_ids[0]} if source_ids else {},
        execution_class="capability",
        authorization_class="none",
        capability_id=_ASR_CAPABILITY_ID,
        expected_result="asr_draft",
    )

    accept_asr = WorkflowAction(
        action_id="accept_asr_transcript",
        title="Принять проверенный ASR-текст",
        explanation="После проверки ASR-черновика явно сохранить его как текущий канонический transcript.",
        enabled=source_ready,
        blocked_by=() if source_ready else ("source.video",),
        prerequisite_ids=("source.video",),
        input_schema=import_transcript.input_schema,
        suggested_input=import_transcript.suggested_input,
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="dubbing_transcript",
    )

    attach_speech = WorkflowAction(
        action_id="attach_prepared_speech",
        title="Привязать подготовленную речь",
        explanation="Привязать project-owned prepared audio к текущей ревизии transcript/translation.",
        enabled=transcript_ready and bool(audio_ids),
        blocked_by=tuple(
            item
            for item, ready in (("dubbing.transcript", transcript_ready), ("source.prepared_audio", bool(audio_ids)))
            if not ready
        ),
        prerequisite_ids=("dubbing.transcript",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["dubbing_id", "audio_id"],
            "properties": {
                "dubbing_id": _enum_property(dubbing_ids),
                "audio_id": _enum_property(audio_ids),
                "translation_id": _enum_property(item.translation_id for item in translations),
                "segment_id": {"type": "string", "minLength": 1, "maxLength": 128},
            },
        },
        suggested_input=(
            {"dubbing_id": dubbing_ids[0], "audio_id": audio_ids[0]}
            if dubbing_ids and audio_ids
            else {}
        ),
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="prepared_speech_take",
    )

    review_speech = WorkflowAction(
        action_id="review_prepared_speech",
        title="Проверить новую речь",
        explanation="Измерить timing/loudness и зафиксировать явную оценку содержания и синхронизации.",
        enabled=take_ready and loudness_ready,
        blocked_by=tuple(
            item
            for item, ready in (("dubbing.prepared_speech", take_ready), ("capability.audio.measure_loudness", loudness_ready))
            if not ready
        ),
        prerequisite_ids=("dubbing.prepared_speech", "capability.audio.measure_loudness"),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["take_id", "verdict", "content_fidelity_confirmed", "synchronization_confirmed"],
            "properties": {
                "take_id": _enum_property(take_ids),
                "verdict": {"type": "string", "enum": ["approved", "needs_revision", "rejected"]},
                "content_fidelity_confirmed": {"type": "boolean"},
                "synchronization_confirmed": {"type": "boolean"},
                "note": {"type": "string", "maxLength": 4000},
            },
        },
        suggested_input={"take_id": take_ids[0]} if take_ids else {},
        execution_class="domain_operation",
        authorization_class="none",
        capability_id=None,
        expected_result="dubbing_review",
    )

    accept_review = WorkflowAction(
        action_id="accept_dubbing_review",
        title="Принять проверенный дубляж",
        explanation="Зафиксировать immutable AcceptedDubbingEdit только из актуального approved Review.",
        enabled=bool(pending_review_ids),
        blocked_by=() if pending_review_ids else ("dubbing.review",),
        prerequisite_ids=("dubbing.review",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["review_id"],
            "properties": {
                "review_id": _enum_property(pending_review_ids),
                "accepted_id": {"type": "string", "minLength": 1, "maxLength": 128},
            },
        },
        suggested_input={"review_id": pending_review_ids[0]} if pending_review_ids else {},
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="accepted_dubbing_edit",
    )

    render = WorkflowAction(
        action_id="render_accepted_dubbing",
        title="Собрать мастер с принятым дубляжом",
        explanation="Материализовать только текущие AcceptedDubbingEdit локальным deterministic renderer.",
        enabled=accepted_ready and render_ready,
        blocked_by=tuple(
            item
            for item, ready in (("dubbing.accepted", accepted_ready), ("capability.video.render_dubbing", render_ready))
            if not ready
        ),
        prerequisite_ids=("dubbing.accepted", "capability.video.render_dubbing"),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["source_id"],
            "properties": {"source_id": _enum_property(accepted_source_ids)},
        },
        suggested_input={"source_id": accepted_source_ids[0]} if accepted_source_ids else {},
        execution_class="capability",
        authorization_class="none",
        capability_id=_RENDER_CAPABILITY_ID,
        expected_result="video",
    )

    if not render_ready and not render_configurable:
        readiness = WorkflowReadiness.UNAVAILABLE
        summary = "Dubbing нельзя завершить в текущем runtime: локальный финальный рендер недоступен."
    elif not source_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Импортируйте видео, чтобы начать Dubbing."
    elif not transcript_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Добавьте проверенный текст речи: вручную или через локальный ASR с явным принятием."
    elif not take_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Подготовьте новую речь и привяжите её к текущему тексту."
    elif not loudness_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED if loudness_configurable else WorkflowReadiness.UNAVAILABLE
        summary = "Локальная аудиопроверка должна быть доступна до Review и принятия."
    elif current_outcome is not None:
        readiness = WorkflowReadiness.READY
        summary = "Текущий мастер точно соответствует принятому состоянию дубляжа."
    else:
        readiness = WorkflowReadiness.READY
        summary = "Dubbing готов к следующему проверяемому действию."

    decisions = tuple(
        {"kind": "accepted_dubbing", **item.to_dict()} for item in accepted
    )
    recent_artifacts = tuple(
        _artifact(reference) for reference in project.artifacts if reference.kind in {"audio", "video"}
    )

    return ProjectWorkflowState(
        project_id=project.project_id,
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        readiness=readiness,
        summary=summary,
        current_outcome=current_outcome,
        prerequisites=prerequisites,
        relevant_workspaces=(
            WorkflowWorkspace(
                workspace_id=DUBBING_WORKSPACE_ID,
                title="Дубляж видео",
                description="Текст → новая речь → Review → Accept → локальный мастер.",
            ),
        ),
        next_actions=(
            import_transcript,
            transcribe,
            accept_asr,
            attach_speech,
            review_speech,
            accept_review,
            render,
        ),
        active_jobs=(),
        user_decisions=decisions,
        recent_artifacts=recent_artifacts,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "DUBBING_RECIPE_ID",
    "DUBBING_WORKSPACE_ID",
    "dubbing_workflow_state",
]
