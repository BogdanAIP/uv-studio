from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from uv_studio.diagnostics import DIAGNOSTICS_SCHEMA_VERSION
from uv_studio.server import app


class DiagnosticsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_diagnostics_are_secret_safe_and_available_without_packaged_release(self) -> None:
        with mock.patch.dict(os.environ, {"UV_STUDIO_RELEASE_ROOT": ""}, clear=False):
            response = self.client.get("/api/uv/diagnostics")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["schema_version"], DIAGNOSTICS_SCHEMA_VERSION)
        self.assertEqual(payload["mode"], "development")
        self.assertIn(payload["overall_status"], {"ok", "degraded"})
        self.assertFalse(payload["release"]["configured"])
        self.assertFalse(payload["storage"]["probe_performed"])
        self.assertFalse(payload["recovery"]["checked"])
        self.assertIn("logical_cpu_count", payload["resources"])
        self.assertIn("total_bytes", payload["resources"]["memory"])
        self.assertIn("available_bytes", payload["resources"]["memory"])
        encoded = json.dumps(payload, sort_keys=True).lower()
        for forbidden in (
            "api_key",
            "bearer ",
            "secret_status",
            "secret_updates",
            "hostname",
            "username",
            "processes",
            "environment",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_deep_release_query_is_safe_in_development_mode(self) -> None:
        with mock.patch.dict(os.environ, {"UV_STUDIO_RELEASE_ROOT": ""}, clear=False):
            response = self.client.get("/api/uv/diagnostics?verify_release=true")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["mode"], "development")
        self.assertIsNone(payload["release"]["integrity"])

    def test_storage_probe_is_available_over_http_without_exposing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private_user_data = root / "private-user-data"
            environment = {
                "UV_STUDIO_RELEASE_ROOT": "",
                "UV_STUDIO_USER_DATA_DIR": str(private_user_data),
                "UV_STUDIO_PROJECTS_DIR": str(root / "private-projects"),
                "UV_STUDIO_CONFIG_DIR": str(root / "private-config"),
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                response = self.client.get("/api/uv/diagnostics?probe_storage=true")

            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["schema_version"], DIAGNOSTICS_SCHEMA_VERSION)
            self.assertTrue(payload["storage"]["probe_performed"])
            self.assertTrue(payload["recovery"]["checked"])
            for key in ("user_data", "project_store", "configuration"):
                self.assertTrue(payload["storage"][key]["writable"])
            self.assertEqual(list(root.rglob(".uv-diagnostics-*.tmp")), [])

            encoded = json.dumps(payload, sort_keys=True)
            self.assertNotIn(str(root), encoded)
            self.assertNotIn("private-user-data", encoded)
            self.assertNotIn("private-projects", encoded)
            self.assertNotIn("private-config", encoded)


if __name__ == "__main__":
    unittest.main()
