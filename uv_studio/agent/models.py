"""Bounded, portable contracts for the UV-owned Agent Harness foundation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from uv_studio.capabilities.models import CapabilityEffects
from uv_studio.projects.models import ProjectValidationError, validate_identifier

AGENT_CONTEXT_SCHEMA_VERSION = 1
AGENT_TRACE_SCHEMA_VERSION = 1
AGENT_TRACE_RECORD_TYPE = "agent_trace"

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_SENSITIVE_VALUE = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._~+/-]{8,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization_token|password|secret)\s*[:=])"
)
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization_token",
    "password",
    "secret",
    "cookie",
    "credentials",
}


class AgentHarnessError(RuntimeError):
    """Base error for bounded Agent Harness contracts."""


class AgentPortableStateError(AgentHarnessError):
    """A context/trace value is unsafe or non-portable."""


class AgentUnknownAction(AgentHarnessError):
    """The requested action is not present in the deterministic catalog."""


def _looks_absolute_path(value: str) -> bool:
    stripped = value.strip()
    return (
        stripped.startswith("/")
        or stripped.startswith("\\\\")
        or stripped.startswith("~/")
        or stripped.startswith("~\\")
        or stripped.lower().startswith("file://")
        or _WINDOWS_ABSOLUTE.match(stripped) is not None
    )


def _contains_sensitive_value(value: str) -> bool:
    return _SENSITIVE_VALUE.search(value) is not None


def _contains_absolute_host_path(value: str) -> bool:
    for fragment in re.split(r"[\s'\"()\[\]{},;]+", value):
        fragment = fragment.strip(".,:")
        if not fragment:
            continue
        if _WINDOWS_ABSOLUTE.match(fragment) is not None:
            return True
        if fragment.startswith("\\\\"):
            return True
        if fragment.startswith("~/") or fragment.startswith("~\\"):
            return True
        if fragment.lower().startswith("file://"):
            return True
        if fragment.startswith("/") and (
            fragment.count("/") >= 2
            or fragment.startswith(("/home/", "/Users/", "/tmp/", "/var/", "/etc/", "/opt/", "/mnt/", "/private/", "/Volumes/"))
        ):
            return True
    return False


def safe_text(
    value: Any,
    *,
    field_name: str,
    allow_empty: bool = False,
    max_length: int = 4000,
) -> str:
    if not isinstance(value, str):
        raise AgentPortableStateError(f"{field_name} must be text")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise AgentPortableStateError(f"{field_name} must be non-empty text")
    if len(normalized) > max_length:
        raise AgentPortableStateError(f"{field_name} exceeds {max_length} characters")
    if _looks_absolute_path(normalized) or _contains_absolute_host_path(normalized):
        raise AgentPortableStateError(f"{field_name} must not contain an absolute host path")
    if _contains_sensitive_value(normalized):
        raise AgentPortableStateError(f"{field_name} must not contain secret/token material")
    return normalized


def portable_json(value: Any, *, field_name: str = "value") -> Any:
    """Detach strict JSON while rejecting sensitive keys and host-path values."""

    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        try:
            encoded = json.dumps(value, allow_nan=False)
            return json.loads(encoded)
        except (ValueError, json.JSONDecodeError) as exc:
            raise AgentPortableStateError(f"{field_name} must contain finite JSON") from exc
    if isinstance(value, str):
        return safe_text(value, field_name=field_name, allow_empty=True)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise AgentPortableStateError(f"{field_name} keys must be strings")
            normalized_key = key.strip()
            if not normalized_key:
                raise AgentPortableStateError(f"{field_name} contains an empty key")
            if normalized_key.lower() in _SENSITIVE_KEYS:
                raise AgentPortableStateError(
                    f"{field_name} contains forbidden sensitive key {normalized_key!r}"
                )
            result[normalized_key] = portable_json(
                item,
                field_name=f"{field_name}.{normalized_key}",
            )
        return result
    if isinstance(value, (list, tuple)):
        return [
            portable_json(item, field_name=f"{field_name}[{index}]")
            for index, item in enumerate(value)
        ]
    raise AgentPortableStateError(
        f"{field_name} contains non-portable value of type {type(value).__name__}"
    )


def stable_digest(value: Mapping[str, Any]) -> str:
    normalized = portable_json(value, field_name="digest payload")
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    if _contains_sensitive_value(message):
        return "execution failed; sensitive details were omitted"
    fragments = re.split(r"[\s'\"()]+", message)
    if any(_looks_absolute_path(fragment) for fragment in fragments if fragment):
        return "execution failed; host-path details were omitted"
    return message[:1000]


@dataclass(frozen=True)
class AgentContextSnapshot:
    project_id: str
    target_kind: str
    target_id: str
    content: dict[str, Any]
    schema_version: int = AGENT_CONTEXT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_CONTEXT_SCHEMA_VERSION:
            raise AgentPortableStateError(
                f"AgentContextSnapshot only represents schema v{AGENT_CONTEXT_SCHEMA_VERSION}"
            )
        try:
            object.__setattr__(
                self,
                "project_id",
                validate_identifier(self.project_id, field_name="project_id"),
            )
            object.__setattr__(
                self,
                "target_id",
                validate_identifier(self.target_id, field_name="target_id"),
            )
        except ProjectValidationError as exc:
            raise AgentPortableStateError(str(exc)) from exc
        if self.target_kind not in {"project", "shot"}:
            raise AgentPortableStateError("target_kind must be 'project' or 'shot'")
        object.__setattr__(
            self,
            "content",
            portable_json(self.content, field_name="agent context"),
        )

    @property
    def digest(self) -> str:
        return stable_digest(
            {
                "schema_version": self.schema_version,
                "project_id": self.project_id,
                "target_kind": self.target_kind,
                "target_id": self.target_id,
                "content": self.content,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "digest": self.digest,
            "content": portable_json(self.content, field_name="agent context"),
        }


@dataclass(frozen=True)
class AgentActionDefinition:
    action_id: str
    title: str
    description: str
    authority: str
    input_fields: tuple[str, ...]
    effects: CapabilityEffects = field(default_factory=CapabilityEffects)
    requires_model: bool = False
    uses_job_manager: bool | None = None
    authorization_may_be_required: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not re.fullmatch(
            r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
            self.action_id,
        ):
            raise AgentPortableStateError(f"invalid action_id: {self.action_id!r}")
        object.__setattr__(self, "title", safe_text(self.title, field_name="action title", max_length=200))
        object.__setattr__(
            self,
            "description",
            safe_text(self.description, field_name="action description"),
        )
        object.__setattr__(
            self,
            "authority",
            safe_text(self.authority, field_name="action authority", max_length=300),
        )
        fields = tuple(self.input_fields)
        if any(not isinstance(item, str) or not item for item in fields):
            raise AgentPortableStateError("action input_fields must be non-empty strings")
        if len(fields) != len(set(fields)):
            raise AgentPortableStateError("action input_fields must be unique")
        object.__setattr__(self, "input_fields", fields)
        if not isinstance(self.effects, CapabilityEffects):
            raise AgentPortableStateError("action effects must be CapabilityEffects")
        if not isinstance(self.requires_model, bool):
            raise AgentPortableStateError("requires_model must be boolean")

        # Stage 15 has one model-bound action: generation.submit. It necessarily
        # enters the existing Job Manager and can reach D-017 depending on the
        # selected offer. Keep explicit overrides available for future actions.
        uses_job_manager = self.requires_model if self.uses_job_manager is None else self.uses_job_manager
        authorization_may_be_required = (
            self.requires_model
            if self.authorization_may_be_required is None
            else self.authorization_may_be_required
        )
        if not isinstance(uses_job_manager, bool):
            raise AgentPortableStateError("uses_job_manager must be boolean")
        if not isinstance(authorization_may_be_required, bool):
            raise AgentPortableStateError("authorization_may_be_required must be boolean")
        object.__setattr__(self, "uses_job_manager", uses_job_manager)
        object.__setattr__(
            self,
            "authorization_may_be_required",
            authorization_may_be_required,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "title": self.title,
            "description": self.description,
            "authority": self.authority,
            "input_fields": list(self.input_fields),
            "effects": self.effects.to_dict(),
            "uses_job_manager": self.uses_job_manager,
            "authorization_may_be_required": self.authorization_may_be_required,
            "requires_model": self.requires_model,
        }


@dataclass(frozen=True)
class AgentPolicyProjection:
    action_id: str
    available: bool
    reason: str
    locality: str
    cost_class: str
    authorization_required: bool
    consent_required: tuple[str, ...]
    effects: CapabilityEffects
    model_id: str | None = None
    capability_id: str | None = None
    offer_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not re.fullmatch(
            r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
            self.action_id,
        ):
            raise AgentPortableStateError(f"invalid policy action_id: {self.action_id!r}")
        if not isinstance(self.available, bool):
            raise AgentPortableStateError("policy available must be boolean")
        if not isinstance(self.authorization_required, bool):
            raise AgentPortableStateError("policy authorization_required must be boolean")
        object.__setattr__(
            self,
            "reason",
            safe_text(self.reason, field_name="policy reason", max_length=1000),
        )
        object.__setattr__(
            self,
            "locality",
            safe_text(self.locality, field_name="policy locality", max_length=100),
        )
        object.__setattr__(
            self,
            "cost_class",
            safe_text(self.cost_class, field_name="policy cost_class", max_length=100),
        )
        if not isinstance(self.effects, CapabilityEffects):
            raise AgentPortableStateError("policy effects must be CapabilityEffects")
        scopes = tuple(
            safe_text(item, field_name="consent scope", max_length=100)
            for item in self.consent_required
        )
        object.__setattr__(self, "consent_required", scopes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "available": self.available,
            "reason": self.reason,
            "locality": self.locality,
            "cost_class": self.cost_class,
            "authorization_required": self.authorization_required,
            "consent_required": list(self.consent_required),
            "effects": self.effects.to_dict(),
            "model_id": self.model_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentPolicyProjection":
        if not isinstance(data, Mapping):
            raise AgentPortableStateError("trace policy must be a JSON object")
        effects = data.get("effects")
        if not isinstance(effects, Mapping):
            raise AgentPortableStateError("trace policy effects must be a JSON object")
        return cls(
            action_id=data["action_id"],
            available=data["available"],
            reason=data["reason"],
            locality=data["locality"],
            cost_class=data["cost_class"],
            authorization_required=data["authorization_required"],
            consent_required=tuple(data.get("consent_required", ())),
            effects=CapabilityEffects(**dict(effects)),
            model_id=data.get("model_id"),
            capability_id=data.get("capability_id"),
            offer_id=data.get("offer_id"),
        )


class AgentTraceStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


_TRACE_REFERENCE_FIELDS = {
    "transaction_id",
    "job_id",
    "attempt_id",
    "output_reference_id",
    "take_id",
    "track_id",
    "clip_id",
}


@dataclass(frozen=True)
class AgentTraceRecord:
    trace_id: str
    project_id: str
    created_at: str
    context_digest: str
    action_id: str
    input_digest: str
    canonical_references: tuple[str, ...]
    policy: AgentPolicyProjection
    status: AgentTraceStatus
    result_references: dict[str, str] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None
    schema_version: int = AGENT_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_TRACE_SCHEMA_VERSION:
            raise AgentPortableStateError(
                f"AgentTraceRecord only represents schema v{AGENT_TRACE_SCHEMA_VERSION}"
            )
        for field_name in ("trace_id", "project_id"):
            try:
                object.__setattr__(
                    self,
                    field_name,
                    validate_identifier(getattr(self, field_name), field_name=field_name),
                )
            except ProjectValidationError as exc:
                raise AgentPortableStateError(str(exc)) from exc
        if not isinstance(self.created_at, str) or not self.created_at:
            raise AgentPortableStateError("trace created_at is required")
        for field_name in ("context_digest", "input_digest"):
            value = getattr(self, field_name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(ch not in "0123456789abcdef" for ch in value)
            ):
                raise AgentPortableStateError(f"{field_name} must be lowercase SHA-256 hex")
        if not isinstance(self.policy, AgentPolicyProjection):
            raise AgentPortableStateError("trace policy must be AgentPolicyProjection")
        if self.policy.action_id != self.action_id:
            raise AgentPortableStateError("trace policy action_id mismatch")
        object.__setattr__(
            self,
            "status",
            self.status if isinstance(self.status, AgentTraceStatus) else AgentTraceStatus(self.status),
        )
        refs = tuple(self.canonical_references)
        try:
            refs = tuple(
                validate_identifier(item, field_name="canonical reference")
                for item in refs
            )
        except ProjectValidationError as exc:
            raise AgentPortableStateError(str(exc)) from exc
        if len(refs) != len(set(refs)):
            raise AgentPortableStateError("canonical_references must be unique")
        object.__setattr__(self, "canonical_references", refs)

        result_refs: dict[str, str] = {}
        for key, value in self.result_references.items():
            if key not in _TRACE_REFERENCE_FIELDS:
                raise AgentPortableStateError(f"unsupported trace result reference: {key!r}")
            try:
                result_refs[key] = validate_identifier(value, field_name=f"trace {key}")
            except ProjectValidationError as exc:
                raise AgentPortableStateError(str(exc)) from exc
        object.__setattr__(self, "result_references", result_refs)

        if self.status is AgentTraceStatus.SUCCEEDED:
            if self.error_type is not None or self.error_message is not None:
                raise AgentPortableStateError("successful trace must not contain an error")
        else:
            if not self.error_type:
                raise AgentPortableStateError("failed trace requires error_type")
            object.__setattr__(
                self,
                "error_type",
                safe_text(self.error_type, field_name="trace error_type", max_length=200),
            )
            if self.error_message is None:
                raise AgentPortableStateError("failed trace requires error_message")
            object.__setattr__(
                self,
                "error_message",
                safe_text(
                    self.error_message,
                    field_name="trace error_message",
                    max_length=1000,
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": AGENT_TRACE_RECORD_TYPE,
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "context_digest": self.context_digest,
            "action_id": self.action_id,
            "input_digest": self.input_digest,
            "canonical_references": list(self.canonical_references),
            "policy": self.policy.to_dict(),
            "status": self.status.value,
            "result_references": dict(self.result_references),
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def agent_trace_from_dict(data: Mapping[str, Any]) -> AgentTraceRecord:
    if not isinstance(data, Mapping) or data.get("record_type") != AGENT_TRACE_RECORD_TYPE:
        raise AgentPortableStateError("task record is not an Agent trace")
    try:
        return AgentTraceRecord(
            schema_version=data["schema_version"],
            trace_id=data["trace_id"],
            project_id=data["project_id"],
            created_at=data["created_at"],
            context_digest=data["context_digest"],
            action_id=data["action_id"],
            input_digest=data["input_digest"],
            canonical_references=tuple(data.get("canonical_references", ())),
            policy=AgentPolicyProjection.from_dict(data["policy"]),
            status=data["status"],
            result_references=dict(data.get("result_references", {})),
            error_type=data.get("error_type"),
            error_message=data.get("error_message"),
        )
    except KeyError as exc:
        raise AgentPortableStateError(f"missing Agent trace field: {exc.args[0]}") from exc
