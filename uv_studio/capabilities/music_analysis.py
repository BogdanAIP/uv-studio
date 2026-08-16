"""Provider-neutral semantic capability for optional Stage 7 music analysis."""

from __future__ import annotations

from .models import CapabilityDefinition, MediaKind, OperationKind
from .registry import CapabilityRegistry


def register_music_analysis_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            capability_id="audio.analyze_music",
            title="Анализ структуры песни",
            description=(
                "Предлагает структуру, музыкальные маркеры и текстовые/вокальные фразы для "
                "Music Analysis Assist. Результат остаётся non-canonical до явного подтверждения Music Map."
            ),
            operation_kind=OperationKind.UNDERSTANDING,
            input_kinds=(MediaKind.AUDIO,),
            output_kinds=(MediaKind.METADATA,),
            asynchronous=False,
        )
    )
