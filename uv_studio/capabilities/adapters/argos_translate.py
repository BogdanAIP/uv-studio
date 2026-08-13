"""Provider-neutral local text translation through optional Argos Translate runtime."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any

from uv_studio.projects.store import ProjectStore

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import CapabilityOffer, CostClass, LocalityClass, OfferAvailability

_MAX_SEGMENTS = 100_000
_MAX_TEXT_LENGTH = 8_000
LoadLanguages = Callable[[], list[Any]]


def _default_language_loader() -> list[Any]:
    try:
        module = importlib.import_module("argostranslate.translate")
    except (ImportError, OSError) as exc:
        raise CapabilityToolUnavailable("Argos Translate runtime is not installed") from exc
    try:
        languages = module.load_installed_languages()
    except Exception as exc:  # Argos may surface model/runtime-specific errors.
        raise CapabilityToolFailed(f"Argos Translate could not load installed languages: {exc}") from exc
    return list(languages)


def _language_code(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvalidCapabilityInput(f"{field_name} must be a language code string")
    normalized = value.strip().lower().split("-", 1)[0]
    if not 2 <= len(normalized) <= 8 or not normalized.isalpha():
        raise InvalidCapabilityInput(f"{field_name} must be a portable language code")
    return normalized


def _segment(value: Any, *, index: int) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise InvalidCapabilityInput(f"segments[{index}] must be an object")
    unknown = set(value).difference({"segment_id", "text"})
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported segments[{index}] fields: {sorted(unknown)!r}"
        )
    segment_id = value.get("segment_id")
    text = value.get("text")
    if not isinstance(segment_id, str) or not segment_id.strip():
        raise InvalidCapabilityInput(f"segments[{index}].segment_id must be a non-empty string")
    if not isinstance(text, str) or not text.strip():
        raise InvalidCapabilityInput(f"segments[{index}].text must be a non-empty string")
    if len(text) > _MAX_TEXT_LENGTH:
        raise InvalidCapabilityInput(
            f"segments[{index}].text must be <= {_MAX_TEXT_LENGTH} characters"
        )
    return {"segment_id": segment_id.strip(), "text": text.strip()}


class ArgosTranslateAdapter:
    """Translate bounded text segments without persisting provider/model identity in project state."""

    adapter_id = "local_argos_translate"

    def __init__(
        self,
        store: ProjectStore,
        *,
        language_loader: LoadLanguages = _default_language_loader,
    ) -> None:
        self.store = store
        self.language_loader = language_loader

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != ArgosTranslateAdapter.adapter_id:
            raise UnsupportedCapabilityExecution(
                f"Argos executor cannot run adapter {offer.adapter_id!r}"
            )
        if offer.capability_id != "text.translate":
            raise UnsupportedCapabilityExecution(
                f"Argos executor does not implement {offer.capability_id!r}"
            )
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution(
                f"offer {offer.offer_id!r} is not currently available"
            )
        if offer.locality is not LocalityClass.LOCAL or offer.cost_class is not CostClass.FREE:
            raise UnsupportedCapabilityExecution(
                "Argos executor accepts only explicit local/free offers"
            )

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        self.store.load_project(project_id)
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("text.translate input must be a JSON object")
        allowed = {"source_language", "target_language", "segments"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(
                f"unsupported text.translate fields: {sorted(unknown)!r}"
            )
        source_language = _language_code(payload.get("source_language"), field_name="source_language")
        target_language = _language_code(payload.get("target_language"), field_name="target_language")
        if source_language == target_language:
            raise InvalidCapabilityInput("source_language and target_language must differ")
        raw_segments = payload.get("segments")
        if not isinstance(raw_segments, list) or not raw_segments:
            raise InvalidCapabilityInput("text.translate requires a non-empty segments array")
        if len(raw_segments) > _MAX_SEGMENTS:
            raise InvalidCapabilityInput(
                f"text.translate supports at most {_MAX_SEGMENTS} segments per execution"
            )
        segments = tuple(_segment(item, index=index) for index, item in enumerate(raw_segments))
        ids = [item["segment_id"] for item in segments]
        if len(ids) != len(set(ids)):
            raise InvalidCapabilityInput("text.translate segment_id values must be unique")

        languages = self.language_loader()
        by_code = {
            str(getattr(language, "code", "")).strip().lower(): language
            for language in languages
            if str(getattr(language, "code", "")).strip()
        }
        source = by_code.get(source_language)
        target = by_code.get(target_language)
        if source is None:
            raise InvalidCapabilityInput(
                f"Argos source language package {source_language!r} is not installed"
            )
        if target is None:
            raise InvalidCapabilityInput(
                f"Argos target language package {target_language!r} is not installed"
            )
        try:
            translation = source.get_translation(target)
        except Exception as exc:
            raise CapabilityToolFailed(
                f"Argos Translate could not resolve {source_language}->{target_language}: {exc}"
            ) from exc
        if translation is None:
            raise InvalidCapabilityInput(
                f"Argos translation package {source_language}->{target_language} is not installed"
            )

        output_segments: list[dict[str, str]] = []
        for item in segments:
            try:
                translated = translation.translate(item["text"])
            except Exception as exc:
                raise CapabilityToolFailed(
                    f"Argos Translate failed for segment {item['segment_id']!r}: {exc}"
                ) from exc
            if not isinstance(translated, str) or not translated.strip():
                raise CapabilityToolFailed(
                    f"Argos Translate returned empty text for segment {item['segment_id']!r}"
                )
            if len(translated) > _MAX_TEXT_LENGTH:
                raise CapabilityToolFailed(
                    f"Argos Translate output for segment {item['segment_id']!r} exceeds project text limit"
                )
            output_segments.append(
                {"segment_id": item["segment_id"], "text": translated.strip()}
            )

        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "source_language": source_language,
                "target_language": target_language,
                "segments": output_segments,
            },
        )
