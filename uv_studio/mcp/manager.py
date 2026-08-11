"""MCP discovery lifecycle, exact binding resolution and invocation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from uv_studio.capabilities.adapters.mcp import MCPBindingOfferAdapter
from uv_studio.capabilities.models import CapabilityOffer
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability

from .client import (
    MCPDiscoveryError,
    MCPDiscoveryTimeout,
    MCPMissingEnvironment,
    MCPStdioDiscoveryClient,
)
from .models import (
    MCPConfigurationError,
    MCPProfile,
    MCPProfileStatus,
    MCPRuntimeState,
    MCPToolBinding,
    MCPToolDescriptor,
)
from .store import MCPConfigStore


class MCPManagerError(RuntimeError):
    pass


class MCPProfileNotFound(MCPManagerError):
    pass


class MCPProfileDisabled(MCPManagerError):
    pass


class MCPProfileNotReady(MCPManagerError):
    pass


class MCPBindingExecutionRejected(MCPManagerError):
    """Selected MCP offer no longer resolves to the exact READY binding snapshot."""


@dataclass(frozen=True)
class MCPDiscoverySnapshot:
    profile_id: str
    tools: tuple[MCPToolDescriptor, ...]
    configuration_digest: str


@dataclass(frozen=True)
class MCPExecutionTarget:
    profile: MCPProfile
    binding: MCPToolBinding
    tool: MCPToolDescriptor


class MCPManager:
    def __init__(
        self,
        config_store: MCPConfigStore,
        registry: CapabilityRegistry,
        *,
        discovery_client: MCPStdioDiscoveryClient | None = None,
    ) -> None:
        self.config_store = config_store
        self.registry = registry
        self.discovery_client = discovery_client or MCPStdioDiscoveryClient(config_store)
        self._statuses: dict[str, MCPProfileStatus] = {}
        self._snapshots: dict[str, MCPDiscoverySnapshot] = {}

    def configuration(self):
        return self.config_store.load()

    def profiles(self) -> tuple[MCPProfile, ...]:
        return self.configuration().profiles

    def bindings(self):
        return self.configuration().bindings

    def status(self, profile_id: str) -> MCPProfileStatus:
        profile = self._get_profile(profile_id)
        existing = self._statuses.get(profile.profile_id)
        if existing is not None:
            return existing
        return MCPProfileStatus(
            profile_id=profile.profile_id,
            state=MCPRuntimeState.CONFIGURED,
            reason="profile configured; discovery has not run",
            tool_count=0,
        )

    def tools(self, profile_id: str) -> tuple[MCPToolDescriptor, ...]:
        profile = self._get_profile(profile_id)
        status = self.status(profile.profile_id)
        snapshot = self._snapshots.get(profile.profile_id)
        if status.state is not MCPRuntimeState.READY or snapshot is None:
            raise MCPProfileNotReady(
                f"MCP profile {profile.profile_id!r} has no ready discovery snapshot"
            )
        return snapshot.tools

    async def connect(self, profile_id: str) -> MCPProfileStatus:
        config = self.configuration()
        profile = self._get_profile(profile_id, config=config)
        if not profile.enabled:
            self._set_status(
                profile,
                MCPRuntimeState.FAILED,
                "profile is disabled",
                tool_count=0,
            )
            self._synchronize(profile, config, (), ready=False, reason="profile is disabled")
            raise MCPProfileDisabled(profile.profile_id)

        self._set_status(
            profile,
            MCPRuntimeState.DISCOVERING,
            "bounded MCP tool discovery in progress",
            tool_count=0,
        )
        try:
            tools = await self.discovery_client.discover(profile)
            self._validate_bindings(config, profile)
        except (MCPDiscoveryTimeout, MCPMissingEnvironment, MCPDiscoveryError, MCPConfigurationError) as exc:
            reason = str(exc)
            self._snapshots.pop(profile.profile_id, None)
            self._set_status(profile, MCPRuntimeState.FAILED, reason, tool_count=0)
            self._synchronize(profile, config, (), ready=False, reason=reason)
            raise
        except Exception as exc:
            reason = f"MCP discovery failed ({type(exc).__name__})"
            self._snapshots.pop(profile.profile_id, None)
            self._set_status(profile, MCPRuntimeState.FAILED, reason, tool_count=0)
            self._synchronize(profile, config, (), ready=False, reason=reason)
            raise MCPManagerError(reason) from exc

        snapshot = MCPDiscoverySnapshot(
            profile.profile_id,
            tools,
            self._configuration_digest(profile, config.bindings_for(profile.profile_id)),
        )
        self._snapshots[profile.profile_id] = snapshot
        status = self._set_status(
            profile,
            MCPRuntimeState.READY,
            "discovery succeeded; no MCP child process is kept resident",
            tool_count=len(tools),
        )
        self._synchronize(profile, config, tools, ready=True, reason=status.reason)
        return status

    async def disconnect(self, profile_id: str) -> MCPProfileStatus:
        config = self.configuration()
        profile = self._get_profile(profile_id, config=config)
        self._snapshots.pop(profile.profile_id, None)
        status = self._set_status(
            profile,
            MCPRuntimeState.STOPPED,
            "discovery snapshot cleared; no MCP child process is resident",
            tool_count=0,
        )
        self._synchronize(profile, config, (), ready=False, reason=status.reason)
        return status

    def resolve_execution_target(self, offer: CapabilityOffer) -> MCPExecutionTarget:
        """Resolve an MCP offer only against the exact unchanged READY binding snapshot."""
        config = self.configuration()
        matches = tuple(
            binding
            for binding in config.bindings
            if f"mcp.{binding.binding_id}" == offer.offer_id
        )
        if len(matches) != 1:
            raise MCPBindingExecutionRejected(
                f"MCP offer {offer.offer_id!r} does not resolve to exactly one configured binding"
            )
        binding = matches[0]
        try:
            profile = config.get_profile(binding.profile_id)
        except (KeyError, ValueError) as exc:
            raise MCPBindingExecutionRejected("MCP binding profile is no longer configured") from exc
        if not profile.enabled:
            raise MCPBindingExecutionRejected("MCP binding profile is disabled")

        expected_adapter = MCPBindingOfferAdapter.adapter_id(profile.profile_id)
        if offer.adapter_id != expected_adapter:
            raise MCPBindingExecutionRejected("MCP offer adapter no longer matches its binding profile")
        if binding.capability_id != offer.capability_id:
            raise MCPBindingExecutionRejected("MCP binding capability no longer matches selected offer")
        if (
            binding.locality is not offer.locality
            or binding.cost_class is not offer.cost_class
            or binding.asynchronous != offer.asynchronous
            or binding.features != offer.features
        ):
            raise MCPBindingExecutionRejected("MCP binding metadata changed after offer discovery")

        status = self._statuses.get(profile.profile_id)
        snapshot = self._snapshots.get(profile.profile_id)
        if status is None or status.state is not MCPRuntimeState.READY or snapshot is None:
            raise MCPBindingExecutionRejected("MCP profile has no READY discovery snapshot")

        current_digest = self._configuration_digest(
            profile,
            config.bindings_for(profile.profile_id),
        )
        if current_digest != snapshot.configuration_digest:
            raise MCPBindingExecutionRejected(
                "MCP profile or binding configuration changed; reconnect before execution"
            )

        exact = tuple(tool for tool in snapshot.tools if tool.name == binding.tool_name)
        if len(exact) != 1:
            raise MCPBindingExecutionRejected(
                f"bound MCP tool {binding.tool_name!r} is not present in the READY snapshot"
            )
        return MCPExecutionTarget(profile=profile, binding=binding, tool=exact[0])

    async def invoke_target(
        self,
        target: MCPExecutionTarget,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Invoke only an already-resolved exact target."""
        return await self.discovery_client.call_tool(
            target.profile,
            target.binding.tool_name,
            arguments,
        )

    def profile_payload(self, profile: MCPProfile) -> dict[str, object]:
        payload = profile.to_dict()
        payload["status"] = self.status(profile.profile_id).to_dict()
        return payload

    def _get_profile(self, profile_id: str, *, config=None) -> MCPProfile:
        config = config or self.configuration()
        try:
            return config.get_profile(profile_id)
        except (KeyError, ValueError) as exc:
            raise MCPProfileNotFound(profile_id) from exc

    def _set_status(
        self,
        profile: MCPProfile,
        state: MCPRuntimeState,
        reason: str,
        *,
        tool_count: int,
    ) -> MCPProfileStatus:
        status = MCPProfileStatus(
            profile_id=profile.profile_id,
            state=state,
            reason=reason,
            tool_count=tool_count,
        )
        self._statuses[profile.profile_id] = status
        return status

    def _validate_bindings(self, config, profile: MCPProfile) -> None:
        for binding in config.bindings_for(profile.profile_id):
            try:
                self.registry.get_capability(binding.capability_id)
            except UnknownCapability as exc:
                raise MCPConfigurationError(
                    f"binding {binding.binding_id!r} references unknown semantic capability "
                    f"{binding.capability_id!r}"
                ) from exc

    def _synchronize(
        self,
        profile: MCPProfile,
        config,
        tools,
        *,
        ready: bool,
        reason: str,
    ) -> None:
        bindings = config.bindings_for(profile.profile_id)
        if not bindings:
            return
        discovered = {tool.name for tool in tools}
        MCPBindingOfferAdapter.synchronize(
            self.registry,
            profile=profile,
            bindings=bindings,
            discovered_tool_names=discovered,
            ready=ready,
            state_reason=reason,
        )

    @staticmethod
    def _configuration_digest(
        profile: MCPProfile,
        bindings: tuple[MCPToolBinding, ...],
    ) -> str:
        payload = {
            "profile": profile.to_dict(),
            "bindings": [
                binding.to_dict()
                for binding in sorted(bindings, key=lambda item: item.binding_id)
            ],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
