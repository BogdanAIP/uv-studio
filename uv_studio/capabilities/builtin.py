"""Built-in semantic capabilities and zero-credential adapter offers."""

from __future__ import annotations

import importlib.util
import shutil

from .models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from .registry import CapabilityRegistry

CAPABILITIES = (
    CapabilityDefinition(
        "text.generate",
        "Генерация текста",
        "Создание или преобразование текста для сценариев и производственных планов.",
        OperationKind.GENERATION,
        (MediaKind.TEXT,),
        (MediaKind.TEXT,),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "image.generate",
        "Генерация изображений",
        "Создание изображения из текстового задания или проектного контекста.",
        OperationKind.GENERATION,
        (MediaKind.TEXT,),
        (MediaKind.IMAGE,),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "video.generate",
        "Генерация видео",
        "Создание видео из текстового и/или визуального задания.",
        OperationKind.GENERATION,
        (MediaKind.TEXT, MediaKind.IMAGE),
        (MediaKind.VIDEO,),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "video.action_transfer",
        "Перенос движения",
        "Перенос движения из исходного видео на целевой визуальный образ.",
        OperationKind.TRANSFORMATION,
        (MediaKind.VIDEO, MediaKind.IMAGE, MediaKind.TEXT),
        (MediaKind.VIDEO,),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "video.digital_human",
        "Говорящее видео",
        "Создание говорящего персонажа из визуального образа и речевого материала.",
        OperationKind.TRANSFORMATION,
        (MediaKind.IMAGE, MediaKind.AUDIO),
        (MediaKind.VIDEO,),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "speech.synthesize",
        "Синтез речи",
        "Создание речевой аудиодорожки по тексту.",
        OperationKind.SPEECH,
        (MediaKind.TEXT,),
        (MediaKind.AUDIO,),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "media.understand",
        "Понимание медиа",
        "Структурированный анализ изображения, видео или аудио.",
        OperationKind.UNDERSTANDING,
        (MediaKind.IMAGE, MediaKind.VIDEO, MediaKind.AUDIO),
        (MediaKind.TEXT, MediaKind.METADATA),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "timeline.assemble",
        "Сборка таймлайна",
        "Детерминированная сборка подготовленных медиафрагментов в итоговую последовательность.",
        OperationKind.ASSEMBLY,
        (MediaKind.VIDEO, MediaKind.AUDIO, MediaKind.TIMELINE),
        (MediaKind.VIDEO,),
        asynchronous=False,
    ),
    CapabilityDefinition(
        "audio.mix",
        "Сведение аудио",
        "Детерминированное сведение подготовленных звуковых дорожек.",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.AUDIO,),
        (MediaKind.AUDIO,),
        asynchronous=False,
    ),
    CapabilityDefinition(
        "subtitle.render",
        "Рендер субтитров",
        "Добавление подготовленных субтитров в видео.",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.VIDEO, MediaKind.SUBTITLE),
        (MediaKind.VIDEO,),
        asynchronous=False,
    ),
    CapabilityDefinition(
        "media.probe",
        "Анализ параметров медиа",
        "Получение технических параметров локального медиафайла без генеративной модели.",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.VIDEO, MediaKind.AUDIO),
        (MediaKind.METADATA,),
        asynchronous=False,
    ),
)

ADAPTERS = (
    AdapterDefinition(
        "local_ffmpeg",
        "Локальный FFmpeg",
        "Локальные детерминированные медиаоперации без платного ИИ API.",
        AdapterKind.LOCAL,
    ),
    AdapterDefinition(
        "native_videoclaw",
        "Совместимость VideoClaw",
        "Существующие модели и специализированные pipelines pinned VideoClaw во время миграции.",
        AdapterKind.NATIVE,
    ),
)


def _tool_offer(
    *,
    offer_id: str,
    capability_id: str,
    tool: str,
    title: str,
    features: tuple[str, ...] = (),
) -> CapabilityOffer:
    path = shutil.which(tool)
    return CapabilityOffer(
        offer_id=offer_id,
        capability_id=capability_id,
        adapter_id="local_ffmpeg",
        title=title,
        availability=OfferAvailability.AVAILABLE if path else OfferAvailability.UNAVAILABLE,
        reason=(
            f"{tool} найден в PATH; локальный инструмент доступен."
            if path
            else f"{tool} не найден в PATH этой установки."
        ),
        locality=LocalityClass.LOCAL,
        cost_class=CostClass.FREE,
        asynchronous=False,
        features=features,
    )


def _native_model_offer(
    *,
    offer_id: str,
    capability_id: str,
    title: str,
    features: tuple[str, ...] = (),
) -> CapabilityOffer:
    return CapabilityOffer(
        offer_id=offer_id,
        capability_id=capability_id,
        adapter_id="native_videoclaw",
        title=title,
        availability=OfferAvailability.CONFIGURATION_REQUIRED,
        reason=(
            "Pinned VideoClaw содержит совместимый model/pipeline слой, но конкретная модель и её "
            "учётные данные ещё не выбраны через UV Studio Capability Registry."
        ),
        locality=LocalityClass.HYBRID,
        cost_class=CostClass.POTENTIALLY_PAID,
        asynchronous=True,
        features=features,
    )


def _edge_tts_offer() -> CapabilityOffer:
    installed = importlib.util.find_spec("edge_tts") is not None
    return CapabilityOffer(
        offer_id="native_videoclaw.edge_tts",
        capability_id="speech.synthesize",
        adapter_id="native_videoclaw",
        title="Edge TTS compatibility",
        availability=OfferAvailability.AVAILABLE if installed else OfferAvailability.UNAVAILABLE,
        reason=(
            "Пакет edge-tts установлен; API-ключ не требуется."
            if installed
            else "Пакет edge-tts не установлен в текущем Python окружении."
        ),
        locality=LocalityClass.REMOTE,
        cost_class=CostClass.FREE,
        asynchronous=True,
        features=("speech.keyless",),
    )


def build_builtin_capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry(CAPABILITIES, ADAPTERS)
    registry.register_offer(
        _tool_offer(
            offer_id="local_ffmpeg.timeline_assemble",
            capability_id="timeline.assemble",
            tool="ffmpeg",
            title="FFmpeg local assembly",
            features=("video.concat",),
        )
    )
    registry.register_offer(
        _tool_offer(
            offer_id="local_ffmpeg.media_probe",
            capability_id="media.probe",
            tool="ffprobe",
            title="FFprobe local media probe",
            features=("media.metadata",),
        )
    )
    registry.register_offer(
        _native_model_offer(
            offer_id="native_videoclaw.text_generate",
            capability_id="text.generate",
            title="VideoClaw text model layer",
        )
    )
    registry.register_offer(
        _native_model_offer(
            offer_id="native_videoclaw.image_generate",
            capability_id="image.generate",
            title="VideoClaw image model layer",
        )
    )
    registry.register_offer(
        _native_model_offer(
            offer_id="native_videoclaw.video_generate",
            capability_id="video.generate",
            title="VideoClaw video model layer",
        )
    )
    registry.register_offer(
        _native_model_offer(
            offer_id="native_videoclaw.action_transfer",
            capability_id="video.action_transfer",
            title="VideoClaw action-transfer model layer",
            features=("video.motion_reference",),
        )
    )
    registry.register_offer(_edge_tts_offer())
    # Intentionally no native offer for video.digital_human: Stage 2 proved that
    # the pinned product-promo contract does not match portrait + supplied speech.
    # Likewise media.understand/audio.mix/subtitle.render stay definition-only until
    # a concrete, tested adapter is registered.
    return registry
