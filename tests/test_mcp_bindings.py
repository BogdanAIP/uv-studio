from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities import (
    CostClass,
    LocalityClass,
    NoEligibleOffer,
    OfferAvailability,
    build_builtin_capability_registry,
    select_offer,
)
from uv_studio.capabilities.registry import UnknownOffer
from uv_studio.mcp.manager import MCPManager
from uv_studio.mcp.models import (
    MCPConfiguration,
    MCPProfile,
    MCPToolBinding,
    MCPToolDescriptor,
)
from uv_studio.mcp.store import MCPConfigStore


class FakeDiscoveryClient:
    def __init__(self, tools):
        self.tools = tuple(tools)
        self.calls = []

    async def discover(self, profile):
        self.calls.append(profile.profile_id)
        return self.tools


class MCPBindingTests(unittest.TestCase):
    def _manager(self, bindings):
        tmp = tempfile.TemporaryDirectory()
        store = MCPConfigStore(Path(tmp.name))
        profile = MCPProfile(
            profile_id="fixture",
            title="Fixture",
            command="python",
        )
        store.save(MCPConfiguration(profiles=(profile,), bindings=tuple(bindings)))
        registry = build_builtin_capability_registry()
        discovery = FakeDiscoveryClient(
            (
                MCPToolDescriptor(
                    name="echo_metadata",
                    title="Echo",
                    description="Local metadata tool",
                    input_schema={"type": "object"},
                ),
                MCPToolDescriptor(
                    name="cloud_generate",
                    title="Cloud",
                    description="Remote generation tool",
                    input_schema={"type": "object"},
                ),
            )
        )
        return tmp, registry, MCPManager(store, registry, discovery_client=discovery)

    def test_discovered_unbound_tool_does_not_become_offer(self) -> None:
        binding = MCPToolBinding(
            binding_id="fixture.echo",
            profile_id="fixture",
            tool_name="echo_metadata",
            capability_id="media.understand",
            title="Fixture echo",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
        )
        tmp, registry, manager = self._manager((binding,))
        try:
            asyncio.run(manager.connect("fixture"))
            offer = registry.get_offer("mcp.fixture.echo")
            self.assertEqual(offer.availability, OfferAvailability.AVAILABLE)
            self.assertEqual(offer.cost_class, CostClass.FREE)
            with self.assertRaises(UnknownOffer):
                registry.get_offer("mcp.fixture.cloud")
        finally:
            tmp.cleanup()

    def test_remote_paid_capable_binding_preserves_cost_and_cannot_be_local_free_fallback(self) -> None:
        binding = MCPToolBinding(
            binding_id="fixture.cloud",
            profile_id="fixture",
            tool_name="cloud_generate",
            capability_id="video.generate",
            title="Fixture cloud video",
            locality=LocalityClass.REMOTE,
            cost_class=CostClass.POTENTIALLY_PAID,
            asynchronous=True,
        )
        tmp, registry, manager = self._manager((binding,))
        try:
            asyncio.run(manager.connect("fixture"))
            offer = registry.get_offer("mcp.fixture.cloud")
            self.assertEqual(offer.availability, OfferAvailability.AVAILABLE)
            self.assertEqual(offer.locality, LocalityClass.REMOTE)
            self.assertEqual(offer.cost_class, CostClass.POTENTIALLY_PAID)
            with self.assertRaises(NoEligibleOffer):
                select_offer(registry, "video.generate", policy="local_free_first")
        finally:
            tmp.cleanup()

    def test_disconnect_marks_bound_offer_unavailable(self) -> None:
        binding = MCPToolBinding(
            binding_id="fixture.echo",
            profile_id="fixture",
            tool_name="echo_metadata",
            capability_id="media.understand",
            title="Fixture echo",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
        )
        tmp, registry, manager = self._manager((binding,))

        async def scenario():
            await manager.connect("fixture")
            self.assertEqual(
                registry.get_offer("mcp.fixture.echo").availability,
                OfferAvailability.AVAILABLE,
            )
            status = await manager.disconnect("fixture")
            self.assertEqual(status.state.value, "stopped")
            self.assertEqual(
                registry.get_offer("mcp.fixture.echo").availability,
                OfferAvailability.UNAVAILABLE,
            )

        try:
            asyncio.run(scenario())
        finally:
            tmp.cleanup()

    def test_missing_bound_tool_creates_unavailable_offer(self) -> None:
        binding = MCPToolBinding(
            binding_id="fixture.missing",
            profile_id="fixture",
            tool_name="not_reported",
            capability_id="media.understand",
            title="Missing tool",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
        )
        tmp, registry, manager = self._manager((binding,))
        try:
            asyncio.run(manager.connect("fixture"))
            offer = registry.get_offer("mcp.fixture.missing")
            self.assertEqual(offer.availability, OfferAvailability.UNAVAILABLE)
            self.assertIn("not reported", offer.reason)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
