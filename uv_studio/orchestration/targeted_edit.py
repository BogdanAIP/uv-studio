"""Targeted existing-video Product Orchestrator projection.

This module is read-only. It projects current Project Store/editor domain state
into user-facing prerequisites and semantic next actions without becoming a
second workflow authority.
"""

from __future__ import annotations

from typing import Iterable

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.continuity_brief import ContinuityBriefError, RangeContinuityBriefStore
from uv_studio.projects.edit_state import EditStateError, RangeEditStateStore
from uv_studio.projects.models import ProjectDocument, ProjectReference
from uv_studio.projects.replacement_candidate import (
    ReplacementCandidateError,
    ReplacementCandidateStore,
)
from uv_studio.projects.replacement_plan import ReplacementPlanError, ReplacementPlanStore
from uv_studio.projects.replacement_review import ReplacementReviewError, ReplacementReviewStore
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

TARGETED_EDIT_RECIPE_ID = "free_project"
TARGETED_EDIT_WORKSPACE_ID = "targeted_edit"
_RENDER_CAPABILITY_ID = "video.render_edits"


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
    payload: dict[str, object] = {"type": "string", "minLength": 1, "maxLength": 512}
    if values:
        payload["enum"] = values
    return payload


def targeted_edit_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project the existing targeted-edit domains for the neutral Free Project recipe."""

    store = source_media.project_store
    diagnostics: list[WorkflowDiagnostic] = []

    video_sources = tuple(source for source in project.sources if source.kind == "video")
    verified_videos: list[ProjectReference] = []
    invalid_video_ids: list[str] = []
    for source in video_sources:
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
                code="source_media_unverified",
                severity="warning" if verified_videos else "error",
                message=(
                    "Видео исключены из точечного редактирования, потому что их project-owned "
                    "bytes отсутствуют или изменились: " + ", ".join(invalid_video_ids)
                ),
            )
        )

    try:
        briefs = RangeContinuityBriefStore(store).validate_project(project.project_id).briefs
    except (ContinuityBriefError, ProjectStoreError) as exc:
        briefs = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_brief_invalid",
                severity="warning",
                message=f"Сохранённые задачи изменения не прошли текущую проверку: {exc}",
            )
        )

    try:
        ReplacementPlanStore(store).validate_project(project.project_id)
    except (ReplacementPlanError, ProjectStoreError) as exc:
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_plan_invalid",
                severity="warning",
                message=f"Сохранённые планы замены устарели или повреждены: {exc}",
            )
        )

    candidate_store = ReplacementCandidateStore(store)
    try:
        candidate_state = candidate_store.load(project.project_id)
    except (ReplacementCandidateError, ProjectStoreError) as exc:
        candidate_state = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_candidate_state_invalid",
                severity="warning",
                message=f"Состояние вариантов замены не удалось проверить: {exc}",
            )
        )
    current_candidates = []
    if candidate_state is not None:
        for candidate in candidate_state.candidates:
            if candidate.stage != "full":
                continue
            try:
                current_candidates.append(
                    candidate_store.validate_candidate(project.project_id, candidate.candidate_id)
                )
            except ReplacementCandidateError:
                continue

    review_store = ReplacementReviewStore(store)
    try:
        review_state = review_store.load(project.project_id)
    except (ReplacementReviewError, ProjectStoreError) as exc:
        review_state = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_review_state_invalid",
                severity="warning",
                message=f"Историю проверки вариантов замены не удалось прочитать: {exc}",
            )
        )
    current_reviews = []
    if review_state is not None:
        for review in review_state.reviews:
            try:
                current_reviews.append(
                    review_store.validate_review(project.project_id, review.review_id)
                )
            except ReplacementReviewError:
                continue
    approved_reviews = tuple(review for review in current_reviews if review.verdict == "approved")

    try:
        accepted_edits = RangeEditStateStore(store).load(project.project_id).edits
    except (EditStateError, ProjectStoreError) as exc:
        accepted_edits = ()
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_accepted_state_invalid",
                severity="error",
                message=f"Принятое состояние правок не удалось прочитать: {exc}",
            )
        )

    source_ready = bool(verified_videos)
    brief_ready = bool(briefs)
    eligible_replacement_pairs: list[dict[str, str]] = []
    path_by_source_id = {source.id: source.path for source in verified_videos}
    for brief in briefs:
        for source_id, source_path in path_by_source_id.items():
            if source_path != brief.source_path:
                eligible_replacement_pairs.append(
                    {"edit_id": brief.edit_id, "replacement_source_id": source_id}
                )
    replacement_source_ready = bool(eligible_replacement_pairs)

    candidate_ready = bool(current_candidates)
    review_ready = bool(approved_reviews)
    accepted_ready = bool(accepted_edits)

    render_capability_ready = False
    render_capability_configurable = False
    try:
        select_offer(
            registry,
            _RENDER_CAPABILITY_ID,
            policy=SelectionPolicy.LOCAL_FREE_FIRST,
        )
        render_capability_ready = True
    except UnknownCapability:
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_render_capability_unknown",
                severity="error",
                message="Локальный capability финальной сборки правок отсутствует в runtime.",
            )
        )
    except NoEligibleOffer:
        render_capability_configurable = any(
            offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
            and offer.cost_class is CostClass.FREE
            and offer.locality is LocalityClass.LOCAL
            for offer in registry.offers_for(_RENDER_CAPABILITY_ID)
        )
        diagnostics.append(
            WorkflowDiagnostic(
                code="targeted_edit_render_capability_unavailable",
                severity="warning" if render_capability_configurable else "error",
                message=(
                    "Локальная финальная сборка требует настройки runtime."
                    if render_capability_configurable
                    else "Нет доступного local/free исполнителя для финальной сборки правок."
                ),
            )
        )

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="source.video",
            title="Исходное видео",
            explanation="Нужно хотя бы одно проверенное project-owned видео для редактирования.",
            satisfied=source_ready,
            resolution=None if source_ready else "Импортируйте исходное видео в рабочее пространство.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="edit.brief",
            title="Фрагмент и задача",
            explanation="Выберите точный диапазон и опишите, что должно измениться.",
            satisfied=brief_ready,
            resolution=None if brief_ready else "Выберите фрагмент на timeline и опишите изменение.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="source.replacement_video",
            title="Материал для замены",
            explanation="Для полностью локального пути нужен второй проверенный видеоклип.",
            satisfied=replacement_source_ready,
            resolution=(
                None
                if replacement_source_ready
                else "Импортируйте отдельный видеоклип, который заменит выбранный фрагмент."
            ),
        ),
        WorkflowPrerequisite(
            prerequisite_id="edit.candidate",
            title="Вариант замены",
            explanation="Подготовьте проверяемый full candidate из утверждённого плана.",
            satisfied=candidate_ready,
            resolution=None if candidate_ready else "Подготовьте вариант замены из выбранного клипа.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="edit.review",
            title="Проверка результата",
            explanation="Кандидат должен пройти evidence-based Review до принятия в timeline.",
            satisfied=review_ready,
            resolution=None if review_ready else "Проверьте вариант по критериям текущей задачи.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="edit.accepted",
            title="Принятая правка",
            explanation="Финальный рендер материализует только явно принятые правки.",
            satisfied=accepted_ready,
            resolution=None if accepted_ready else "Примите одобренный результат в timeline.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.video.render_edits",
            title="Локальная финальная сборка",
            explanation="Мастер собирается существующим local/free `video.render_edits` capability.",
            satisfied=render_capability_ready,
            resolution=(
                None
                if render_capability_ready
                else (
                    "Завершите настройку локального media runtime."
                    if render_capability_configurable
                    else "Установите обязательный локальный media runtime и перезапустите UV Studio."
                )
            ),
        ),
    )

    verified_source_ids = tuple(source.id for source in verified_videos)
    brief_ids = tuple(brief.edit_id for brief in briefs)
    candidate_ids = tuple(candidate.candidate_id for candidate in current_candidates)
    approved_review_ids = tuple(review.review_id for review in approved_reviews)
    accepted_source_paths = tuple(dict.fromkeys(edit.source_path for edit in accepted_edits))

    select_action = WorkflowAction(
        action_id="select_target_range",
        title="Выбрать фрагмент и описать изменение",
        explanation="Зафиксировать точный диапазон и создать каноническую задачу изменения.",
        enabled=source_ready,
        blocked_by=() if source_ready else ("source.video",),
        prerequisite_ids=("source.video",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["source_id", "start_us", "end_us", "change_request"],
            "properties": {
                "source_id": _enum_property(verified_source_ids),
                "start_us": {"type": "integer", "minimum": 0},
                "end_us": {"type": "integer", "minimum": 1},
                "change_request": {"type": "string", "minLength": 1, "maxLength": 4000},
                "context_before_us": {"type": "integer", "minimum": 0, "maximum": 30_000_000, "default": 5_000_000},
                "context_after_us": {"type": "integer", "minimum": 0, "maximum": 30_000_000, "default": 5_000_000},
            },
        },
        suggested_input={"source_id": verified_source_ids[0]} if verified_source_ids else {},
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="targeted_edit_brief",
    )

    prepare_blocked = tuple(
        prerequisite
        for prerequisite, ready in (
            ("edit.brief", brief_ready),
            ("source.replacement_video", replacement_source_ready),
        )
        if not ready
    )
    prepare_action = WorkflowAction(
        action_id="prepare_replacement",
        title="Подготовить вариант замены",
        explanation=(
            "Утвердить локальный prepared-asset план для выбранной задачи и создать отдельный "
            "full candidate, не меняя timeline."
        ),
        enabled=not prepare_blocked,
        blocked_by=prepare_blocked,
        prerequisite_ids=("edit.brief", "source.replacement_video"),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["edit_id", "replacement_source_id"],
            "properties": {
                "edit_id": _enum_property(brief_ids),
                "replacement_source_id": _enum_property(verified_source_ids),
            },
            "x-allowed-pairs": tuple(eligible_replacement_pairs),
        },
        suggested_input=dict(eligible_replacement_pairs[0]) if eligible_replacement_pairs else {},
        execution_class="domain_operation",
        authorization_class="none",
        capability_id=None,
        expected_result="replacement_candidate",
    )

    review_action = WorkflowAction(
        action_id="review_replacement",
        title="Проверить вариант замены",
        explanation="Зафиксировать evidence-based оценку текущего full candidate по ReviewTarget задачи.",
        enabled=candidate_ready,
        blocked_by=() if candidate_ready else ("edit.candidate",),
        prerequisite_ids=("edit.candidate",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["candidate_id", "verdict", "observations", "assessments"],
            "properties": {
                "candidate_id": _enum_property(candidate_ids),
                "verdict": {"type": "string", "enum": ["approved", "rejected", "needs_revision"]},
                "observations": {"type": "array", "minItems": 1},
                "assessments": {"type": "array", "minItems": 1},
            },
        },
        suggested_input={"candidate_id": candidate_ids[0]} if candidate_ids else {},
        execution_class="domain_operation",
        authorization_class="none",
        capability_id=None,
        expected_result="replacement_review",
    )

    accept_action = WorkflowAction(
        action_id="accept_replacement",
        title="Принять проверенную замену",
        explanation="Принять только одобренный и актуальный Review в non-destructive timeline state.",
        enabled=review_ready,
        blocked_by=() if review_ready else ("edit.review",),
        prerequisite_ids=("edit.review",),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["review_id"],
            "properties": {"review_id": _enum_property(approved_review_ids)},
        },
        suggested_input={"review_id": approved_review_ids[0]} if approved_review_ids else {},
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="accepted_range_edit",
    )

    render_blocked = tuple(
        prerequisite
        for prerequisite, ready in (
            ("edit.accepted", accepted_ready),
            ("capability.video.render_edits", render_capability_ready),
        )
        if not ready
    )
    render_action = WorkflowAction(
        action_id="render_accepted_edits",
        title="Собрать мастер с принятыми правками",
        explanation="Одним локальным проходом материализовать текущий Accepted state выбранного исходника.",
        enabled=not render_blocked,
        blocked_by=render_blocked,
        prerequisite_ids=("edit.accepted", "capability.video.render_edits"),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["source_path"],
            "properties": {"source_path": _enum_property(accepted_source_paths)},
        },
        suggested_input={"source_path": accepted_source_paths[0]} if accepted_source_paths else {},
        execution_class="local_deterministic",
        authorization_class="d017_exact_one_shot_if_required",
        capability_id=_RENDER_CAPABILITY_ID,
        expected_result="video_artifact",
    )

    render_artifacts = tuple(
        _artifact(reference)
        for reference in reversed(project.artifacts)
        if reference.kind == "video" and reference.metadata.get("lifecycle") == "render"
    )

    if not source_ready:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Импортируйте исходное видео, чтобы начать точечное редактирование."
    else:
        readiness = WorkflowReadiness.READY
        if accepted_ready:
            summary = "Принятые правки готовы к локальной финальной сборке."
        elif review_ready:
            summary = "Проверенный вариант готов к принятию в timeline."
        elif candidate_ready:
            summary = "Вариант замены готов к проверке."
        elif brief_ready:
            summary = "Задача изменения сохранена; подготовьте материал замены."
        else:
            summary = "Исходное видео готово. Выберите фрагмент и опишите изменение."

    return ProjectWorkflowState(
        project_id=project.project_id,
        recipe_id=project.recipe_id,
        recipe_title=recipe.title,
        readiness=readiness,
        summary=summary,
        current_outcome=render_artifacts[0] if render_artifacts else None,
        prerequisites=prerequisites,
        relevant_workspaces=(
            WorkflowWorkspace(
                workspace_id=TARGETED_EDIT_WORKSPACE_ID,
                title="Точечное редактирование видео",
                description="Исходник, диапазон, вариант замены, проверка и финальная сборка.",
            ),
        ),
        next_actions=(select_action, prepare_action, review_action, accept_action, render_action),
        active_jobs=(),
        user_decisions=tuple(
            {
                "kind": "accepted_range_edit",
                "edit_id": edit.edit_id,
                "source_path": edit.source_path,
                "start_us": edit.start_us,
                "end_us": edit.end_us,
            }
            for edit in accepted_edits
        ),
        recent_artifacts=render_artifacts[:10],
        diagnostics=tuple(diagnostics),
    )
