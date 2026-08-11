from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities import CostClass, LocalityClass
from uv_studio.mcp.models import (
    MCPConfiguration,
    MCPConfigurationError,
    MCPProfile,
    MCPToolBinding,
)
from uv_studio.mcp.store import MCPConfigStore


class MCPModelTests(unittest.TestCase):
    def test_profile_stores_environment_references_not_values(self) -> None:
        profile = MCPProfile(
            profile_id="fixture",
            title="Fixture",
            command="python",
            args=("server.py",),
            env_refs=(("SERVER_TOKEN", "UV_TEST_SECRET"),),
        )
        payload = profile.to_dict()
        encoded = json.dumps(payload)
        self.assertEqual(payload["env_refs"], {"SERVER_TOKEN": "UV_TEST_SECRET"})
        self.assertNotIn("super-secret-value", encoded)

    def test_profile_from_dict_rejects_raw_environment_value_field(self) -> None:
        with self.assertRaises(MCPConfigurationError):
            MCPProfile.from_dict(
                {
                    "profile_id": "fixture",
                    "title": "Fixture",
                    "command": "python",
                    "env": {"TOKEN": "raw-secret"},
                }
            )

    def test_binding_must_reference_configured_profile(self) -> None:
        binding = MCPToolBinding(
            binding_id="fixture.echo",
            profile_id="missing",
            tool_name="echo_metadata",
            capability_id="media.understand",
            title="Fixture echo",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
        )
        with self.assertRaises(MCPConfigurationError):
            MCPConfiguration(bindings=(binding,))

    def test_store_missing_file_is_empty_and_round_trip_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MCPConfigStore(Path(tmp))
            self.assertEqual(store.load(), MCPConfiguration.empty())
            profile = MCPProfile(
                profile_id="fixture",
                title="Fixture",
                command="python",
                env_refs=(("TOKEN", "UV_TEST_SECRET"),),
            )
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
            config = MCPConfiguration(profiles=(profile,), bindings=(binding,))
            os.environ["UV_TEST_SECRET"] = "super-secret-value"
            try:
                store.save(config)
                raw = store.path.read_text(encoding="utf-8")
                self.assertNotIn("super-secret-value", raw)
                self.assertIn("UV_TEST_SECRET", raw)
                self.assertEqual(store.load(), config)
            finally:
                os.environ.pop("UV_TEST_SECRET", None)


if __name__ == "__main__":
    unittest.main()
