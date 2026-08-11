"""MCP discovery lifecycle, explicit binding synchronization and invocation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

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


class MCPBindingNotFound(MCPManagerError):
    pass


class MCPBindingMismatch(MCPManagerError):
    pass


@dataclass(frozen=True)
class MCPDiscoverySnapshot:
    profile_id: str
    tools: tuple[MCPToolDescriptor, ...]


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
            self._set_status(profile, MCPRuntimeState.FAILED, "profile is disabled", tool_count=0)
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

        snapshot = MCPDiscoverySnapshot(profile.profile_id, tools)
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

    def resolve_offer_binding(self, offer: CapabilityOffer) -> tuple[MCPProfile, MCPToolBinding]:
        if not offer.offer_id.startswith("mcp.") or not offer.adapter_id.startswith("mcp."):
            raise MCPBindingMismatch(f"offer {offer.offer_id!r} is not an MCP offer")
        binding_id = offer.offer_id[len("mcp.") :]
        config = self.configuration()
        try:
            binding = config.get_binding(binding_id)
            profile = config.get_profile(binding.profile_id)
        except KeyError as exc:
            raise MCPBindingNotFound(binding_id) from exc
        expected_adapter = f"mcp.{binding.profile_id}"
        if offer.adapter_id != expected_adapter:
            raise MCPBindingMismatch(
                f"offer adapter {offer.adapter_id!r} does not match binding profile {binding.profile_id!r}"
            )
        if offer.capability_id != binding.capability_id:
            raise MCPBindingMismatch(
                f"offer capability {offer.capability_id!r} does not match binding {binding.capability_id!r}"
            )
        return profile, binding

    async def invoke_offer(
        self,
        offer: CapabilityOffer,
        arguments: Mapping[str, Any],
        *,
        timeout_sec: float = 30.0,
        max_response_bytes: int = 1024 * 1024,
    ) -> tuple[MCPToolBinding, dict[str, Any]]:
        profile, binding = self.resolve_offer_binding(offer)
        status = self.status(profile.profile_id)
        snapshot = self._snapshots.get(profile.profile_id)
        if status.state is not MCPRuntimeState.READY or snapshot is None:
            raise MCPProfileNotReady(
                f"MCP profile {profile.profile_id!r} must complete discovery before execution"
            )
        if binding.tool_name not in {tool.name for tool in snapshot.tools}:
            raise MCPBindingMismatch(
                f"bound tool {binding.tool_name!r} is not present in the latest discovery snapshot"
            )
        result = await self.discovery_client.invoke(
            profile,
            tool_name=binding.tool_name,
            arguments=arguments,
            timeout_sec=timeout_sec,
            max_response_bytes=max_response_bytes,
        )
        return binding, result

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
