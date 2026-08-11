from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.mcp import get_mcp_config_store
from uv_studio.api.qwen_mm import get_qwen_platform
from uv_studio.mcp.store import MCPConfigStore
from uv_studio.server import app


class QwenMMPackApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MCPConfigStore(Path(self.tmp.name))
        app.dependency_overrides[get_mcp_config_store] = lambda: self.store
        app.dependency_overrides[get_qwen_platform] = lambda: "linux"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_catalog_is_pinned_secret_free_and_execution_is_conditional(self) -> None:
        os.environ["DASHSCOPE_API_KEY"] = "should-never-appear"
        try:
            response = self.client.get("/api/uv/integrations/qwen-mm")
            self.assertEqual(response.status_code, 200, response.text)
            packs = response.json()
            self.assertEqual([pack["pack_id"] for pack in packs], ["core", "api", "video-edit"])
            encoded = json.dumps(packs)
            self.assertNotIn("should-never-appear", encoded)
            self.assertNotIn(".git@main", encoded)
            for pack in packs:
                self.assertTrue(pack["tool_execution_enabled"])
                self.assertEqual(
                    pack["execution_policy"]["mode"],
                    "generic_mcp_after_discovery_and_authorization",
                )
                self.assertFalse(pack["execution_policy"]["automatic"])
                self.assertTrue(pack["execution_policy"]["requires_ready_discovery"])
                self.assertTrue(pack["execution_policy"]["authorization_enforced"])
        finally:
            os.environ.pop("DASHSCOPE_API_KEY", None)

    def test_configure_core_writes_known_profile_and_media_info_file_contract(self) -> None:
        response = self.client.post("/api/uv/integrations/qwen-mm/core/configure")
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["configured_profile_id"], "qwen-mm-core")
        self.assertIn("exact READY bindings", payload["next_action"])
        config = self.store.load()
        self.assertEqual([profile.profile_id for profile in config.profiles], ["qwen-mm-core"])
        self.assertEqual([binding.tool_name for binding in config.bindings], ["media_info"])
        binding = config.bindings[0]
        self.assertEqual(len(binding.project_file_inputs), 1)
        file_input = binding.project_file_inputs[0]
        self.assertEqual(file_input.argument_name, "path")
        self.assertEqual(
            file_input.allowed_roots,
            ("sources", "assets", "artifacts", "exports"),
        )
        self.assertTrue(file_input.required)

    def test_cloud_bindings_do_not_gain_unverified_file_contracts(self) -> None:
        response = self.client.post("/api/uv/integrations/qwen-mm/video-edit/configure")
        self.assertEqual(response.status_code, 201, response.text)
        config = self.store.load()
        self.assertTrue(config.bindings)
        self.assertTrue(all(binding.project_file_inputs == () for binding in config.bindings))

    def test_configure_cloud_pack_stores_key_reference_not_value(self) -> None:
        os.environ["DASHSCOPE_API_KEY"] = "never-write-this"
        try:
            response = self.client.post("/api/uv/integrations/qwen-mm/video-edit/configure")
            self.assertEqual(response.status_code, 201, response.text)
            raw = self.store.path.read_text(encoding="utf-8")
            self.assertIn("DASHSCOPE_API_KEY", raw)
            self.assertNotIn("never-write-this", raw)
            next_action = response.json()["next_action"]
            self.assertIn("READY", next_action)
            self.assertIn("execution authorization", next_action)
        finally:
            os.environ.pop("DASHSCOPE_API_KEY", None)

    def test_native_windows_is_explicitly_unsupported_for_current_upstream(self) -> None:
        app.dependency_overrides[get_qwen_platform] = lambda: "win32"
        response = self.client.post("/api/uv/integrations/qwen-mm/core/configure")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("WSL2", response.json()["detail"])
        self.assertFalse(self.store.path.exists())

    def test_unknown_pack_is_404(self) -> None:
        self.assertEqual(
            self.client.get("/api/uv/integrations/qwen-mm/missing").status_code,
            404,
        )
        self.assertEqual(
            self.client.post("/api/uv/integrations/qwen-mm/missing/configure").status_code,
            404,
        )

    def test_no_generic_command_payload_is_accepted(self) -> None:
        response = self.client.post(
            "/api/uv/integrations/qwen-mm/core/configure",
            json={"command": "powershell", "args": ["arbitrary"]},
        )
        # The endpoint has no request-body contract at all; arbitrary data is ignored by
        # FastAPI for this trusted static action, and the persisted command must remain pinned.
        self.assertEqual(response.status_code, 201, response.text)
        profile = self.store.load().get_profile("qwen-mm-core")
        self.assertEqual(profile.command, "uvx")
        self.assertNotIn("powershell", " ".join(profile.args))


if __name__ == "__main__":
    unittest.main()
