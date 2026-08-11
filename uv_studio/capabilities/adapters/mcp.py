"""Translate explicit MCP tool bindings into semantic CapabilityOffer metadata."""

from __future__ import annotations

from collections.abc import Iterable

from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityOffer,
    OfferAvailability,
)
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownAdapter
from uv_studio.mcp.models import MCPProfile, MCPToolBinding


class MCPBindingOfferAdapter:
    @staticmethod
    def adapter_id(profile_id: str) -> str:
        return f"mcp.{profile_id}"

    @classmethod
    def adapter_definition(cls, profile: MCPProfile) -> AdapterDefinition:
        return AdapterDefinition(
            cls.adapter_id(profile.profile_id),
            f"MCP: {profile.title}",
            "Explicitly configured MCP stdio capability package.",
            AdapterKind.MCP,
        )

    @classmethod
    def synchronize(
        cls,
        registry: CapabilityRegistry,
        *,
        profile: MCPProfile,
        bindings: Iterable[MCPToolBinding],
        discovered_tool_names: set[str],
        ready: bool,
        state_reason: str,
    ) -> tuple[CapabilityOffer, ...]:
        adapter = cls.adapter_definition(profile)
        registry.upsert_adapter(adapter)
        offers: list[CapabilityOffer] = []
        for binding in bindings:
            # Semantic capability must already exist in UV Studio. Discovery never
            # creates new domain capabilities from provider/tool names.
            registry.get_capability(binding.capability_id)
            tool_present = binding.tool_name in discovered_tool_names
            available = ready and tool_present and profile.enabled
            if available:
                reason = f"MCP tool {binding.tool_name!r} discovered in profile {profile.profile_id!r}."
            elif not profile.enabled:
                reason = f"MCP profile {profile.profile_id!r} is disabled."
            elif ready and not tool_present:
                reason = f"Bound MCP tool {binding.tool_name!r} was not reported by the server."
            else:
                reason = state_reason
            offer = CapabilityOffer(
                offer_id=f"mcp.{binding.binding_id}",
                capability_id=binding.capability_id,
                adapter_id=adapter.adapter_id,
                title=binding.title,
                availability=(
                    OfferAvailability.AVAILABLE if available else OfferAvailability.UNAVAILABLE
                ),
                reason=reason,
                locality=binding.locality,
                cost_class=binding.cost_class,
                asynchronous=binding.asynchronous,
                features=binding.features,
            )
            registry.upsert_offer(offer)
            offers.append(offer)
        return tuple(offers)
