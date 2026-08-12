from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.configuration import get_runtime_config_store
from uv_studio.runtime_config import RuntimeConfigStore
from uv_studio.server import app


class RuntimeSecurityApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.store = RuntimeConfigStore(
            config_path=root / "runtime.json",
            secrets_path=root / "secrets.json",
        )
        app.dependency_overrides[get_runtime_config_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.pop(get_runtime_config_store, None)
        self.tempdir.cleanup()

    def test_config_read_never_emits_raw_provider_secret(self) -> None:
        secret = "raw-provider-secret-must-not-leak"
        response = self.client.put(
            "/api/config",
            json={
                "values": {"generation": {"video_resolution": "1080P"}},
                "secret_updates": {"api_providers.openai.api_key": secret},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(secret, response.text)
        self.assertNotIn("api_key\"", str(response.json()["config"]))
        self.assertTrue(response.json()["secrets"]["api_providers.openai.api_key"])

        read = self.client.get("/api/config")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertNotIn(secret, read.text)
        self.assertEqual(read.json()["path"], "data/config/runtime.json")
        self.assertFalse(Path(read.json()["path"]).is_absolute())

    def test_secret_can_be_replaced_without_round_tripping_old_value(self) -> None:
        path = "api_providers.openai.api_key"
        first = self.client.put(
            "/api/config",
            json={"secret_updates": {path: "first-secret"}},
        )
        self.assertEqual(first.status_code, 200, first.text)

        second = self.client.put(
            "/api/config",
            json={"secret_updates": {path: "second-secret"}},
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertNotIn("first-secret", second.text)
        self.assertNotIn("second-secret", second.text)
        self.assertEqual(self.store.secret_value(path), "second-secret")

    def test_secret_clear_is_explicit_null(self) -> None:
        path = "api_providers.openai.api_key"
        self.store.update(secret_updates={path: "configured-secret"})
        response = self.client.put(
            "/api/config",
            json={"secret_updates": {path: None}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["secrets"][path])
        self.assertIsNone(self.store.secret_value(path))

    def test_public_config_cannot_accept_secret_field(self) -> None:
        response = self.client.put(
            "/api/config",
            json={"values": {"api_providers": {"openai": {"api_key": "forbidden"}}}},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertNotIn("forbidden", response.text)

    def test_untrusted_browser_origin_is_not_granted_cors_access(self) -> None:
        response = self.client.options(
            "/api/config",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "https://evil.example")

    def test_intended_local_frontend_origin_is_granted_cors_access(self) -> None:
        origin = "http://127.0.0.1:3000"
        response = self.client.options(
            "/api/config",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)

    def test_legacy_remote_execution_routes_are_not_mounted(self) -> None:
        blocked = (
            ("/api/sandbox/llm", {"prompt": "must not execute", "model": "any"}),
            ("/api/pipelines/standard/tasks", {}),
            ("/api/project/fake/execute/video_generation", {}),
        )
        for path, payload in blocked:
            with self.subTest(path=path):
                response = self.client.post(path, json=payload)
                self.assertEqual(response.status_code, 404, response.text)

    def test_uv_studio_capability_catalog_remains_available(self) -> None:
        response = self.client.get("/api/uv/capabilities")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(any(item["capability_id"] == "timeline.assemble" for item in response.json()))

    def test_health_is_uv_studio_owned(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"status": "ok", "service": "uv-studio"})


if __name__ == "__main__":
    unittest.main()
