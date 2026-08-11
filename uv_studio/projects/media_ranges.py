"""Exact provider-neutral media ranges for existing-video workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import ProjectValidationError, validate_project_relative_path

MEDIA_RANGE_SCHEMA_VERSION = 1
MICROSECONDS_PER_SECOND = 1_000_000


def _require_int_microseconds(value: Any, *, field_name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectValidationError(f"{field_name} must be an integer number of microseconds")
    if value < minimum:
        raise ProjectValidationError(f"{field_name} must be >= {minimum}")
    return value


@dataclass(frozen=True)
class ResolvedProjectMediaRange:
    """A requested range resolved against one concrete source duration."""

    source_path: str
    source_duration_us: int
    start_us: int
    end_us: int
    context_before_us: int
    context_after_us: int
    context_start_us: int
    context_end_us: int

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us

    @property
    def before_duration_us(self) -> int:
        return self.start_us - self.context_start_us

    @property
    def after_duration_us(self) -> int:
        return self.context_end_us - self.end_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "source_duration_us": self.source_duration_us,
            "requested": {
                "start_us": self.start_us,
                "end_us": self.end_us,
                "duration_us": self.duration_us,
            },
            "context": {
                "requested_before_us": self.context_before_us,
                "requested_after_us": self.context_after_us,
                "start_us": self.context_start_us,
                "end_us": self.context_end_us,
                "before_duration_us": self.before_duration_us,
                "after_duration_us": self.after_duration_us,
            },
        }


@dataclass(frozen=True)
class ProjectMediaRange:
    """Portable exact range expressed in integer microseconds.

    The user's requested interval is immutable. Context is represented separately and
    clamped only when the range is resolved against the actual source duration.
    """

    source_path: str
    start_us: int
    end_us: int
    context_before_us: int = 0
    context_after_us: int = 0
    schema_version: int = MEDIA_RANGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MEDIA_RANGE_SCHEMA_VERSION:
            raise ProjectValidationError(
                f"unsupported media range schema version: {self.schema_version!r}"
            )
        canonical = validate_project_relative_path(self.source_path)
        object.__setattr__(self, "source_path", canonical)
        start_us = _require_int_microseconds(self.start_us, field_name="start_us")
        end_us = _require_int_microseconds(self.end_us, field_name="end_us")
        _require_int_microseconds(self.context_before_us, field_name="context_before_us")
        _require_int_microseconds(self.context_after_us, field_name="context_after_us")
        if end_us <= start_us:
            raise ProjectValidationError("end_us must be greater than start_us")

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us

    def resolve(self, source_duration_us: int) -> ResolvedProjectMediaRange:
        duration_us = _require_int_microseconds(
            source_duration_us,
            field_name="source_duration_us",
            minimum=1,
        )
        if self.end_us > duration_us:
            raise ProjectValidationError(
                "requested media range ends after the source duration"
            )
        return ResolvedProjectMediaRange(
            source_path=self.source_path,
            source_duration_us=duration_us,
            start_us=self.start_us,
            end_us=self.end_us,
            context_before_us=self.context_before_us,
            context_after_us=self.context_after_us,
            context_start_us=max(0, self.start_us - self.context_before_us),
            context_end_us=min(duration_us, self.end_us + self.context_after_us),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_path": self.source_path,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "context_before_us": self.context_before_us,
            "context_after_us": self.context_after_us,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ProjectMediaRange":
        if not isinstance(raw, Mapping):
            raise ProjectValidationError("media range must be an object")
        allowed = {
            "schema_version",
            "source_path",
            "start_us",
            "end_us",
            "context_before_us",
            "context_after_us",
        }
        unknown = set(raw).difference(allowed)
        if unknown:
            raise ProjectValidationError(f"unsupported media range fields: {sorted(unknown)!r}")
        source_path = raw.get("source_path")
        if not isinstance(source_path, str):
            raise ProjectValidationError("source_path must be a string")
        return cls(
            source_path=source_path,
            start_us=raw.get("start_us"),
            end_us=raw.get("end_us"),
            context_before_us=raw.get("context_before_us", 0),
            context_after_us=raw.get("context_after_us", 0),
            schema_version=raw.get("schema_version", MEDIA_RANGE_SCHEMA_VERSION),
        )
