"""Machine-global MCP profile, binding and discovery metadata.

Profiles deliberately store environment variable *references*, never secret values.
They are UV Studio machine configuration and are not part of portable projects.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from uv_studio.capabilities.models import CostClass, LocalityClass, validate_capability_id

MCP_CONFIG_SCHEMA_VERSION = 1
MCP_PROJECT_FILE_INPUT_SCHEMA_VERSION = 1
MCP_PROJECT_FILE_ALLOWED_ROOTS = frozenset(("sources", "assets", "artifacts", "exports"))
_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_SCHEMA_BYTES = 64 * 1024
_MAX_TOOLS = 500


class MCPConfigurationError(ValueError):
    pass


class MCPTransport(str, Enum):
    STDIO = "stdio"


class MCPRuntimeState(str, Enum):
    CONFIGURED = "configured"
    DISCOVERING = "discovering"
    READY = "ready"
    FAILED = "failed"
    STOPPED = "stopped"


def _clean_text(value: Any, *, field_name: str, max_length: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MCPConfigurationError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if "\x00" in normalized:
        raise MCPConfigurationError(f"{field_name} contains a NUL byte")
    if len(normalized) > max_length:
        raise MCPConfigurationError(f"{field_name} is too long")
    return normalized


def _enum_value(value: Any, enum_type: type[Enum], *, field_name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise MCPConfigurationError(f"invalid {field_name}: {value!r}") from exc


def _exact_keys(data: Mapping[str, Any], allowed: set[str], *, context: str) -> None:
    unknown = set(data).difference(allowed)
    if unknown:
        raise MCPConfigurationError(f"unsupported {context} fields: {sorted(unknown)!r}")


def _timeout(value: Any, *, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise MCPConfigurationError(f"{field_name} must be numeric") from exc
    if number < 0.1 or number > 120.0:
        raise MCPConfigurationError(f"{field_name} must be between 0.1 and 120 seconds")
    return number


def _schema(value: Any, *, field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MCPConfigurationError(f"{field_name} must be an object when present")
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise MCPConfigurationError(f"{field_name} must be JSON serializable") from exc
    if len(encoded.encode("utf-8")) > _MAX_SCHEMA_BYTES:
        raise MCPConfigurationError(f"{field_name} exceeds {_MAX_SCHEMA_BYTES} bytes")
    return dict(value)


@dataclass(frozen=True)
class MCPProfile:
    profile_id: str
    title: str
    command: str
    args: tuple[str, ...] = ()
    cwd: str | None = None
    env_refs: tuple[tuple[str, str], ...] = ()
    enabled: bool = True
    startup_timeout_sec: float = 10.0
    discovery_timeout_sec: float = 15.0
    transport: MCPTransport = MCPTransport.STDIO
    schema_version: int = MCP_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MCP_CONFIG_SCHEMA_VERSION:
            raise MCPConfigurationError(f"MCPProfile only supports schema v{MCP_CONFIG_SCHEMA_VERSION}")
        object.__setattr__(self, "profile_id", validate_capability_id(self.profile_id, field_name="profile_id"))
        object.__setattr__(self, "title", _clean_text(self.title, field_name="title", max_length=200))
        object.__setattr__(self, "command", _clean_text(self.command, field_name="command", max_length=2000))
        if not isinstance(self.args, tuple):
            raise MCPConfigurationError("args must be a tuple")
        normalized_args = tuple(_clean_text(value, field_name="arg", max_length=4000) for value in self.args)
        if len(normalized_args) > 100:
            raise MCPConfigurationError("args contains too many entries")
        object.__setattr__(self, "args", normalized_args)
        if self.cwd is not None:
            object.__setattr__(self, "cwd", _clean_text(self.cwd, field_name="cwd", max_length=4000))
        if not isinstance(self.env_refs, tuple):
            raise MCPConfigurationError("env_refs must be a tuple")
        normalized_refs: list[tuple[str, str]] = []
        seen_children: set[str] = set()
        for pair in self.env_refs:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise MCPConfigurationError("each env_refs entry must be a (child, source) tuple")
            child, source = pair
            if not isinstance(child, str) or not _ENV_RE.fullmatch(child):
                raise MCPConfigurationError(f"invalid child environment name: {child!r}")
            if not isinstance(source, str) or not _ENV_RE.fullmatch(source):
                raise MCPConfigurationError(f"invalid source environment name: {source!r}")
            if child in seen_children:
                raise MCPConfigurationError(f"duplicate child environment name: {child!r}")
            seen_children.add(child)
            normalized_refs.append((child, source))
        object.__setattr__(self, "env_refs", tuple(normalized_refs))
        if not isinstance(self.enabled, bool):
            raise MCPConfigurationError("enabled must be boolean")
        object.__setattr__(self, "startup_timeout_sec", _timeout(self.startup_timeout_sec, field_name="startup_timeout_sec"))
        object.__setattr__(self, "discovery_timeout_sec", _timeout(self.discovery_timeout_sec, field_name="discovery_timeout_sec"))
        object.__setattr__(self, "transport", _enum_value(self.transport, MCPTransport, field_name="transport"))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MCPProfile":
        if not isinstance(data, Mapping):
            raise MCPConfigurationError("MCP profile must be an object")
        _exact_keys(data, {"schema_version", "profile_id", "title", "transport", "command", "args", "cwd", "env_refs", "enabled", "startup_timeout_sec", "discovery_timeout_sec"}, context="MCP profile")
        raw_refs = data.get("env_refs", {})
        if not isinstance(raw_refs, Mapping):
            raise MCPConfigurationError("env_refs must be an object mapping child name to source env name")
        raw_args = data.get("args", [])
        if not isinstance(raw_args, list):
            raise MCPConfigurationError("args must be an array")
        return cls(
            schema_version=int(data.get("schema_version", MCP_CONFIG_SCHEMA_VERSION)),
            profile_id=data.get("profile_id"), title=data.get("title"),
            transport=data.get("transport", MCPTransport.STDIO.value), command=data.get("command"),
            args=tuple(raw_args), cwd=data.get("cwd"),
            env_refs=tuple((str(key), value) for key, value in raw_refs.items()),
            enabled=data.get("enabled", True), startup_timeout_sec=data.get("startup_timeout_sec", 10.0),
            discovery_timeout_sec=data.get("discovery_timeout_sec", 15.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "profile_id": self.profile_id, "title": self.title,
            "transport": self.transport.value, "command": self.command, "args": list(self.args), "cwd": self.cwd,
            "env_refs": {child: source for child, source in self.env_refs}, "enabled": self.enabled,
            "startup_timeout_sec": self.startup_timeout_sec, "discovery_timeout_sec": self.discovery_timeout_sec,
        }


@dataclass(frozen=True)
class MCPProjectFileInput:
    """One explicit top-level MCP argument that UV Studio may resolve from project storage."""

    argument_name: str
    allowed_roots: tuple[str, ...]
    required: bool = True
    schema_version: int = MCP_PROJECT_FILE_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MCP_PROJECT_FILE_INPUT_SCHEMA_VERSION:
            raise MCPConfigurationError(
                f"MCPProjectFileInput only supports schema v{MCP_PROJECT_FILE_INPUT_SCHEMA_VERSION}"
            )
        object.__setattr__(self, "argument_name", _clean_text(self.argument_name, field_name="argument_name", max_length=256))
        if not isinstance(self.allowed_roots, tuple) or not self.allowed_roots:
            raise MCPConfigurationError("allowed_roots must be a non-empty tuple")
        roots = tuple(_clean_text(root, field_name="allowed_root", max_length=64) for root in self.allowed_roots)
        if len(set(roots)) != len(roots):
            raise MCPConfigurationError("allowed_roots contains duplicates")
        unknown = set(roots).difference(MCP_PROJECT_FILE_ALLOWED_ROOTS)
        if unknown:
            raise MCPConfigurationError(
                f"unsupported project-file roots: {sorted(unknown)!r}; allowed roots are {sorted(MCP_PROJECT_FILE_ALLOWED_ROOTS)!r}"
            )
        object.__setattr__(self, "allowed_roots", roots)
        if not isinstance(self.required, bool):
            raise MCPConfigurationError("required must be boolean")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MCPProjectFileInput":
        if not isinstance(data, Mapping):
            raise MCPConfigurationError("project_file_input must be an object")
        _exact_keys(data, {"schema_version", "argument_name", "allowed_roots", "required"}, context="project_file_input")
        roots = data.get("allowed_roots", [])
        if not isinstance(roots, list):
            raise MCPConfigurationError("project_file_input.allowed_roots must be an array")
        return cls(
            schema_version=int(data.get("schema_version", MCP_PROJECT_FILE_INPUT_SCHEMA_VERSION)),
            argument_name=data.get("argument_name"), allowed_roots=tuple(roots), required=data.get("required", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "argument_name": self.argument_name,
            "allowed_roots": list(self.allowed_roots),
            "required": self.required,
        }


@dataclass(frozen=True)
class MCPToolBinding:
    binding_id: str
    profile_id: str
    tool_name: str
    capability_id: str
    title: str
    locality: LocalityClass
    cost_class: CostClass
    asynchronous: bool
    features: tuple[str, ...] = ()
    project_file_inputs: tuple[MCPProjectFileInput, ...] = ()
    schema_version: int = MCP_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MCP_CONFIG_SCHEMA_VERSION:
            raise MCPConfigurationError(f"MCPToolBinding only supports schema v{MCP_CONFIG_SCHEMA_VERSION}")
        object.__setattr__(self, "binding_id", validate_capability_id(self.binding_id, field_name="binding_id"))
        object.__setattr__(self, "profile_id", validate_capability_id(self.profile_id, field_name="profile_id"))
        object.__setattr__(self, "tool_name", _clean_text(self.tool_name, field_name="tool_name", max_length=256))
        object.__setattr__(self, "capability_id", validate_capability_id(self.capability_id, field_name="capability_id"))
        object.__setattr__(self, "title", _clean_text(self.title, field_name="title", max_length=200))
        object.__setattr__(self, "locality", _enum_value(self.locality, LocalityClass, field_name="locality"))
        object.__setattr__(self, "cost_class", _enum_value(self.cost_class, CostClass, field_name="cost_class"))
        if not isinstance(self.asynchronous, bool):
            raise MCPConfigurationError("asynchronous must be boolean")
        if not isinstance(self.features, tuple):
            raise MCPConfigurationError("features must be a tuple")
        normalized_features = tuple(validate_capability_id(value, field_name="feature") for value in self.features)
        if len(set(normalized_features)) != len(normalized_features):
            raise MCPConfigurationError("features contains duplicates")
        object.__setattr__(self, "features", normalized_features)
        if not isinstance(self.project_file_inputs, tuple):
            raise MCPConfigurationError("project_file_inputs must be a tuple")
        if any(not isinstance(item, MCPProjectFileInput) for item in self.project_file_inputs):
            raise MCPConfigurationError("project_file_inputs must contain MCPProjectFileInput values")
        names = [item.argument_name for item in self.project_file_inputs]
        if len(set(names)) != len(names):
            raise MCPConfigurationError("project_file_inputs contains duplicate argument_name values")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MCPToolBinding":
        if not isinstance(data, Mapping):
            raise MCPConfigurationError("MCP binding must be an object")
        _exact_keys(data, {"schema_version", "binding_id", "profile_id", "tool_name", "capability_id", "title", "locality", "cost_class", "asynchronous", "features", "project_file_inputs"}, context="MCP binding")
        raw_features = data.get("features", [])
        raw_file_inputs = data.get("project_file_inputs", [])
        if not isinstance(raw_features, list):
            raise MCPConfigurationError("features must be an array")
        if not isinstance(raw_file_inputs, list):
            raise MCPConfigurationError("project_file_inputs must be an array")
        return cls(
            schema_version=int(data.get("schema_version", MCP_CONFIG_SCHEMA_VERSION)),
            binding_id=data.get("binding_id"), profile_id=data.get("profile_id"), tool_name=data.get("tool_name"),
            capability_id=data.get("capability_id"), title=data.get("title"), locality=data.get("locality"),
            cost_class=data.get("cost_class"), asynchronous=data.get("asynchronous", True),
            features=tuple(raw_features),
            project_file_inputs=tuple(MCPProjectFileInput.from_dict(item) for item in raw_file_inputs),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "binding_id": self.binding_id, "profile_id": self.profile_id,
            "tool_name": self.tool_name, "capability_id": self.capability_id, "title": self.title,
            "locality": self.locality.value, "cost_class": self.cost_class.value,
            "asynchronous": self.asynchronous, "features": list(self.features),
            "project_file_inputs": [item.to_dict() for item in self.project_file_inputs],
        }


@dataclass(frozen=True)
class MCPConfiguration:
    profiles: tuple[MCPProfile, ...] = ()
    bindings: tuple[MCPToolBinding, ...] = ()
    schema_version: int = MCP_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MCP_CONFIG_SCHEMA_VERSION:
            raise MCPConfigurationError(f"MCPConfiguration only supports schema v{MCP_CONFIG_SCHEMA_VERSION}")
        profile_ids = [profile.profile_id for profile in self.profiles]
        if len(set(profile_ids)) != len(profile_ids):
            raise MCPConfigurationError("duplicate MCP profile_id")
        binding_ids = [binding.binding_id for binding in self.bindings]
        if len(set(binding_ids)) != len(binding_ids):
            raise MCPConfigurationError("duplicate MCP binding_id")
        known_profiles = set(profile_ids)
        for binding in self.bindings:
            if binding.profile_id not in known_profiles:
                raise MCPConfigurationError(
                    f"binding {binding.binding_id!r} references unknown profile {binding.profile_id!r}"
                )

    @classmethod
    def empty(cls) -> "MCPConfiguration":
        return cls()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MCPConfiguration":
        if not isinstance(data, Mapping):
            raise MCPConfigurationError("MCP configuration must be an object")
        _exact_keys(data, {"schema_version", "profiles", "bindings"}, context="MCP configuration")
        profiles = data.get("profiles", [])
        bindings = data.get("bindings", [])
        if not isinstance(profiles, list) or not isinstance(bindings, list):
            raise MCPConfigurationError("profiles and bindings must be arrays")
        return cls(
            schema_version=int(data.get("schema_version", MCP_CONFIG_SCHEMA_VERSION)),
            profiles=tuple(MCPProfile.from_dict(item) for item in profiles),
            bindings=tuple(MCPToolBinding.from_dict(item) for item in bindings),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profiles": [profile.to_dict() for profile in self.profiles],
            "bindings": [binding.to_dict() for binding in self.bindings],
        }

    def get_profile(self, profile_id: str) -> MCPProfile:
        normalized = validate_capability_id(profile_id, field_name="profile_id")
        for profile in self.profiles:
            if profile.profile_id == normalized:
                return profile
        raise KeyError(normalized)

    def bindings_for(self, profile_id: str) -> tuple[MCPToolBinding, ...]:
        normalized = validate_capability_id(profile_id, field_name="profile_id")
        return tuple(binding for binding in self.bindings if binding.profile_id == normalized)


@dataclass(frozen=True)
class MCPToolDescriptor:
    name: str
    title: str | None
    description: str | None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_text(self.name, field_name="tool name", max_length=256))
        if self.title is not None:
            object.__setattr__(self, "title", _clean_text(self.title, field_name="tool title", max_length=500))
        if self.description is not None:
            object.__setattr__(self, "description", _clean_text(self.description, field_name="tool description", max_length=8000))
        object.__setattr__(self, "input_schema", _schema(self.input_schema, field_name="input_schema") or {})
        object.__setattr__(self, "output_schema", _schema(self.output_schema, field_name="output_schema"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "title": self.title, "description": self.description,
            "input_schema": dict(self.input_schema),
            "output_schema": None if self.output_schema is None else dict(self.output_schema),
        }


@dataclass(frozen=True)
class MCPProfileStatus:
    profile_id: str
    state: MCPRuntimeState
    reason: str
    tool_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id, "state": self.state.value,
            "reason": self.reason, "tool_count": self.tool_count,
        }


MAX_MCP_DISCOVERED_TOOLS = _MAX_TOOLS
