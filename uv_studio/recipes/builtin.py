"""Initial provider-neutral recipes and temporary VideoClaw pipeline bindings."""

from __future__ import annotations

from .models import PolicyMode, ProductionPolicy, RecipeDefinition, RecipeStep, RecipeUIHints
from .registry import RecipeRegistry

GENERAL_VIDEO = RecipeDefinition(
    recipe_id="general_video",
    title="Обычный видеоролик",
    description="Создание ролика из идеи или brief без обязательной песни, диктора, персонажей или continuity.",
    required_inputs=("brief",),
    optional_inputs=("script", "image", "video", "audio"),
    required_capabilities=("video.generate", "timeline.assemble"),
    optional_capabilities=("image.generate", "audio.mix", "media.understand"),
    steps=(
        RecipeStep("visual_plan", "Визуальный план", "Определить содержание и структуру ролика."),
        RecipeStep("shots", "Кадры", "Подготовить только необходимый набор кадров и длительности."),
        RecipeStep("generate", "Создание видео", "Получить необходимые видеоматериалы.", "video.generate"),
        RecipeStep("assemble", "Сборка", "Собрать выбранные материалы в итоговую последовательность.", "timeline.assemble"),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.OPTIONAL,
        direction_gate=PolicyMode.OPTIONAL,
        sample_first=PolicyMode.OPTIONAL,
        final_review=PolicyMode.OPTIONAL,
    ),
    ui=RecipeUIHints(
        category="create",
        primary_input_label="Что нужно показать в ролике?",
        visible_sections=("brief", "format"),
        advanced_sections=("style", "providers"),
        featured=True,
    ),
)

NARRATED_VIDEO = RecipeDefinition(
    recipe_id="narrated_video",
    title="Видео с диктором",
    description="Информационный или объясняющий ролик, где речь задаёт структуру визуального ряда.",
    required_inputs=("brief",),
    optional_inputs=("script", "voice", "image", "video"),
    required_capabilities=("speech.synthesize", "timeline.assemble"),
    optional_capabilities=("image.generate", "video.generate", "subtitle.render", "media.understand"),
    steps=(
        RecipeStep("script", "Текст", "Подготовить или разбить готовый дикторский текст."),
        RecipeStep("voice", "Речь", "Получить или использовать выбранную речевую дорожку.", "speech.synthesize"),
        RecipeStep("visual_plan", "Визуальный план", "Подобрать визуалы под смысловые фрагменты речи."),
        RecipeStep("visuals", "Визуалы", "Создать недостающие изображения или видео.", "video.generate", optional=True),
        RecipeStep("assemble", "Сборка", "Свести речь, визуалы и тайминг.", "timeline.assemble"),
    ),
    production_policy=ProductionPolicy(
        direction_gate=PolicyMode.OPTIONAL,
        sample_first=PolicyMode.OPTIONAL,
        plan_gate=PolicyMode.OPTIONAL,
        final_review=PolicyMode.OPTIONAL,
    ),
    ui=RecipeUIHints(
        category="create",
        primary_input_label="Тема или текст ролика",
        visible_sections=("brief", "voice"),
        advanced_sections=("visual_style", "subtitles", "providers"),
        featured=True,
    ),
)

