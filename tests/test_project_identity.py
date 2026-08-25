from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.identity import (
    STUDIO_COMPAT_RECIPE_ID,
    StudioIdentityError,
    classify_project_identity,
    require_modern_studio_identity,
    studio_project_extensions,
)
from uv_studio.projects.store import ProjectStore


class ProjectIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_modern_identity_is_typed_and_uses_its_own_schema_version(self) -> None:
        project = self.store.create_project(
            title="Modern",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            project_id="prj_modern_identity",
            extensions=studio_project_extensions("micro_drama"),
        )
        identity = require_modern_studio_identity(project)
        self.assertEqual(identity.schema_version, 1)
        self.assertEqual(identity.product_model, "production_directions")
        self.assertEqual(identity.direction_id, "micro_drama")
        self.assertEqual(classify_project_identity(project).kind, "modern_direction")

    def test_pretyped_schema_version_two_is_explicit_legacy_compatibility(self) -> None:
        project = self.store.create_project(
            title="PR63-era",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            project_id="prj_old_direction_identity",
            extensions={
                "studio": {
                    "schema_version": 2,
                    "product_model": "production_directions",
                    "direction_id": "commercial",
                }
            },
        )
        projection = classify_project_identity(project)
        self.assertEqual(projection.kind, "legacy_compatibility")
        self.assertEqual(projection.compatibility_kind, "production_directions_v2")
        self.assertEqual(projection.direction_id, "commercial")
        with self.assertRaises(StudioIdentityError):
            require_modern_studio_identity(project)

    def test_tampered_unknown_direction_is_invalid_recovery(self) -> None:
        project = self.store.create_project(
            title="Legacy",
            recipe_id="general_video",
            project_id="prj_tampered_identity",
        )
        path = self.store.project_path(project.project_id)
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["recipe_id"] = STUDIO_COMPAT_RECIPE_ID
        raw["extensions"] = {
            "studio": {
                "schema_version": 1,
                "product_model": "production_directions",
                "direction_id": "unknown_direction",
            }
        }
        path.write_text(json.dumps(raw), encoding="utf-8")

        reloaded = self.store.load_project(project.project_id)
        projection = classify_project_identity(reloaded)
        self.assertEqual(projection.kind, "invalid_recovery")
        self.assertIn("unknown production direction", projection.reason or "")

    def test_generic_update_cannot_change_or_remove_modern_identity(self) -> None:
        project = self.store.create_project(
            title="Protected",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            project_id="prj_protected_identity",
            extensions=studio_project_extensions("free_project"),
        )
        original = self.store.project_path(project.project_id).read_bytes()

        with self.assertRaises(StudioIdentityError):
            self.store.update_project(
                project.project_id,
                extensions=studio_project_extensions("micro_drama"),
            )
        self.assertEqual(self.store.project_path(project.project_id).read_bytes(), original)

        with self.assertRaises(StudioIdentityError):
            self.store.update_project(project.project_id, extensions={})
        self.assertEqual(self.store.project_path(project.project_id).read_bytes(), original)

    def test_generic_update_may_change_unrelated_metadata_while_preserving_identity(self) -> None:
        project = self.store.create_project(
            title="Protected",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            project_id="prj_identity_unrelated",
            extensions={**studio_project_extensions("free_project"), "demo": {"enabled": True}},
        )
        updated = self.store.update_project(
            project.project_id,
            title="Renamed",
            extensions={
                **studio_project_extensions("free_project"),
                "demo": {"enabled": False},
            },
        )
        self.assertEqual(updated.title, "Renamed")
        self.assertFalse(updated.extensions["demo"]["enabled"])
        self.assertEqual(classify_project_identity(updated).kind, "modern_direction")


if __name__ == "__main__":
    unittest.main()
