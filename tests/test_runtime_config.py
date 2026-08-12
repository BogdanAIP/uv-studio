from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uv_studio.config import allowed_frontend_origins
from uv_studio.runtime_config import RuntimeConfigError, RuntimeConfigStore


class RuntimeConfigStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.config_path = root / "runtime.json"
        self.secrets_path = root / "secrets.json"
        self.store = RuntimeConfigStore(
            config_path=self.config_path,
            secrets_path=self.secrets_path,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_defaults_are_public_and_contain_no_secret_fields(self) -> None:
        public = self.store.public_config()
        encoded = json.dumps(public, sort_keys=True)
        self.assertNotIn("api_key", encoded)
        self.assertFalse(any(self.store.secret_status().values()))

    def test_secret_updates_are_separate_from_public_config(self) -> None:
        secret = "test-secret-never-return-this"
        public, status = self.store.update(
            values={"generation": {"video_resolution": "1080P"}},
            secret_updates={"api_providers.openai.api_key": secret},
        )

        self.assertEqual(public["generation"]["video_resolution"], "1080P")
        self.assertTrue(status["api_providers.openai.api_key"])
        self.assertEqual(self.store.secret_value("api_providers.openai.api_key"), secret)
        self.assertNotIn(secret, self.config_path.read_text(encoding="utf-8"))
        self.assertIn(secret, self.secrets_path.read_text(encoding="utf-8"))
        self.assertNotIn("api_key", json.dumps(public, sort_keys=True))

    def test_public_values_cannot_smuggle_an_api_key(self) -> None:
        with self.assertRaises(RuntimeConfigError):
            self.store.update(
                values={"api_providers": {"openai": {"api_key": "forbidden"}}},
            )

    def test_secret_replacement_does_not_require_old_value_and_null_clears(self) -> None:
        path = "api_providers.openai.api_key"
        self.store.update(secret_updates={path: "first-secret"})
        self.store.update(secret_updates={path: "second-secret"})
        self.assertEqual(self.store.secret_value(path), "second-secret")

        _, status = self.store.update(secret_updates={path: None})
        self.assertFalse(status[path])
        self.assertIsNone(self.store.secret_value(path))

    def test_empty_secret_update_is_rejected_instead_of_implicitly_clearing(self) -> None:
        with self.assertRaises(RuntimeConfigError):
            self.store.update(
                secret_updates={"api_providers.openai.api_key": "   "},
            )

    def test_server_host_is_fail_closed_to_loopback(self) -> None:
        with self.assertRaises(RuntimeConfigError):
            self.store.update(values={"server": {"host": "0.0.0.0"}})

    def test_unknown_persisted_fields_fail_closed(self) -> None:
        self.config_path.write_text(
            json.dumps({"unexpected": {"field": True}}),
            encoding="utf-8",
        )
        with self.assertRaises(RuntimeConfigError):
            self.store.public_config()

    def test_allowed_frontend_origins_rejects_wildcard(self) -> None:
        with patch.dict(os.environ, {"UV_STUDIO_ALLOWED_ORIGINS": "*"}, clear=False):
            with self.assertRaises(RuntimeError):
                allowed_frontend_origins()

    def test_allowed_frontend_origins_accepts_explicit_local_origins(self) -> None:
        with patch.dict(
            os.environ,
            {"UV_STUDIO_ALLOWED_ORIGINS": "http://127.0.0.1:3000,http://localhost:3000"},
            clear=False,
        ):
            self.assertEqual(
                allowed_frontend_origins(),
                ("http://127.0.0.1:3000", "http://localhost:3000"),
            )


if __name__ == "__main__":
    unittest.main()
