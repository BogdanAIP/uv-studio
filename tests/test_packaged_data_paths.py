from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.config import (
    ROOT,
    configuration_root,
    packaged_mode,
    projects_root,
    release_root,
    user_data_root,
)


class PackagedDataPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.release = self.root / "installed-app"
        self.release.mkdir()
        self.local_app_data = self.root / "LocalAppData"
        self.local_app_data.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _packaged_env(self, **updates: str) -> dict[str, str]:
        values = {
            "UV_STUDIO_RELEASE_ROOT": str(self.release),
            "UV_STUDIO_USER_DATA_DIR": "",
            "UV_STUDIO_PROJECTS_DIR": "",
            "UV_STUDIO_CONFIG_DIR": "",
            "LOCALAPPDATA": str(self.local_app_data),
            "XDG_DATA_HOME": "",
        }
        values.update(updates)
        return values

    def test_development_defaults_remain_repository_local(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "UV_STUDIO_RELEASE_ROOT": "",
                "UV_STUDIO_USER_DATA_DIR": "",
                "UV_STUDIO_PROJECTS_DIR": "",
                "UV_STUDIO_CONFIG_DIR": "",
            },
            clear=False,
        ):
            self.assertFalse(packaged_mode())
            self.assertIsNone(release_root())
            self.assertEqual(projects_root(), (ROOT / "data" / "projects").resolve())
            self.assertEqual(configuration_root(), (ROOT / "data" / "config").resolve())

    def test_packaged_defaults_use_local_app_data_not_release_payload(self) -> None:
        with mock.patch.dict(os.environ, self._packaged_env(), clear=False):
            self.assertTrue(packaged_mode())
            self.assertEqual(release_root(), self.release.resolve())
            expected = (self.local_app_data / "UV Studio").resolve()
            self.assertEqual(user_data_root(), expected)
            self.assertEqual(projects_root(), expected / "projects")
            self.assertEqual(configuration_root(), expected / "config")
            self.assertNotIn(self.release.resolve(), projects_root().parents)
            self.assertNotIn(self.release.resolve(), configuration_root().parents)

    def test_packaged_user_data_root_has_explicit_admin_override(self) -> None:
        custom = self.root / "PortableUserData"
        with mock.patch.dict(
            os.environ,
            self._packaged_env(UV_STUDIO_USER_DATA_DIR=str(custom)),
            clear=False,
        ):
            self.assertEqual(user_data_root(), custom.resolve())
            self.assertEqual(projects_root(), custom.resolve() / "projects")
            self.assertEqual(configuration_root(), custom.resolve() / "config")

    def test_project_store_cannot_be_placed_inside_release_payload(self) -> None:
        forbidden = self.release / "mutable-projects"
        with mock.patch.dict(
            os.environ,
            self._packaged_env(UV_STUDIO_PROJECTS_DIR=str(forbidden)),
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                projects_root()

    def test_machine_configuration_cannot_be_placed_inside_release_payload(self) -> None:
        forbidden = self.release / "mutable-config"
        with mock.patch.dict(
            os.environ,
            self._packaged_env(UV_STUDIO_CONFIG_DIR=str(forbidden)),
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                configuration_root()

    def test_project_store_and_configuration_must_not_overlap_in_either_direction(self) -> None:
        parent = self.root / "mutable"
        cases = (
            (parent, parent / "config"),
            (parent / "projects", parent),
            (parent, parent),
        )
        for projects, config in cases:
            with self.subTest(projects=projects, config=config):
                with mock.patch.dict(
                    os.environ,
                    self._packaged_env(
                        UV_STUDIO_PROJECTS_DIR=str(projects),
                        UV_STUDIO_CONFIG_DIR=str(config),
                    ),
                    clear=False,
                ):
                    with self.assertRaises(RuntimeError):
                        projects_root()
                    with self.assertRaises(RuntimeError):
                        configuration_root()


if __name__ == "__main__":
    unittest.main()
