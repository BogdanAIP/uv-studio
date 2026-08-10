from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "uv_dev.py"
SPEC = importlib.util.spec_from_file_location("uv_dev", MODULE_PATH)
assert SPEC and SPEC.loader
uv_dev = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = uv_dev
SPEC.loader.exec_module(uv_dev)


class LayoutTests(unittest.TestCase):
    def test_expected_paths_stay_under_repository_root(self) -> None:
        self.assertIn(uv_dev.VENDOR_APP, uv_dev.BACKEND.parents)
        self.assertIn(uv_dev.VENDOR_APP, uv_dev.FRONTEND.parents)
        self.assertEqual(uv_dev.BACKEND_ENTRYPOINT.name, "api_server.py")
        self.assertEqual(uv_dev.FRONTEND_PACKAGE.name, "package.json")

    def test_current_vendored_layout_is_valid(self) -> None:
        uv_dev.validate_layout()


class CommandTests(unittest.TestCase):
    def test_backend_uses_current_python(self) -> None:
        command = uv_dev.backend_command()
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[1]), uv_dev.BACKEND_ENTRYPOINT)

    @mock.patch.object(uv_dev, "npm_executable", return_value="npm-test")
    def test_frontend_command_is_repo_wrapper(self, _mock_npm) -> None:
        self.assertEqual(
            uv_dev.frontend_command("dev"),
            ["npm-test", "run", "dev"],
        )

    def test_invalid_frontend_mode_is_rejected(self) -> None:
        with self.assertRaises(uv_dev.DevError):
            uv_dev.frontend_command("unknown")


class HealthPayloadTests(unittest.TestCase):
    @mock.patch("urllib.request.urlopen")
    def test_read_health_requires_ok_payload(self, urlopen) -> None:
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = json.dumps({"status": "ok", "timestamp": 1}).encode()
        response.__enter__.return_value = response
        urlopen.return_value = response
        payload = uv_dev.read_health("http://example.test/api/health")
        self.assertEqual(payload["status"], "ok")

    @mock.patch("urllib.request.urlopen")
    def test_read_health_rejects_wrong_payload(self, urlopen) -> None:
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = json.dumps({"status": "bad"}).encode()
        response.__enter__.return_value = response
        urlopen.return_value = response
        with self.assertRaises(uv_dev.DevError):
            uv_dev.read_health("http://example.test/api/health")


if __name__ == "__main__":
    unittest.main()
