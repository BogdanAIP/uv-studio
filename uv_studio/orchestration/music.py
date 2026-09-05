"""Read-only Product Orchestrator projection for the permanent Music Video journey."""

from __future__ import annotations

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import NoEligibleOffer, SelectionPolicy, select_offer
from uv_studio.projects.media_integrity import MediaIntegrityError, verify_registered_media_bytes
from uv_studio.projects.models import ProjectDocument, ProjectReference
from uv_studio.projects.music_assembly import MusicAssemblyError, MusicAssemblyStore
from uv_studio.projects.music_direction import MusicDirectionError, MusicDirectionStore
from uv_studio.projects.music_map import MusicMapError, MusicMapStore
from uv_studio.projects.music_video_review import MusicVideoReviewError, MusicVideoReviewStore
from uv_studio.projects.source_media import (
    ProjectSourceMediaStore,
    SourceMediaError,
    SourceMediaNotFound,
)
from uv_studio.projects.store import ProjectStoreError
from uv_studio.recipes.models import RecipeDefinition

from .models import (
    ProjectWorkflowState,
    WorkflowArtifact,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
    WorkflowWorkspace,
)

MUSIC_RECIPE_ID = "music_video"
MUSIC_WORKSPACE_ID = "music_video"
_RENDER_CAPABILITY_ID = "video.render_music_video"
_RENDER_LIFECYCLE = "music_video_render"
_RENDER_COMPOSITION_MODE = "music_assembly_visual_concat_with_exact_master_song_excerpt"


def _artifact(reference: ProjectReference) -> WorkflowArtifact:
    return WorkflowArtifact(
        artifact_id=reference.id,
        kind=reference.kind,
        path=reference.path,
        lifecycle=str(reference.metadata.get("lifecycle", "")),
        metadata=dict(reference.metadata),
    )


def _local_free_status(
    registry: CapabilityRegistry,
    capability_id: str,
) -> tuple[bool, bool, str | None]:
    try:
        decision = select_offer(registry, capability_id, policy=SelectionPolicy.LOCAL_FREE_FIRST)
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


def _verified_sources(
    project: ProjectDocument,
    source_media: ProjectSourceMediaStore,
    *,
    kind: str,
) -> tuple[tuple[ProjectReference, ...], tuple[str, ...]]:
    verified: list[ProjectReference] = []
    invalid: list[str] = []
    for source in project.sources:
        if source.kind != kind:
            continue
        try:
            reference, _path = source_media.resolve_verified(
                project.project_id,
                source.id,
                expected_kind=kind,
            )
        except (SourceMediaError, SourceMediaNotFound, ProjectStoreError):
            invalid.append(source.id)
            continue
        verified.append(reference)
    return tuple(verified), tuple(invalid)


def _current_render_artifacts(
    project: ProjectDocument,
    music_map,
    direction,
    assembly,
) -> tuple[ProjectReference, ...]:
    if music_map is None or direction is None or assembly is None:
        return ()
    valid: list[ProjectReference] = []
    for reference in project.artifacts:
        if reference.kind != "video" or reference.metadata.get("lifecycle") != _RENDER_LIFECYCLE:
            continue
        metadata = reference.metadata
        if (
            metadata.get("capability_id") != _RENDER_CAPABILITY_ID
            or metadata.get("composition_mode") != _RENDER_COMPOSITION_MODE
            or metadata.get("music_map_revision_sha256") != music_map.revision_sha256
            or metadata.get("music_direction_revision_sha256") != direction.revision_sha256
            or metadata.get("music_assembly_revision_sha256") != assembly.revision_sha256
            or metadata.get("song_reference_id") != music_map.song.reference_id
            or metadata.get("song_sha256") != music_map.song.sha256
            or metadata.get("song_excerpt") != music_map.excerpt.to_dict()
            or metadata.get("visual_bindings") != [item.to_dict() for item in assembly.bindings]
        ):
            continue
        valid.append(reference)
    return tuple(valid)


def _verified_current_renders(
    project: ProjectDocument,
    project_store,
    music_map,
    direction,
    assembly,
    *,
    diagnostics: list[WorkflowDiagnostic],
) -> tuple[ProjectReference, ...]:
    candidates = _current_render_artifacts(
        project,
        music_map,
        direction,
        assembly,
    )
    valid: list[ProjectReference] = []
    invalid: list[str] = []
    for reference in candidates:
        try:
            path = project_store.resolve_project_file(
                project.project_id,
                reference.path,
                must_exist=True,
                allowed_roots=("artifacts",),
            )
            verify_registered_media_bytes(path, reference.metadata)
        except (MediaIntegrityError, ProjectStoreError, OSError):
            invalid.append(reference.id)
            continue
        valid.append(reference)
    if invalid:
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_render_unverified",
                severity="warning" if valid else "error",
                message=(
                    "Music render исключён из Review, потому что текущие bytes не прошли проверку: "
                    + ", ".join(invalid)
                ),
            )
        )
    return tuple(valid)


