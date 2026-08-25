"""Built-in named model identities above current capability execution mappings."""

from __future__ import annotations

from uv_studio.capabilities.builtin import build_builtin_capability_registry
from uv_studio.capabilities.models import MediaKind
from uv_studio.capabilities.registry import CapabilityRegistry

from .models import ModelDefinition, ModelRegistry

BUILTIN_MODELS = (
    ModelDefinition(
        model_id="uv.image.standard",
        title="UV Image Standard",
        description=(
            "Базовый пользовательский выбор для генерации изображения. "
            "Конкретный provider/adapter остаётся отдельным execution mapping и "
            "может требовать настройки перед запуском."
        ),
        capability_id="image.generate",
        offer_id="native_videoclaw.image_generate",
        output_kind=MediaKind.IMAGE,
    ),
)


def build_builtin_model_registry(
    capability_registry: CapabilityRegistry | None = None,
) -> ModelRegistry:
    capabilities = capability_registry or build_builtin_capability_registry()
    return ModelRegistry(capabilities, BUILTIN_MODELS)
