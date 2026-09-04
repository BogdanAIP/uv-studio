from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.projects.migrations import UnsupportedProjectSchema
from uv_studio.projects.models import (
    PROJECT_SCHEMA_VERSION,
    ProjectReference,
    ProjectValidationError,
    compatibility_recipe_id,
)
from uv_studio.projects.store import (
    PROJECT_DIRECTORIES,
    ProjectAlreadyExists,
    ProjectNotFound,
    ProjectStore,
    ProjectStoreError,
)


class ProjectStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_project_writes_canonical_layout(self) -> None:
        project = self.store.create_project(
            title="First Project",
            recipe_id="general_video",
            project_id="prj_test",
        )
        self.assertEqual(project.project_id, "prj_test")
        path = self.root / "prj_test" / "project.json"
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], PROJECT_SCHEMA_VERSION)
        self.assertNotIn("recipe_id", data)
        self.assertEqual(
            data["compatibility"],
            {"schema_version": 1, "recipe_id": "general_video"},
        )
        self.assertEqual(compatibility_recipe_id(project), "general_video")
        for name in PROJECT_DIRECTORIES:
            self.assertTrue((self.root / "prj_test" / name).is_dir())

    def test_schema_v1_load_preserves_legacy_identity_and_references_until_write(self) -> None:
        project = self.store.create_project(
            recipe_id="general_video",
            title="Legacy fixture",
            project_id="prj_legacy_v1",
        )
        source = ProjectReference(
            id="src_legacy",
            kind="source",
            path="sources/input.mp4",
            metadata={"role": "primary"},
        )
        artifact = ProjectReference(
            id="art_legacy",
            kind="artifact",
            path="artifacts/output.mp4",
            metadata={"origin": "historic"},
        )
        self.store.update_project(
            project.project_id,
            settings={"aspect_ratio": "9:16"},
            sources=[source],
            artifacts=[artifact],
        )
        path = self.store.project_path(project.project_id)
        raw_v2 = json.loads(path.read_text(encoding="utf-8"))
        compatibility = raw_v2.pop("compatibility")
        raw_v2["schema_version"] = 1
        raw_v2["recipe_id"] = "historic_recipe_unknown"
        path.write_text(json.dumps(raw_v2, ensure_ascii=False, indent=2), encoding="utf-8")
        legacy_bytes = path.read_bytes()

        loaded = ProjectStore(self.root).load_project(project.project_id)

        self.assertEqual(loaded.schema_version, PROJECT_SCHEMA_VERSION)
        self.assertEqual(compatibility_recipe_id(loaded), "historic_recipe_unknown")
        self.assertEqual(loaded.sources[0].id, "src_legacy")
        self.assertEqual(loaded.sources[0].path, "sources/input.mp4")
        self.assertEqual(loaded.artifacts[0].id, "art_legacy")
        self.assertEqual(loaded.artifacts[0].path, "artifacts/output.mp4")
        self.assertEqual(loaded.settings, {"aspect_ratio": "9:16"})
        self.assertEqual(path.read_bytes(), legacy_bytes)
        self.assertNotIn("recipe_id", loaded.to_dict())
        self.assertEqual(
            loaded.to_dict()["compatibility"],
            {"schema_version": compatibility["schema_version"], "recipe_id": "historic_recipe_unknown"},
        )

        saved = self.store.save_project(loaded)
        persisted_v2 = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved.schema_version, PROJECT_SCHEMA_VERSION)
        self.assertEqual(persisted_v2["schema_version"], PROJECT_SCHEMA_VERSION)
        self.assertNotIn("recipe_id", persisted_v2)
        self.assertEqual(
            persisted_v2["compatibility"]["recipe_id"],
            "historic_recipe_unknown",
        )
        self.assertEqual(persisted_v2["sources"][0]["id"], "src_legacy")
        self.assertEqual(persisted_v2["sources"][0]["path"], "sources/input.mp4")
        self.assertEqual(persisted_v2["artifacts"][0]["id"], "art_legacy")
        self.assertEqual(persisted_v2["artifacts"][0]["path"], "artifacts/output.mp4")

    def test_schema_v1_reserved_compatibility_state_is_rejected(self) -> None:
        self.store.create_project(
            recipe_id="general_video",
            title="Ambiguous legacy",
            project_id="prj_legacy_ambiguous",
        )
        path = self.store.project_path("prj_legacy_ambiguous")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["schema_version"] = 1
        raw["recipe_id"] = "general_video"
        path.write_text(json.dumps(raw), encoding="utf-8")

        with self.assertRaises(ProjectStoreError) as caught:
            self.store.load_project("prj_legacy_ambiguous")
        self.assertIn("reserved compatibility", str(caught.exception))

    def test_restart_can_load_existing_project(self) -> None:
        created = self.store.create_project(recipe_id="general_video", title="Persistent", project_id="prj_restart")
        restarted = ProjectStore(self.root)
        loaded = restarted.load_project("prj_restart")
        self.assertEqual(loaded.to_dict(), created.to_dict())

    def test_update_preserves_created_at_and_changes_data(self) -> None:
        created = self.store.create_project(recipe_id="general_video", title="Before", project_id="prj_update")
        source = ProjectReference(
            id="src_1",
            kind="source",
            path="sources/input.mp4",
            metadata={"role": "primary"},
        )
        updated = self.store.update_project(
            "prj_update",
            title="After",
            settings={"aspect_ratio": "16:9"},
            sources=[source],
        )
        self.assertEqual(updated.created_at, created.created_at)
        self.assertEqual(updated.title, "After")
        self.assertEqual(updated.settings["aspect_ratio"], "16:9")
        self.assertEqual(updated.sources[0].path, "sources/input.mp4")
        loaded = ProjectStore(self.root).load_project("prj_update")
        self.assertEqual(loaded.title, "After")

    def test_nested_nonportable_values_are_rejected_at_model_boundaries(self) -> None:
        bad_project_id = "prj_bad_json"
        with self.assertRaises(ProjectValidationError):
            self.store.create_project(recipe_id="general_video",
                title="Bad JSON",
                project_id=bad_project_id,
                settings={"nested": [{"value": float("nan")}]},
            )
        self.assertFalse((self.root / bad_project_id).exists())

        with self.assertRaises(ProjectValidationError):
            self.store.create_project(recipe_id="general_video",
                title="Bad Key",
                project_id="prj_bad_key",
                extensions={"nested": {1: "not-portable"}},
            )

        with self.assertRaises(ProjectValidationError):
            self.store.create_project(recipe_id="general_video",
                title="Bad Tuple",
                project_id="prj_bad_tuple",
                settings={"nested": ("python-only-array",)},
            )

        with self.assertRaises(ProjectValidationError):
            ProjectReference(
                id="src_bad_json",
                kind="source",
                path="sources/input.mp4",
                metadata={"nested": [object()]},
            )

        recursive: list[object] = []
        recursive.append(recursive)
        with self.assertRaises(ProjectValidationError):
            self.store.create_project(recipe_id="general_video",
                title="Recursive",
                project_id="prj_recursive",
                settings={"value": recursive},
            )

    def test_update_rejects_nonfinite_value_and_preserves_previous_document(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Stable", project_id="prj_update_json")
        path = self.store.project_path("prj_update_json")
        before = path.read_bytes()

        with self.assertRaises(ProjectValidationError):
            self.store.update_project(
                "prj_update_json",
                extensions={"nested": {"value": float("inf")}},
            )

        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.store.load_project("prj_update_json").title, "Stable")

    def test_save_strict_writer_rejects_mutated_reference_metadata(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Stable", project_id="prj_save_json")
        reference = ProjectReference(
            id="src_mutable",
            kind="source",
            path="sources/input.mp4",
            metadata={"score": 1.0},
        )
        document = self.store.update_project("prj_save_json", sources=[reference])
        path = self.store.project_path("prj_save_json")
        before = path.read_bytes()

        document.sources[0].metadata["score"] = float("-inf")
        with self.assertRaises(ProjectValidationError):
            self.store.save_project(document)

        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.store.load_project("prj_save_json").sources[0].metadata["score"], 1.0)

    def test_reopen_rejects_nonfinite_json_constant(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Nonfinite", project_id="prj_nonfinite")
        path = self.store.project_path("prj_nonfinite")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["settings"] = {"nested": {"value": float("nan")}}
        path.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaises(ProjectStoreError) as caught:
            ProjectStore(self.root).load_project("prj_nonfinite")
        self.assertIn("non-finite", str(caught.exception).lower())

    def test_duplicate_project_is_rejected(self) -> None:
        self.store.create_project(recipe_id="general_video", title="One", project_id="prj_duplicate")
        with self.assertRaises(ProjectAlreadyExists):
            self.store.create_project(recipe_id="general_video", title="Two", project_id="prj_duplicate")

    def test_missing_project_is_explicit(self) -> None:
        with self.assertRaises(ProjectNotFound):
            self.store.load_project("prj_missing")

    def test_project_id_traversal_is_rejected(self) -> None:
        with self.assertRaises(ProjectValidationError):
            self.store.create_project(recipe_id="general_video", title="Bad", project_id="../escape")
        with self.assertRaises(ProjectValidationError):
            self.store.load_project("..\\escape")

    def test_reference_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(ProjectValidationError):
            ProjectReference(id="src_bad", kind="source", path="../outside.mp4")
        with self.assertRaises(ProjectValidationError):
            ProjectReference(id="src_bad2", kind="source", path="C:\\outside.mp4")

    def test_resolve_project_file_rechecks_allowed_root_after_symlink_resolution(self) -> None:
        project = self.store.create_project(recipe_id="general_video", title="Symlink boundary", project_id="prj_symlink")
        project_dir = self.store.project_directory(project.project_id)
        private = project_dir / "tasks" / "private.json"
        private.write_text('{"secret": true}\n', encoding="utf-8")
        alias = project_dir / "sources" / "alias.json"
        try:
            alias.symlink_to(Path("..") / "tasks" / "private.json")
        except OSError as exc:
            self.skipTest(f"symlinks are unavailable on this runner: {exc}")

        with self.assertRaises(ProjectValidationError):
            self.store.resolve_project_file(
                project.project_id,
                "sources/alias.json",
                must_exist=True,
                allowed_roots=("sources",),
            )

    def test_malformed_json_is_rejected(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Broken", project_id="prj_broken")
        path = self.store.project_path("prj_broken")
        path.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(ProjectStoreError):
            self.store.load_project("prj_broken")

    def test_newer_schema_is_rejected(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Future", project_id="prj_future")
        path = self.store.project_path("prj_future")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = 999
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ProjectStoreError) as caught:
            self.store.load_project("prj_future")
        self.assertIn("newer than supported", str(caught.exception))

    def test_directory_id_must_match_document_id(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Mismatch", project_id="prj_match")
        path = self.store.project_path("prj_match")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["project_id"] = "prj_other"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ProjectStoreError):
            self.store.load_project("prj_match")

    def test_failed_atomic_replace_leaves_previous_document_intact(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Stable", project_id="prj_atomic")
        path = self.store.project_path("prj_atomic")
        before = path.read_bytes()

        with mock.patch.object(os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                self.store.update_project("prj_atomic", title="Should Not Persist")

        self.assertEqual(path.read_bytes(), before)
        temporary_files = list(path.parent.glob(".project.json.*.tmp"))
        self.assertEqual(temporary_files, [])

    def test_list_projects_ignores_unrelated_directories(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Older", project_id="prj_a")
        self.store.create_project(recipe_id="general_video", title="Newer", project_id="prj_b")
        (self.root / "not-a-project").mkdir()
        projects = self.store.list_projects()
        self.assertEqual({item.project_id for item in projects}, {"prj_a", "prj_b"})

    def test_list_projects_isolates_corrupt_project_and_preserves_its_bytes(self) -> None:
        self.store.create_project(recipe_id="general_video", title="Healthy A", project_id="prj_healthy_a")
        self.store.create_project(recipe_id="general_video", title="Broken", project_id="prj_corrupt")
        self.store.create_project(recipe_id="general_video", title="Healthy B", project_id="prj_healthy_b")
        corrupt_path = self.store.project_path("prj_corrupt")
        corrupt_bytes = b"{not-json\n"
        corrupt_path.write_bytes(corrupt_bytes)

        projects, diagnostics = self.store.list_projects_with_diagnostics()

        self.assertEqual(
            {item.project_id for item in projects},
            {"prj_healthy_a", "prj_healthy_b"},
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].project_id, "prj_corrupt")
        self.assertEqual(diagnostics[0].path, str(corrupt_path))
        self.assertIn("Malformed project JSON", diagnostics[0].error)
        self.assertLessEqual(len(diagnostics[0].error), 500)
        self.assertEqual(corrupt_path.read_bytes(), corrupt_bytes)
        self.assertEqual(
            {item.project_id for item in self.store.list_projects()},
            {"prj_healthy_a", "prj_healthy_b"},
        )


if __name__ == "__main__":
    unittest.main()
