from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

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
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["mode"], "development")
        self.assertIn(payload["overall_status"], {"ok", "degraded"})
        self.assertFalse(payload["release"]["configured"])
        encoded = json.dumps(payload, sort_keys=True).lower()
        for forbidden in ("api_key", "bearer ", "secret_status", "secret_updates"):
            self.assertNotIn(forbidden, encoded)

    def test_deep_release_query_is_safe_in_development_mode(self) -> None:
        with mock.patch.dict(os.environ, {"UV_STUDIO_RELEASE_ROOT": ""}, clear=False):
            response = self.client.get("/api/uv/diagnostics?verify_release=true")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["mode"], "development")
        self.assertIsNone(payload["release"]["integrity"])


if __name__ == "__main__":
    unittest.main()
