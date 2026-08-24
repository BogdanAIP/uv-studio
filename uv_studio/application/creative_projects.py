"""Intent-first creative project application service.

The service deliberately keeps the existing ProjectDocument schema stable. A
creative project's user intent lives under one namespaced extension while the
legacy/general-video recipe remains an internal execution primitive until the
older recipe model is retired.
"""

from __future__ import annotations

from typing import Any

from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.orchestration import project_workflow_state
from uv_studio.projects.models import ProjectDocument
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.recipes import RecipeRegistry, UnknownRecipe

CREATIVE_EXTENSION_KEY = "creative_project"
CREATIVE_SCHEMA_VERSION = 1
_INTERNAL_RECIPE_ID = "general_video"


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
            next_step = "Материалы готовы. Сохраните их порядок и соберите первый черновой ролик."
        elif visual_count == 0:
            overall_state = "needs_materials"
            if image_route["state"] == "ready" or video_route["state"] == "ready":
                next_step = "Создайте визуальные материалы подключённым генератором или добавьте свои файлы."
            else:
                next_step = "Добавьте свои изображения/видео либо подключите генератор изображений или видео."
        elif not intent["script"]:
            overall_state = "planning"
            next_step = "Уточните план ролика и сохраните выбранные визуальные материалы."
        else:
            overall_state = "preparing"
            next_step = "Сохраните план и выбранные материалы, чтобы открыть финальную локальную сборку."

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
                "state": "complete" if visual_count else "actionable",
                "summary": (
                    f"В проекте {visual_count} визуальных материалов."
                    if visual_count
                    else "Нужны кадры: их можно импортировать или получить через подключённую генерацию."
                ),
                "blocking": visual_count == 0,
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
                "state": "complete" if audio_count else "optional",
                "summary": (
                    f"В проекте {audio_count} аудиоматериалов."
                    if audio_count
                    else "Этот шаг необязателен для первого черновика. Можно добавить готовое аудио или подключить синтез речи."
                ),
                "blocking": False,
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
            "provider_policy": intent["provider_policy"],
            "allow_paid_remote": intent["allow_paid_remote"],
            "overall_state": overall_state,
            "next_step": next_step,
            "source_summary": {
                "images": image_count,
                "videos": video_count,
                "audio": audio_count,
                "visuals": visual_count,
            },
            "current_outcome": outcome.to_dict() if outcome is not None else None,
            "phases": phases,
        }

    def _load(self, project_id: str) -> ProjectDocument:
        try:
            return self.store.load_project(project_id)
        except ProjectNotFound as exc:
            raise CreativeProjectError("project not found") from exc
        except ProjectStoreError as exc:
            raise CreativeProjectError(str(exc)) from exc