MUSIC_VIDEO = RecipeDefinition(
    recipe_id="music_video",
    title="Музыкальный клип",
    description=(
        "Музыкально-ориентированный монтаж, где выбранная песня и Music Map задают "
        "тайминг, структуру и точки проверки, не становясь универсальным режимом редактора."
    ),
    required_inputs=("song",),
    optional_inputs=("brief", "lyrics", "image", "video", "style"),
    required_capabilities=("timeline.assemble",),
    optional_capabilities=("video.generate", "image.generate", "audio.mix", "media.understand"),
    steps=(
        RecipeStep(
            "music_map",
            "Карта музыки",
            "Зафиксировать excerpt, структуру, ритмические маркеры и вокальные фразы.",
        ),
        RecipeStep(
            "music_direction",
            "Музыкальная режиссура",
            "Связать смысловые и ритмические участки с планом кадров без выбора конкретного провайдера.",
        ),
        RecipeStep(
            "sample_assets",
            "Пробные материалы",
            "Проверить короткие подготовленные или сгенерированные материалы до полной сборки.",
            "video.generate",
            optional=True,
        ),
        RecipeStep(
            "assemble",
            "Музыкальная сборка",
            "Собрать утверждённые визуальные материалы по Music Map с сохранением master-аудио.",
            "timeline.assemble",
        ),
        RecipeStep(
            "rhythm_review",
            "Проверка ритма",
            "Проверить монтажные границы, музыкальные акценты и переходы по измеримым временным данным.",
        ),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.REQUIRED,
        direction_gate=PolicyMode.REQUIRED,
        sample_first=PolicyMode.REQUIRED,
        plan_gate=PolicyMode.REQUIRED,
        scene_ledger=PolicyMode.OPTIONAL,
        final_review=PolicyMode.REQUIRED,
        continuity=PolicyMode.OPTIONAL,
    ),
    ui=RecipeUIHints(
        category="create",
        primary_input_label="Песня или музыкальный фрагмент",
        visible_sections=("song", "music_map"),
        advanced_sections=("lyrics", "visual_style", "providers"),
        featured=True,
    ),
)

ACTION_TRANSFER = RecipeDefinition(
    recipe_id="action_transfer",
    title="Перенос движения",
    description="Перенос действия или движения из исходного видео на выбранный образ/персонажа.",
    required_inputs=("source_video", "target_reference"),
    optional_inputs=("instruction",),
    required_capabilities=("video.action_transfer",),
    optional_capabilities=("media.understand",),
    steps=(
        RecipeStep("source_review", "Проверка исходника", "Проверить движение и пригодность исходного фрагмента."),
        RecipeStep("sample", "Пробный результат", "Сначала получить один ограниченный тестовый результат.", "video.action_transfer"),
        RecipeStep("render", "Перенос движения", "Выполнить выбранный перенос после проверки теста.", "video.action_transfer"),
        RecipeStep("review", "Проверка", "Сравнить результат с исходным движением и заданием."),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.REQUIRED,
        sample_first=PolicyMode.REQUIRED,
        final_review=PolicyMode.REQUIRED,
    ),
    ui=RecipeUIHints(
        category="transform",
        primary_input_label="Исходное видео с движением",
        visible_sections=("source_video", "target_reference"),
        advanced_sections=("instruction", "providers"),
    ),
)

DIGITAL_HUMAN = RecipeDefinition(
    recipe_id="digital_human",
    title="Говорящий персонаж",
    description="Создание говорящего видео из портрета/персонажа и готовой либо синтезируемой речи.",
    required_inputs=("portrait", "speech"),
    optional_inputs=("instruction", "voice_reference"),
    required_capabilities=("video.digital_human",),
    optional_capabilities=("speech.synthesize", "media.understand"),
    steps=(
        RecipeStep("source_review", "Проверка материалов", "Проверить портрет и речевую дорожку."),
        RecipeStep("sample", "Пробный фрагмент", "Проверить короткий sample до полного рендера.", "video.digital_human"),
        RecipeStep("render", "Говорящее видео", "Создать полный результат.", "video.digital_human"),
        RecipeStep("review", "Проверка", "Проверить синхронизацию, лицо и звук."),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.REQUIRED,
        sample_first=PolicyMode.REQUIRED,
        final_review=PolicyMode.REQUIRED,
    ),
    ui=RecipeUIHints(
        category="performance",
        primary_input_label="Портрет и речь",
        visible_sections=("portrait", "speech"),
        advanced_sections=("voice", "providers"),
    ),
)

BUILTIN_RECIPES = (
    GENERAL_VIDEO,
    NARRATED_VIDEO,
    MUSIC_VIDEO,
    ACTION_TRANSFER,
    DIGITAL_HUMAN,
)

# Temporary compatibility metadata. This is deliberately kept outside the
# provider-neutral RecipeDefinition and may disappear when Stage 3 capability
# execution replaces direct pipeline binding.
VIDEOCLAW_PIPELINE_BINDINGS: dict[str, str] = {
    "narrated_video": "standard",
    "action_transfer": "action_transfer",
    "digital_human": "digital_human",
}


def build_builtin_registry() -> RecipeRegistry:
    return RecipeRegistry(BUILTIN_RECIPES)
