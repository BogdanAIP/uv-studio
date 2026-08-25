from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from uv_studio.config import (
    ROOT,
    allowed_frontend_origins,
    configuration_root,
    runtime_config_path,
    runtime_secrets_path,
)
from uv_studio.projects.archive import export_project
from uv_studio.projects.store import ProjectStore
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

    def test_default_machine_config_lives_outside_vendor_tree(self) -> None:
        with patch.dict(os.environ, {"UV_STUDIO_CONFIG_DIR": ""}, clear=False):
            config_path = runtime_config_path()
            secrets_path = runtime_secrets_path()
        self.assertEqual(config_path, (ROOT / "data" / "config" / "runtime.json").resolve())
        self.assertEqual(secrets_path, (ROOT / "data" / "config" / "secrets.json").resolve())
        self.assertNotIn("vendor", config_path.parts)
        self.assertNotIn("vendor", secrets_path.parts)

    def test_machine_config_override_cannot_point_into_vendor_tree(self) -> None:
        forbidden = str(ROOT / "vendor" / "credential-store")
        with patch.dict(os.environ, {"UV_STUDIO_CONFIG_DIR": forbidden}, clear=False):
            with self.assertRaises(RuntimeError):
                configuration_root()

    def test_machine_config_override_cannot_point_into_project_store(self) -> None:
        root = Path(self.tempdir.name)
        project_store = root / "canonical-projects"
        forbidden = project_store / "project-a" / "machine-config"
        with patch.dict(
            os.environ,
            {
                "UV_STUDIO_PROJECTS_DIR": str(project_store),
                "UV_STUDIO_CONFIG_DIR": str(forbidden),
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                configuration_root()

    def test_runtime_config_store_rejects_direct_vendor_paths(self) -> None:
        vendor_runtime = ROOT / "vendor" / "runtime.json"
        vendor_secrets = ROOT / "vendor" / "secrets.json"
        with self.assertRaises(RuntimeConfigError):
            RuntimeConfigStore(
                config_path=vendor_runtime,
                secrets_path=self.secrets_path,
            )
        with self.assertRaises(RuntimeConfigError):
            RuntimeConfigStore(
                config_path=self.config_path,
                secrets_path=vendor_secrets,
            )

    def test_runtime_config_store_rejects_direct_project_store_paths(self) -> None:
        root = Path(self.tempdir.name)
        project_store = root / "canonical-projects"
        inside_project_store = project_store / "project-a" / "secrets.json"
        with patch.dict(
            os.environ,
            {"UV_STUDIO_PROJECTS_DIR": str(project_store)},
            clear=False,
        ):
            with self.assertRaises(RuntimeConfigError):
                RuntimeConfigStore(
                    config_path=self.config_path,
                    secrets_path=inside_project_store,
                )

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

    def test_machine_secret_is_not_exported_with_canonical_project(self) -> None:
        secret = "machine-only-secret-never-in-project-archive"
        self.store.update(
            secret_updates={"api_providers.openai.api_key": secret},
        )

        root = Path(self.tempdir.name)
        project_store = ProjectStore(root / "projects")
        project = project_store.create_project(recipe_id="general_video", title="Portable project")
        archive_path = export_project(
            project_store,
            project.project_id,
            root / "portable.uvproj.zip",
        )

        with zipfile.ZipFile(archive_path, "r") as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    self.assertNotIn(secret.encode("utf-8"), archive.read(info), info.filename)

    def test_public_values_cannot_smuggle_an_api_key(self) -> None:
        with self.assertRaises(RuntimeConfigError):
            self.store.update(
                values={"api_providers": {"openai": {"api_key": "forbidden"}}},
            )

    def test_public_provider_urls_cannot_embed_credentials_or_query_secrets(self) -> None:
        for base_url in (
            "https://user:password@example.test/v1",
            "https://example.test/v1?api_key=secret",
            "https://example.test/v1#secret",
        ):
            with self.subTest(base_url=base_url):
                with self.assertRaises(RuntimeConfigError):
                    self.store.update(
                        values={"api_providers": {"openai": {"base_url": base_url}}},
                    )

    def test_public_proxy_cannot_embed_credentials(self) -> None:
        with self.assertRaises(RuntimeConfigError):
            self.store.update(
                values={
                    "api_providers": {
                        "common": {"proxy": "http://user:password@127.0.0.1:8080"}
                    }
                },
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

    def test_allowed_frontend_origins_rejects_userinfo(self) -> None:
        with patch.dict(
            os.environ,
            {"UV_STUDIO_ALLOWED_ORIGINS": "http://user:password@127.0.0.1:3000"},
            clear=False,
        ):
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
