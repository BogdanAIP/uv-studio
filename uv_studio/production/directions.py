"""Production directions above the shared UV Studio core.

A ProductionDirection describes how a project is organized for a distinct
creative/production journey. It is deliberately not an execution pipeline:
all directions share Project Store, Studio shell, timeline, tools, models,
jobs and command authority.
"""

from __future__ import annotations

from dataclasses import dataclass


class ProductionDirectionNotFound(LookupError):
    pass


@dataclass(frozen=True)
class ProductionDirection:
    direction_id: str
    title: str
    description: str
    primary_input_label: str
    workspace_sections: tuple[str, ...]
    default_tools: tuple[str, ...] = ()
    featured: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "direction_id": self.direction_id,
            "title": self.title,
            "description": self.description,
            "primary_input_label": self.primary_input_label,
            "workspace_sections": list(self.workspace_sections),
            "default_tools": list(self.default_tools),
            "featured": self.featured,
        }


MICRO_DRAMA = ProductionDirection(
    direction_id="micro_drama",
    title="Микродрама / сюжетное видео",
    description=(
        "Сценически организованное производство: история, персонажи, локации, сцены, "
        "шоты, варианты дублей и continuity поверх общего Studio Core."
    ),
    primary_input_label="О чём история?",
    workspace_sections=("story", "characters", "locations", "scenes", "shots", "assets"),
    default_tools=("continuity", "image_ai", "video_ai", "dubbing"),
)

COMMERCIAL = ProductionDirection(
    direction_id="commercial",
    title="Реклама / продукт",
    description=(
        "Производство рекламного ролика от brief и продукта до концепций, product shots, "
        "вариантов креатива и финальных форматов."
    ),
    primary_input_label="Что рекламируем и какой результат нужен?",
    workspace_sections=("brief", "product", "brand", "audience", "concepts", "shots", "assets"),
    default_tools=("image_ai", "video_ai", "voice", "review"),
)

MUSIC_VIDEO = ProductionDirection(
    direction_id="music_video",
    title="Музыкальный клип",
    description=(
        "Музыкально-ориентированное производство с Music Map, визуальной режиссурой, "
        "шотами и монтажом по структуре и ритму песни."
    ),
    primary_input_label="Песня или музыкальный фрагмент",
    workspace_sections=("song", "music_map", "sections", "visual_direction", "shots", "assets"),
    default_tools=("music_analysis", "image_ai", "video_ai", "timeline_sync"),
)

NARRATED_VIDEO = ProductionDirection(
    direction_id="narrated_video",
    title="Видео с диктором",
    description=(
        "Ролик, где текст и речь задают смысловую структуру: сценарий, голос, сегменты, "
        "визуальный план, субтитры и сборка."
    ),
    primary_input_label="Тема или текст ролика",
    workspace_sections=("brief", "script", "voice", "segments", "visual_plan", "assets"),
    default_tools=("speech", "subtitles", "image_ai", "video_ai"),
)

DUB_BATTLE = ProductionDirection(
    direction_id="dub_battle",
    title="Киноозвучка / Кинобатл",
    description=(
        "Сценическая переозвучка: исходная сцена, персонажи, реплики, распределение ролей, "
        "запись дублей и финальное сведение с фоном."
    ),
    primary_input_label="Видео или сцена для переозвучки",
    workspace_sections=("source_scene", "characters", "dialogue", "cast", "takes", "mix"),
    default_tools=("speech_separation", "transcription", "recording", "audio_mix"),
)

FREE_PROJECT = ProductionDirection(
    direction_id="free_project",
    title="Свободный проект",
    description=(
        "Универсальная Studio без обязательной производственной схемы: медиа, инструменты, "
        "таймлайн и агент подключаются только по необходимости."
    ),
    primary_input_label="Начните с любого материала или задачи",
    workspace_sections=("media", "assets", "timeline"),
    default_tools=(),
)


BUILTIN_PRODUCTION_DIRECTIONS = (
    MICRO_DRAMA,
    COMMERCIAL,
    MUSIC_VIDEO,
    NARRATED_VIDEO,
    DUB_BATTLE,
    FREE_PROJECT,
)

_DIRECTION_BY_ID = {direction.direction_id: direction for direction in BUILTIN_PRODUCTION_DIRECTIONS}


def list_production_directions() -> tuple[ProductionDirection, ...]:
    return BUILTIN_PRODUCTION_DIRECTIONS


def get_production_direction(direction_id: str) -> ProductionDirection:
    try:
        return _DIRECTION_BY_ID[direction_id]
    except KeyError as exc:
        raise ProductionDirectionNotFound(f"unknown production direction: {direction_id!r}") from exc