def music_workflow_state(
    project: ProjectDocument,
    recipe: RecipeDefinition,
    registry: CapabilityRegistry,
    source_media: ProjectSourceMediaStore,
) -> ProjectWorkflowState:
    """Project the canonical Music Video chain without owning durable workflow state."""

    store = source_media.project_store
    diagnostics: list[WorkflowDiagnostic] = []

    verified_audio, invalid_audio = _verified_sources(project, source_media, kind="audio")
    verified_video, invalid_video = _verified_sources(project, source_media, kind="video")
    if invalid_audio:
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_audio_source_unverified",
                severity="warning" if verified_audio else "error",
                message=(
                    "Аудио исключено из Music Map, потому что project-owned bytes отсутствуют или изменились: "
                    + ", ".join(invalid_audio)
                ),
            )
        )
    if invalid_video:
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_video_source_unverified",
                severity="warning" if verified_video else "error",
                message=(
                    "Видео исключено из Music Assembly, потому что project-owned bytes отсутствуют или изменились: "
                    + ", ".join(invalid_video)
                ),
            )
        )

    map_store = MusicMapStore(store)
    direction_store = MusicDirectionStore(store)
    assembly_store = MusicAssemblyStore(store)
    review_store = MusicVideoReviewStore(store)

    try:
        music_map = map_store.load(project.project_id, validate_current=True)
    except (MusicMapError, ProjectStoreError) as exc:
        music_map = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_map_invalid",
                severity="error",
                message=f"Music Map не является текущим: {exc}",
            )
        )

    try:
        direction = direction_store.load(project.project_id, validate_current=True)
    except (MusicMapError, MusicDirectionError, ProjectStoreError) as exc:
        direction = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_direction_invalid",
                severity="warning" if music_map is not None else "error",
                message=f"Music Director не является текущим: {exc}",
            )
        )

    try:
        assembly = assembly_store.load(project.project_id, validate_current=True)
    except (MusicMapError, MusicDirectionError, MusicAssemblyError, SourceMediaError, ProjectStoreError) as exc:
        assembly = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_assembly_invalid",
                severity="warning" if direction is not None else "error",
                message=f"Music Assembly не является текущим: {exc}",
            )
        )

    rhythm_audit = None
    if direction is not None:
        try:
            rhythm_audit = direction_store.rhythm_audit(project.project_id)
        except (MusicMapError, MusicDirectionError, ProjectStoreError) as exc:
            diagnostics.append(
                WorkflowDiagnostic(
                    code="music_rhythm_audit_invalid",
                    severity="error",
                    message=f"Rhythm audit не удалось вычислить из текущего плана: {exc}",
                )
            )
    rhythm_aligned = bool(
        rhythm_audit is not None and rhythm_audit.get("summary", {}).get("all_aligned") is True
    )
    if rhythm_audit is not None and not rhythm_aligned:
        summary = rhythm_audit.get("summary", {})
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_rhythm_alignment_failed",
                severity="warning",
                message=(
                    "Rhythm audit требует правки: "
                    f"aligned={summary.get('aligned_count', 0)}, "
                    f"unaligned={summary.get('unaligned_count', 0)}."
                ),
            )
        )

    render_ready, render_configurable, render_reason = _local_free_status(
        registry, _RENDER_CAPABILITY_ID
    )
    if not render_ready:
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_render_runtime_unavailable",
                severity="warning" if render_configurable else "error",
                message=(
                    "Локальный Music render требует настройки FFmpeg runtime."
                    if render_configurable
                    else f"Локальный Music render недоступен: {render_reason}"
                ),
            )
        )

    current_renders = _verified_current_renders(
        project,
        store,
        music_map,
        direction,
        assembly,
        diagnostics=diagnostics,
    )

    try:
        review = review_store.load(project.project_id, validate_current=True)
    except (MusicMapError, MusicDirectionError, MusicAssemblyError, MusicVideoReviewError, ProjectStoreError) as exc:
        review = None
        diagnostics.append(
            WorkflowDiagnostic(
                code="music_review_invalid",
                severity="warning",
                message=f"Предыдущий Music Review больше не является текущим: {exc}",
            )
        )

    approved = review is not None and review.verdict == "approved"
    current_outcome = None
    if approved:
        match = next((item for item in current_renders if item.id == review.artifact_id), None)
        if match is not None:
            current_outcome = _artifact(match)

    prerequisites = (
        WorkflowPrerequisite(
            prerequisite_id="source.audio",
            title="Master-песня",
            explanation="Нужен проверенный project-owned audio source с длительностью и SHA256.",
            satisfied=bool(verified_audio),
            resolution=None if verified_audio else "Загрузите master-песню в проект.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="music.map",
            title="Music Map",
            explanation="Рабочий excerpt, секции и ритмические маркеры должны быть привязаны к точным байтам песни.",
            satisfied=music_map is not None,
            resolution=None if music_map is not None else "Сохраните Music Map для выбранной master-песни.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="music.direction",
            title="Music Director",
            explanation="План кадров должен соответствовать точной текущей ревизии Music Map.",
            satisfied=direction is not None,
            resolution=None if direction is not None else "Сохраните план кадров для текущего Music Map.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="source.video",
            title="Видео для кадров",
            explanation="Каждый кадр Assembly использует только проверенное project-owned видео.",
            satisfied=bool(verified_video),
            resolution=None if verified_video else "Загрузите хотя бы один видеоисточник.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="music.assembly",
            title="Music Assembly",
            explanation="Все кадры текущего Music Director должны быть привязаны к проверенным видеоисточникам.",
            satisfied=assembly is not None,
            resolution=None if assembly is not None else "Сохраните Assembly Plan для текущего Music Director.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="music.rhythm_aligned",
            title="Rhythm audit",
            explanation="Детерминированная проверка должна подтвердить привязку монтажных склеек к текущим маркерам/границам.",
            satisfied=rhythm_aligned,
            resolution=None if rhythm_aligned else "Исправьте границы кадров или sync markers до прохождения rhythm audit.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="capability.video.render_music_video",
            title="Локальный Music render",
            explanation="Финальный мастер собирается существующим local/free video.render_music_video capability.",
            satisfied=render_ready,
            resolution=None if render_ready else "Настройте локальные FFmpeg/FFprobe инструменты.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="music.render",
            title="Текущий master-render",
            explanation="Review принимает только проверенный render, совпадающий с текущими Map/Direction/Assembly и master-song bytes.",
            satisfied=bool(current_renders),
            resolution=None if current_renders else "Соберите текущий master-render после прохождения rhythm audit.",
        ),
        WorkflowPrerequisite(
            prerequisite_id="music.review",
            title="Одобренный финальный Review",
            explanation="Approval должен быть evidence-bound к текущему рендеру и пройти duration/rhythm/master/assembly/render checks.",
            satisfied=approved and current_outcome is not None,
            resolution=None if approved and current_outcome is not None else "Проверьте текущий рендер и явно сохраните финальный Review.",
        ),
    )

    if current_outcome is not None:
        readiness = WorkflowReadiness.READY
        summary = "Текущий Music Video master подтверждён evidence-bound Review и соответствует каноническому состоянию проекта."
    elif assembly is not None and not render_ready and not render_configurable:
        readiness = WorkflowReadiness.UNAVAILABLE
        summary = "Music Video нельзя завершить в текущем runtime: local/free финальный render недоступен."
    elif not verified_audio:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Загрузите master-песню, чтобы начать Music Video journey."
    elif music_map is None:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Master-песня готова. Сохраните Music Map для выбранного excerpt."
    elif direction is None:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Music Map готов. Сохраните Music Director для этой точной ревизии."
    elif not verified_video:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Music Director готов. Загрузите видео для кадров Assembly."
    elif assembly is None:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Сохраните Music Assembly для текущего режиссёрского плана."
    elif not rhythm_aligned:
        readiness = WorkflowReadiness.SETUP_REQUIRED
        summary = "Assembly готов, но rhythm audit требует исправить синхронизацию склеек."
    elif not current_renders:
        readiness = WorkflowReadiness.READY
        summary = "Каноническое состояние готово к local/free master-render."
    else:
        readiness = WorkflowReadiness.READY
        summary = "Текущий master-render готов к evidence-bound финальному Review."

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
                workspace_id=MUSIC_WORKSPACE_ID,
                title="Music Video",
                description="Music Map → Director → Assembly → Rhythm Audit → Review → master-render.",
            ),
        ),
        next_actions=(),
        active_jobs=(),
        user_decisions=(
            ({"kind": "music_video_review", **review.to_dict()},) if review is not None else ()
        ),
        recent_artifacts=tuple(_artifact(item) for item in current_renders),
        diagnostics=tuple(diagnostics),
    )
