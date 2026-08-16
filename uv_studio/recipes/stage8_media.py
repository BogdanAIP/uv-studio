"""Stage 8 deterministic local-media recipe definitions."""

from __future__ import annotations

from .models import PolicyMode, ProductionPolicy, RecipeDefinition, RecipeStep, RecipeUIHints

PHOTO_TO_VIDEO = RecipeDefinition(
    recipe_id="photo_to_video",
    title="Фото в видео",
    description=(
        "Детерминированный видеоролик из project-owned неподвижных изображений, "
        "опционально с готовой аудиодорожкой, без обязательного генеративного провайдера."
    ),
    required_inputs=("images",),
    optional_inputs=("audio", "brief", "duration_per_image"),
    required_capabilities=("video.compose_photos",),
    optional_capabilities=("image.generate", "media.understand"),
    steps=(
        RecipeStep("source_review", "Проверка фото", "Проверить порядок, кадрирование и пригодность исходных изображений."),
        RecipeStep("timing", "Тайминг", "Задать длительность показа фотографий и опциональную аудиодорожку."),
        RecipeStep("render", "Сборка видео", "Собрать изображения локальным детерминированным capability.", "video.compose_photos"),
        RecipeStep("review", "Проверка", "Проверить порядок, длительность, геометрию и аудио готового ролика."),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.REQUIRED,
        direction_gate=PolicyMode.OPTIONAL,
        sample_first=PolicyMode.OPTIONAL,
        plan_gate=PolicyMode.REQUIRED,
        final_review=PolicyMode.REQUIRED,
    ),
    ui=RecipeUIHints(
        category="create",
        primary_input_label="Фотографии",
        visible_sections=("images", "timing"),
        advanced_sections=("audio", "providers"),
        featured=True,
    ),
)

VISUALIZER = RecipeDefinition(
    recipe_id="visualizer",
    title="Аудиовизуализатор",
    description=(
        "Локальный waveform-визуализатор project-owned аудио, опционально поверх обложки, "
        "без обязательной генеративной модели или платного API."
    ),
    required_inputs=("audio",),
    optional_inputs=("artwork", "brief"),
    required_capabilities=("audio.visualize",),
    optional_capabilities=("image.generate", "audio.analyze_music", "media.understand"),
    steps=(
        RecipeStep("source_review", "Проверка аудио", "Проверить master-аудио и опциональную обложку."),
        RecipeStep("direction", "Вид визуализатора", "Подтвердить композицию без выбора конкретного провайдера."),
        RecipeStep("render", "Визуализатор", "Создать локальный waveform-видеоряд с master-аудио.", "audio.visualize"),
        RecipeStep("review", "Проверка", "Проверить длительность, наличие master-аудио и визуальный результат."),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.REQUIRED,
        direction_gate=PolicyMode.OPTIONAL,
        sample_first=PolicyMode.OFF,
        plan_gate=PolicyMode.OPTIONAL,
        final_review=PolicyMode.REQUIRED,
    ),
    ui=RecipeUIHints(
        category="create",
        primary_input_label="Аудиодорожка",
        visible_sections=("audio", "artwork"),
        advanced_sections=("analysis", "providers"),
        featured=True,
    ),
)

STAGE8_MEDIA_RECIPES = (PHOTO_TO_VIDEO, VISUALIZER)
