from __future__ import annotations

import asyncio
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from uv_studio.capabilities import (
    CostClass,
    LocalityClass,
    build_builtin_capability_registry,
)
from uv_studio.mcp.manager import MCPBindingExecutionRejected, MCPManager
from uv_studio.mcp.models import (
    MCPConfiguration,
    MCPConfigurationError,
    MCPProfile,
    MCPProjectFileInput,
    MCPToolBinding,
    MCPToolDescriptor,
)
from uv_studio.mcp.store import MCPConfigStore


class FakeDiscoveryClient:
    async def discover(self, profile):
        return (
            MCPToolDescriptor(
                name="read_project_file",
                title="Read project file",
                description="Fixture",
                input_schema={"type": "object"},
            ),
        )


class MCPProjectFileContractTests(unittest.TestCase):
    def test_old_binding_payload_remains_backward_compatible(self) -> None:
        binding = MCPToolBinding.from_dict(
            {
                "schema_version": 1,
                "binding_id": "fixture.old",
                "profile_id": "fixture",
                "tool_name": "read_project_file",
                "capability_id": "media.understand",
                "title": "Old binding",
                "locality": "local",
                "cost_class": "free",
                "asynchronous": False,
                "features": [],
            }
        )
        self.assertEqual(binding.project_file_inputs, ())
        self.assertEqual(binding.to_dict()["project_file_inputs"], [])

    def test_file_contract_round_trips(self) -> None:
        binding = self._binding(
            MCPProjectFileInput(
                argument_name="path",
                allowed_roots=("sources", "assets"),
                required=True,
            )
        )
        restored = MCPToolBinding.from_dict(binding.to_dict())
        self.assertEqual(restored, binding)
        self.assertEqual(restored.project_file_inputs[0].argument_name, "path")
        self.assertEqual(restored.project_file_inputs[0].allowed_roots, ("sources", "assets"))

    def test_internal_project_roots_are_not_exposable(self) -> None:
        for root in ("tasks", "timeline", "reviews"):
            with self.subTest(root=root), self.assertRaises(MCPConfigurationError):
                MCPProjectFileInput(argument_name="path", allowed_roots=(root,))

    def test_duplicate_file_argument_contract_is_rejected(self) -> None:
        spec = MCPProjectFileInput(argument_name="path", allowed_roots=("sources",))
        with self.assertRaises(MCPConfigurationError):
            MCPToolBinding(
                binding_id="fixture.duplicate",
                profile_id="fixture",
                tool_name="read_project_file",
                capability_id="media.understand",
                title="Duplicate",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=False,
                project_file_inputs=(spec, spec),
            )

    def test_file_contract_change_invalidates_ready_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_store = MCPConfigStore(Path(tmp))
            profile = MCPProfile(profile_id="fixture", title="Fixture", command="python")
            binding = self._binding(
                MCPProjectFileInput(argument_name="path", allowed_roots=("sources",))
            )
            config_store.save(MCPConfiguration(profiles=(profile,), bindings=(binding,)))
            registry = build_builtin_capability_registry()
            manager = MCPManager(config_store, registry, discovery_client=FakeDiscoveryClient())
            asyncio.run(manager.connect("fixture"))
            offer = registry.get_offer("mcp.fixture.file")

            changed = replace(
                binding,
                project_file_inputs=(
                    MCPProjectFileInput(argument_name="path", allowed_roots=("assets",)),
                ),
            )
            config_store.save(MCPConfiguration(profiles=(profile,), bindings=(changed,)))

            with self.assertRaises(MCPBindingExecutionRejected) as caught:
                manager.resolve_execution_target(offer)
            self.assertIn("reconnect", str(caught.exception))

    @staticmethod
    def _binding(spec: MCPProjectFileInput) -> MCPToolBinding:
        return MCPToolBinding(
            binding_id="fixture.file",
            profile_id="fixture",
            tool_name="read_project_file",
            capability_id="media.understand",
            title="Fixture file",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            project_file_inputs=(spec,),
        )


if __name__ == "__main__":
    unittest.main()
