"""Provider-neutral Dubbing recipe for the permanent Product Recovery journey."""

from __future__ import annotations

from .models import PolicyMode, ProductionPolicy, RecipeDefinition, RecipeStep, RecipeUIHints

DUBBING = RecipeDefinition(
    recipe_id="dubbing",
    title="Дубляж видео",
    description=(
        "Замена речи в существующем видео через проверяемую цепочку: текст, подготовленная речь, "
        "Review, явное принятие и локальный финальный рендер."
    ),
    required_inputs=("source_video",),
    optional_inputs=("transcript", "translation", "speech_audio"),
    required_capabilities=("video.render_dubbing",),
    optional_capabilities=(
        "speech.transcribe",
        "text.translate",
        "speech.synthesize",
        "audio.align",
    ),
    steps=(
        RecipeStep(
            "source",
            "Исходное видео",
            "Импортировать проверенное project-owned видео, которое нужно озвучить.",
        ),
        RecipeStep(
            "transcript",
            "Текст речи",
            "Импортировать текст или получить ASR-черновик и явно принять его в проект.",
            "speech.transcribe",
            optional=True,
        ),
        RecipeStep(
            "speech",
            "Новая речь",
            "Импортировать, записать или синтезировать речь и привязать её к текущей ревизии текста.",
            "speech.synthesize",
            optional=True,
        ),
        RecipeStep(
            "review",
            "Проверка",
            "Проверить содержание, синхронизацию, тайминг и аудиобезопасность до принятия.",
        ),
        RecipeStep(
            "render",
            "Финальный рендер",
            "Собрать только явно принятый дубляж существующим локальным capability.",
            "video.render_dubbing",
        ),
    ),
    production_policy=ProductionPolicy(
        source_review=PolicyMode.REQUIRED,
        direction_gate=PolicyMode.OPTIONAL,
        sample_first=PolicyMode.OPTIONAL,
        plan_gate=PolicyMode.OPTIONAL,
        final_review=PolicyMode.REQUIRED,
        continuity=PolicyMode.OPTIONAL,
    ),
    ui=RecipeUIHints(
        category="transform",
        primary_input_label="Видео для дубляжа",
        visible_sections=("source_video", "transcript", "speech"),
        advanced_sections=("translation", "alignment", "providers"),
        featured=True,
    ),
)

__all__ = ["DUBBING"]
