"""Intent-first creative project application service.

The service deliberately keeps the existing ProjectDocument schema stable. A
creative project's user intent lives under one namespaced extension while the
legacy/general-video recipe remains an internal execution primitive until the
older recipe model is retired.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Sequence

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.orchestration import project_workflow_state
from uv_studio.projects.models import ProjectDocument
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import (
    Stage8RecipeWorkspace,
    Stage8WorkspaceError,
    build_stage8_workspace_for_project,
    extensions_with_stage8_workspace,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.recipes import RecipeRegistry, UnknownRecipe

CREATIVE_EXTENSION_KEY = "creative_project"
CREATIVE_SCHEMA_VERSION = 1
_INTERNAL_RECIPE_ID = "general_video"
_MAX_MATERIAL_SOURCE_IDS = 200


class CreativeProjectError(RuntimeError):
    pass


def _clean_text(value: str, *, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise CreativeProjectError(f"{field_name} must be text")
    normalized = value.strip()
    if not normalized:
        raise CreativeProjectError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise CreativeProjectError(f"{field_name} is too long")
    return normalized


def _optional_text(value: str | None, *, field_name: str, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CreativeProjectError(f"{field_name} must be text")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise CreativeProjectError(f"{field_name} is too long")
    return normalized


def _material_source_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CreativeProjectError("creative project material_source_ids must be an array")
    if len(value) > _MAX_MATERIAL_SOURCE_IDS:
        raise CreativeProjectError("creative project has too many selected materials")
    if any(not isinstance(item, str) or not item for item in value):
        raise CreativeProjectError("creative project material_source_ids must contain non-empty ids")
    if len(set(value)) != len(value):
        raise CreativeProjectError("creative project material_source_ids must be unique")
    return list(value)


def _creative_extension(project: ProjectDocument) -> dict[str, Any]:
    raw = project.extensions.get(CREATIVE_EXTENSION_KEY)
    if not isinstance(raw, dict):
        raise CreativeProjectError("project is not an intent-first creative project")
    if raw.get("schema_version") != CREATIVE_SCHEMA_VERSION:
        raise CreativeProjectError("unsupported creative project extension version")
    goal = raw.get("goal")
    script = raw.get("script", "")
    if not isinstance(goal, str) or not goal.strip():
        raise CreativeProjectError("creative project goal is missing")
    if not isinstance(script, str):
        raise CreativeProjectError("creative project script must be text")
    return {
        "schema_version": CREATIVE_SCHEMA_VERSION,
        "goal": goal.strip(),
        "script": script.strip(),
        "material_source_ids": _material_source_ids(raw.get("material_source_ids", [])),
        "provider_policy": "local_free_first",
        "allow_paid_remote": False,
    }


def is_creative_project(project: ProjectDocument) -> bool:
    try:
        _creative_extension(project)
    except CreativeProjectError:
        return False
    return True


def _default_title(goal: str) -> str:
    first_line = goal.strip().splitlines()[0].strip()
    if len(first_line) <= 80:
        return first_line
    return first_line[:77].rstrip() + "..."


def _capability_route(registry: CapabilityRegistry, capability_id: str) -> dict[str, Any]:
    try:
        offers = registry.offers_for(capability_id)
    except UnknownCapability:
        return {
            "capability_id": capability_id,
            "state": "unavailable",
            "route_class": "missing",
            "reason": "Эта возможность отсутствует в текущей установке UV Studio.",
            "available_offer_count": 0,
            "configuration_required_count": 0,
            "has_local_free": False,
            "has_external": False,
            "may_cost_money": False,
        }

    available = [offer for offer in offers if offer.availability is OfferAvailability.AVAILABLE]
    configurable = [
        offer for offer in offers if offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
    ]
    local_free = [
        offer
        for offer in available
        if offer.locality is LocalityClass.LOCAL and offer.cost_class is CostClass.FREE
    ]
    external = [offer for offer in available if offer.locality is not LocalityClass.LOCAL]
    paid = [offer for offer in available if offer.cost_class is not CostClass.FREE]

    if local_free:
        best = local_free[0]
        state = "ready"
        route_class = "local_free"
        reason = best.reason
    elif available:
        best = available[0]
        state = "ready"
        route_class = "external_paid" if best.cost_class is not CostClass.FREE else "external_free"
        reason = best.reason
    elif configurable:
        best = configurable[0]
        state = "needs_connection"
        route_class = "configuration_required"
        reason = best.reason
    else:
        best = offers[0] if offers else None
        state = "unavailable"
        route_class = "unavailable"
        reason = best.reason if best is not None else "Для этой возможности пока нет исполнителя."

    return {
        "capability_id": capability_id,
        "state": state,
        "route_class": route_class,
        "reason": reason,
        "available_offer_count": len(available),
        "configuration_required_count": len(configurable),
        "has_local_free": bool(local_free),
        "has_external": bool(external),
        "may_cost_money": bool(paid),
    }


class CreativeProjectService:
    """Create, update and project the user-facing creative production journey."""

    def __init__(
        self,
        store: ProjectStore,
        registry: CapabilityRegistry,
        recipe_registry: RecipeRegistry,
    ) -> None:
        self.store = store
        self.registry = registry
        self.recipe_registry = recipe_registry

    def create(self, *, goal: str, title: str | None = None) -> ProjectDocument:
        normalized_goal = _clean_text(goal, field_name="goal", max_length=20_000)
        normalized_title = _optional_text(title, field_name="title", max_length=500)
        extension = {
            "schema_version": CREATIVE_SCHEMA_VERSION,
            "goal": normalized_goal,
            "script": "",
            "material_source_ids": [],
            "provider_policy": "local_free_first",
            "allow_paid_remote": False,
        }
        return self.store.create_project(
            title=normalized_title or _default_title(normalized_goal),
            recipe_id=_INTERNAL_RECIPE_ID,
            extensions={CREATIVE_EXTENSION_KEY: extension},
        )

    def update_intent(
        self,
        project_id: str,
        *,
        goal: str | None = None,
        script: str | None = None,
    ) -> ProjectDocument:
        project = self._load(project_id)
        current = _creative_extension(project)
        if goal is not None:
            current["goal"] = _clean_text(goal, field_name="goal", max_length=20_000)
        if script is not None:
            current["script"] = _optional_text(
                script,
                field_name="script",
                max_length=100_000,
            ) or ""
        extensions = dict(project.extensions)
        extensions[CREATIVE_EXTENSION_KEY] = current
        return self.store.update_project(project_id, extensions=extensions)

    def save_preparation(
        self,
        project_id: str,
        *,
        goal: str,
        script: str,
        source_ids: Sequence[str],
    ) -> tuple[ProjectDocument, Stage8RecipeWorkspace]:
        """Commit creative state and the bounded assembly projection in one store write."""

        project = self._load(project_id)
        current = _creative_extension(project)
        current["goal"] = _clean_text(goal, field_name="goal", max_length=20_000)
        current["script"] = _optional_text(
            script,
            field_name="script",
            max_length=100_000,
        ) or ""
        current["material_source_ids"] = _material_source_ids(list(source_ids))
        try:
            workspace = build_stage8_workspace_for_project(
                self.store,
                project,
                brief=current["goal"],
                script=current["script"],
                source_ids=current["material_source_ids"],
            )
            extensions = extensions_with_stage8_workspace(project, workspace)
            extensions[CREATIVE_EXTENSION_KEY] = current
            updated = self.store.update_project(project_id, extensions=extensions)
        except (Stage8WorkspaceError, ProjectStoreError) as exc:
            raise CreativeProjectError(str(exc)) from exc
        return updated, workspace

    def plan(self, project_id: str) -> dict[str, Any]:
        project = self._load(project_id)
        intent = _creative_extension(project)
        if project.recipe_id != _INTERNAL_RECIPE_ID:
            raise CreativeProjectError(
                "intent-first creative projects currently require the internal general-video execution path"
            )

        try:
            recipe = self.recipe_registry.get(project.recipe_id)
        except UnknownRecipe as exc:
            raise CreativeProjectError("internal execution recipe is unavailable") from exc

        workflow = project_workflow_state(
            project,
            recipe,
            self.registry,
            ProjectSourceMediaStore(self.store),
        )
        image_count = sum(source.kind == "image" for source in project.sources)
        video_count = sum(source.kind == "video" for source in project.sources)
        audio_count = sum(source.kind == "audio" for source in project.sources)
        visual_count = image_count + video_count
        selected_ids = intent["material_source_ids"]
        source_by_id = {source.id: source for source in project.sources}
        selected_sources = [source_by_id[item] for item in selected_ids if item in source_by_id]
        selected_visual_count = sum(source.kind in {"image", "video"} for source in selected_sources)
        selected_audio_count = sum(source.kind == "audio" for source in selected_sources)

        text_route = _capability_route(self.registry, "text.generate")
        image_route = _capability_route(self.registry, "image.generate")
        video_route = _capability_route(self.registry, "video.generate")
        speech_route = _capability_route(self.registry, "speech.synthesize")

        render_action = next(
            (action for action in workflow.next_actions if action.action_id == "render_general"),
            None,
        )
        outcome = workflow.current_outcome

        if outcome is not None:
            overall_state = "result_ready"
            next_step = "Просмотрите готовый ролик и решите, нужны ли правки или новый вариант."
        elif render_action is not None and render_action.enabled:
            overall_state = "ready_to_assemble"
            next_step = "Материалы готовы. Соберите первый черновой ролик."
        elif visual_count == 0:
            overall_state = "needs_materials"
            if image_route["state"] == "ready" or video_route["state"] == "ready":
                next_step = "Создайте визуальные материалы подключённым генератором или добавьте свои файлы."
            else:
                next_step = "Добавьте свои изображения/видео либо подключите генератор изображений или видео."
        elif selected_visual_count == 0:
            overall_state = "needs_selection"
            next_step = "Выберите из материалов проекта хотя бы одно изображение или видео для первого черновика."
        elif selected_audio_count > 1:
            overall_state = "needs_selection"
            next_step = "Для первого локального черновика оставьте не более одной выбранной аудиодорожки."
        else:
            overall_state = "preparing"
            next_step = "Сохраните текущий план и материалы, чтобы открыть локальную сборку."

        phases = [
            {
                "phase_id": "intent",
                "title": "Замысел",
                "state": "complete",
                "summary": intent["goal"],
                "blocking": False,
                "routes": [],
            },
            {
                "phase_id": "plan",
                "title": "Сценарий и план",
                "state": "complete" if intent["script"] else "actionable",
                "summary": (
                    "План сохранён и остаётся редактируемым."
                    if intent["script"]
                    else "Можно написать план вручную; ИИ используется только если для text.generate есть реальный исполнитель."
                ),
                "blocking": False,
                "routes": [
                    {
                        "route_id": "write_manually",
                        "title": "Написать или отредактировать вручную",
                        "state": "ready",
                        "route_class": "manual",
                        "reason": "Не требует внешнего сервиса.",
                    },
                    {
                        "route_id": "generate_text",
                        "title": "Помочь с текстом через ИИ",
                        **text_route,
                    },
                ],
            },
            {
                "phase_id": "visuals",
                "title": "Визуальные материалы",
                "state": "complete" if selected_visual_count else "actionable",
                "summary": (
                    f"Для черновика выбрано {selected_visual_count} визуальных материалов."
                    if selected_visual_count
                    else f"В библиотеке проекта {visual_count} визуальных материалов; выберите нужные или добавьте новые."
                    if visual_count
                    else "Нужны кадры: их можно импортировать или получить через подключённую генерацию."
                ),
                "blocking": selected_visual_count == 0,
                "routes": [
                    {
                        "route_id": "use_own_media",
                        "title": "Использовать свои изображения или видео",
                        "state": "ready",
                        "route_class": "local_input",
                        "reason": "Файлы копируются в Project Store и остаются частью переносимого проекта.",
                    },
                    {
                        "route_id": "generate_images",
                        "title": "Сгенерировать изображения",
                        **image_route,
                    },
                    {
                        "route_id": "generate_video",
                        "title": "Сгенерировать видео",
                        **video_route,
                    },
                ],
            },
            {
                "phase_id": "audio",
                "title": "Голос, музыка и звук",
                "state": "complete" if selected_audio_count else "optional",
                "summary": (
                    "Для черновика выбрана одна аудиодорожка."
                    if selected_audio_count == 1
                    else "Для первого локального черновика оставьте не более одной аудиодорожки."
                    if selected_audio_count > 1
                    else "Этот шаг необязателен. Можно добавить готовое аудио или подключить синтез речи."
                ),
                "blocking": selected_audio_count > 1,
                "routes": [
                    {
                        "route_id": "use_own_audio",
                        "title": "Использовать своё аудио",
                        "state": "ready",
                        "route_class": "local_input",
                        "reason": "Готовая музыка, речь или другая дорожка импортируется в проект.",
                    },
                    {
                        "route_id": "synthesize_speech",
                        "title": "Создать речь из текста",
                        **speech_route,
                    },
                ],
            },
            {
                "phase_id": "assembly",
                "title": "Черновая сборка",
                "state": (
                    "complete"
                    if outcome is not None
                    else "actionable"
                    if render_action is not None and render_action.enabled
                    else "blocked"
                ),
                "summary": (
                    "Готовый мастер зарегистрирован в Project Store."
                    if outcome is not None
                    else workflow.summary
                ),
                "blocking": outcome is None and not (render_action is not None and render_action.enabled),
                "routes": [
                    {
                        "route_id": "assemble_locally",
                        "title": "Собрать локально",
                        "state": "ready" if render_action is not None and render_action.enabled else "blocked",
                        "route_class": "local_free",
                        "reason": (
                            render_action.explanation
                            if render_action is not None
                            else "Финальная сборка пока не доступна для текущего состояния проекта."
                        ),
                    }
                ],
            },
            {
                "phase_id": "review",
                "title": "Просмотр и правки",
                "state": "actionable" if outcome is not None else "waiting",
                "summary": (
                    "Проверьте результат и меняйте замысел, план или материалы; новый render создаст новую ревизию."
                    if outcome is not None
                    else "Появится после первой сборки."
                ),
                "blocking": False,
                "routes": [],
            },
        ]

        return {
            "schema_version": CREATIVE_SCHEMA_VERSION,
            "project_id": project.project_id,
            "title": project.title,
            "goal": intent["goal"],
            "script": intent["script"],
            "material_source_ids": selected_ids,
            "provider_policy": intent["provider_policy"],
            "allow_paid_remote": intent["allow_paid_remote"],
            "overall_state": overall_state,
            "next_step": next_step,
            "source_summary": {
                "images": image_count,
                "videos": video_count,
                "audio": audio_count,
                "visuals": visual_count,
                "selected_visuals": selected_visual_count,
                "selected_audio": selected_audio_count,
            },
            "current_outcome": asdict(outcome) if outcome is not None else None,
            "phases": phases,
        }

    def _load(self, project_id: str) -> ProjectDocument:
        try:
            return self.store.load_project(project_id)
        except ProjectNotFound as exc:
            raise CreativeProjectError("project not found") from exc
        except ProjectStoreError as exc:
            raise CreativeProjectError(str(exc)) from exc
