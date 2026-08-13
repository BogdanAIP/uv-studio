"""Built-in semantic capabilities and zero-credential adapter offers."""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

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
        "text.translate",
        "Перевод текста",
        "Перевод подготовленного текста между языками без привязки проектного состояния к конкретному провайдеру.",
        OperationKind.TRANSFORMATION,
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
        "speech.transcribe",
        "Распознавание речи",
        "Преобразование речи из аудио или видео в текст и временные речевые аннотации.",
        OperationKind.SPEECH,
        (MediaKind.AUDIO, MediaKind.VIDEO),
        (MediaKind.TEXT, MediaKind.SUBTITLE, MediaKind.METADATA),
        asynchronous=True,
    ),
    CapabilityDefinition(
        "audio.align",
        "Выравнивание речи",
        "Уточнение временной привязки подготовленного текста или речи к проектному аудио.",
        OperationKind.SPEECH,
        (MediaKind.AUDIO, MediaKind.TEXT),
        (MediaKind.METADATA,),
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
        "video.extract_range",
        "Извлечение диапазона видео",
        (
            "Детерминированное извлечение выбранного временного диапазона существующего видео "
            "и ограниченного контекста до/после без генеративной модели."
        ),
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.VIDEO,),
        (MediaKind.VIDEO,),
        asynchronous=False,
    ),
    CapabilityDefinition(
        "video.replace_range",
        "Замена диапазона видео",
        (
            "Детерминированная замена точного временного диапазона существующего видео "
            "подготовленным replacement-клипом без скрытого ретайминга или генеративной модели."
        ),
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.VIDEO,),
        (MediaKind.VIDEO,),
        asynchronous=False,
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
        "local_whisper_cpp",
        "Локальный whisper.cpp",
        "Локальное распознавание речи через отдельно устанавливаемый whisper.cpp без платного API.",
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


def _required_local_media_offer(
    *,
    offer_id: str,
    capability_id: str,
    title: str,
    available_reason: str,
    features: tuple[str, ...],
) -> CapabilityOffer:
    required_tools = ("ffmpeg", "ffprobe")
    missing = [tool for tool in required_tools if not shutil.which(tool)]
    return CapabilityOffer(
        offer_id=offer_id,
        capability_id=capability_id,
        adapter_id="local_ffmpeg",
        title=title,
        availability=(
            OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE
        ),
        reason=(
            f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
            if missing
            else available_reason
        ),
        locality=LocalityClass.LOCAL,
        cost_class=CostClass.FREE,
        asynchronous=False,
        features=features,
    )


def _range_extract_offer() -> CapabilityOffer:
    return _required_local_media_offer(
        offer_id="local_ffmpeg.video_extract_range",
        capability_id="video.extract_range",
        title="FFmpeg accurate-seek lossless range extraction",
        available_reason=(
            "FFmpeg и FFprobe найдены в PATH; локальное извлечение диапазона доступно."
        ),
        features=("video.range", "video.context", "video.lossless_intermediate"),
    )


def _range_replace_offer() -> CapabilityOffer:
    return _required_local_media_offer(
        offer_id="local_ffmpeg.video_replace_range",
        capability_id="video.replace_range",
        title="FFmpeg deterministic exact-range reinsertion",
        available_reason=(
            "FFmpeg и FFprobe найдены в PATH; локальная замена диапазона доступна."
        ),
        features=(
            "video.range_replace",
            "video.reinsertion",
            "video.lossless_intermediate",
        ),
    )


def _whisper_cpp_binary() -> str | None:
    configured = os.environ.get("UV_WHISPER_CPP_BIN")
    if configured:
        candidate = Path(configured).expanduser()
        return str(candidate) if candidate.is_file() else None
    return shutil.which("whisper-cli")


def _whisper_cpp_offer() -> CapabilityOffer:
    binary = _whisper_cpp_binary()
    ffmpeg = shutil.which("ffmpeg")
    configured_model = os.environ.get("UV_WHISPER_CPP_MODEL")
    model_ok = False
    if configured_model:
        model = Path(configured_model).expanduser()
        model_ok = model.is_file() and not model.is_symlink()

    if not binary:
        availability = OfferAvailability.UNAVAILABLE
        reason = (
            "whisper-cli не найден; установите pinned whisper.cpp runtime или задайте "
            "UV_WHISPER_CPP_BIN."
        )
    elif not ffmpeg:
        availability = OfferAvailability.UNAVAILABLE
        reason = "FFmpeg не найден в PATH; локальная подготовка аудио для whisper.cpp недоступна."
    elif not model_ok:
        availability = OfferAvailability.CONFIGURATION_REQUIRED
        reason = (
            "whisper.cpp runtime и FFmpeg найдены, но локальная модель не настроена; "
            "задайте UV_WHISPER_CPP_MODEL на существующий model file."
        )
    else:
        availability = OfferAvailability.AVAILABLE
        reason = (
            "Локальные whisper.cpp runtime, модель и FFmpeg настроены; "
            "распознавание речи доступно."
        )

    return CapabilityOffer(
        offer_id="local_whisper_cpp.speech_transcribe",
        capability_id="speech.transcribe",
        adapter_id="local_whisper_cpp",
        title="whisper.cpp local transcription",
        availability=availability,
        reason=reason,
        locality=LocalityClass.LOCAL,
        cost_class=CostClass.FREE,
        asynchronous=False,
        features=(
            "speech.timestamps",
            "speech.language_detection",
            "speech.local_cpu",
        ),
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
    registry.register_offer(_range_extract_offer())
    registry.register_offer(_range_replace_offer())
    registry.register_offer(_whisper_cpp_offer())
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
    # Intentionally no native offer for video.digital_human. text.translate and
    # audio.align stay definition-only until a concrete tested adapter is accepted.
    return registry
