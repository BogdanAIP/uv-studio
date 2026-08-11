from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from uv_studio.projects.archive import (
    ARCHIVE_MANIFEST,
    ArchiveLimits,
    ProjectArchiveError,
    UnsupportedArchiveSchema,
    create_backup,
    export_project,
    import_project,
)
from uv_studio.projects.store import ProjectAlreadyExists, ProjectStore, ProjectStoreError


class ProjectArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source_store = ProjectStore(self.base / "source-projects")
        self.target_store = ProjectStore(self.base / "target-projects")
        self.project = self.source_store.create_project(
            title="Portable Project",
            recipe_id="general_video",
            project_id="prj_portable",
            settings={"aspect_ratio": "16:9"},
        )
        project_dir = self.source_store.project_path(self.project.project_id).parent
        (project_dir / "sources" / "clip.bin").write_bytes(b"source-bytes")
        nested = project_dir / "artifacts" / "preview"
        nested.mkdir(parents=True)
        (nested / "frame.txt").write_text("frame-data", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _export(self, name: str = "project.uvproj.zip") -> Path:
        return export_project(
            self.source_store,
            self.project.project_id,
            self.base / name,
        )

    def _rewrite_archive(self, source: Path, target: Path, mutator) -> None:
        with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(
            target, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as dst:
            for info in src.infolist():
                data = src.read(info) if not info.is_dir() else b""
                replacement = mutator(info.filename, data)
                if replacement is None:
                    replacement = data
                dst.writestr(info, replacement)

    def test_round_trip_preserves_project_and_files(self) -> None:
        archive = self._export()
        imported = import_project(self.target_store, archive)

        self.assertEqual(imported.to_dict(), self.project.to_dict())
        target_dir = self.target_store.project_path(imported.project_id).parent
        self.assertEqual((target_dir / "sources" / "clip.bin").read_bytes(), b"source-bytes")
        self.assertEqual(
            (target_dir / "artifacts" / "preview" / "frame.txt").read_text(encoding="utf-8"),
            "frame-data",
        )

    def test_backup_creates_portable_archive(self) -> None:
        backup = create_backup(
            self.source_store,
            self.project.project_id,
            self.base / "backups",
        )
        self.assertTrue(backup.is_file())
        self.assertTrue(backup.name.endswith(".uvproj.zip"))
        imported = import_project(self.target_store, backup)
        self.assertEqual(imported.project_id, self.project.project_id)

    def test_export_rejects_archive_inside_project(self) -> None:
        project_dir = self.source_store.project_path(self.project.project_id).parent
        with self.assertRaises(ProjectArchiveError):
            export_project(
                self.source_store,
                self.project.project_id,
                project_dir / "exports" / "self.uvproj.zip",
            )

    def test_duplicate_import_is_rejected_without_overwrite(self) -> None:
        archive = self._export()
        import_project(self.target_store, archive)
        before = self.target_store.project_path(self.project.project_id).read_bytes()
        with self.assertRaises(ProjectAlreadyExists):
            import_project(self.target_store, archive)
        self.assertEqual(
            self.target_store.project_path(self.project.project_id).read_bytes(),
            before,
        )

    def test_tampered_file_hash_is_rejected_and_project_is_not_committed(self) -> None:
        archive = self._export()
        tampered = self.base / "tampered.uvproj.zip"

        def mutate(name: str, data: bytes) -> bytes | None:
            if name == "project/sources/clip.bin":
                return b"tampered"
            return data

        self._rewrite_archive(archive, tampered, mutate)
        with self.assertRaises(ProjectArchiveError) as caught:
            import_project(self.target_store, tampered)
        self.assertIn("mismatch", str(caught.exception).lower())
        self.assertFalse((self.target_store.root / self.project.project_id).exists())

    def test_failed_final_commit_leaves_no_partial_canonical_project(self) -> None:
        archive = self._export()
        canonical = self.target_store.root / self.project.project_id

        with mock.patch("uv_studio.projects.store.os.replace", side_effect=OSError("simulated commit failure")):
            with self.assertRaises(ProjectStoreError):
                import_project(self.target_store, archive)

        self.assertFalse(canonical.exists())
        self.assertEqual(
            [item for item in self.target_store.root.iterdir() if not item.name.startswith(".uv-import-")],
            [],
        )

    def test_undeclared_project_file_is_rejected(self) -> None:
        archive = self._export()
        tampered = self.base / "undeclared.uvproj.zip"
        self._rewrite_archive(archive, tampered, lambda _name, data: data)
        with zipfile.ZipFile(tampered, "a", compression=zipfile.ZIP_DEFLATED) as dst:
            dst.writestr("project/sources/undeclared.bin", b"unexpected")

        with self.assertRaises(ProjectArchiveError) as caught:
            import_project(self.target_store, tampered)
        self.assertIn("undeclared", str(caught.exception).lower())

    def test_path_traversal_is_rejected_before_extraction(self) -> None:
        malicious = self.base / "traversal.uvproj.zip"
        with zipfile.ZipFile(malicious, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                ARCHIVE_MANIFEST,
                json.dumps(
                    {
                        "archive_schema_version": 1,
                        "project_id": "prj_escape",
                        "project_schema_version": 1,
                        "files": [],
                    }
                ),
            )
            archive.writestr("../escape.txt", b"bad")

        with self.assertRaises(ProjectArchiveError):
            import_project(self.target_store, malicious)
        self.assertFalse((self.base / "escape.txt").exists())

    def test_manifest_project_id_traversal_is_rejected_before_staging(self) -> None:
        archive = self._export()
        malicious = self.base / "bad-project-id.uvproj.zip"

        def mutate(name: str, data: bytes) -> bytes | None:
            if name == ARCHIVE_MANIFEST:
                manifest = json.loads(data.decode("utf-8"))
                manifest["project_id"] = "../escape"
                return json.dumps(manifest).encode("utf-8")
            return data

        self._rewrite_archive(archive, malicious, mutate)
        with self.assertRaises(ProjectArchiveError):
            import_project(self.target_store, malicious)
        self.assertFalse((self.target_store.root.parent / "escape").exists())
        self.assertEqual(list(self.target_store.root.iterdir()), [])

    def test_future_archive_schema_is_rejected(self) -> None:
        archive = self._export()
        future = self.base / "future.uvproj.zip"

        def mutate(name: str, data: bytes) -> bytes | None:
            if name == ARCHIVE_MANIFEST:
                manifest = json.loads(data.decode("utf-8"))
                manifest["archive_schema_version"] = 999
                return json.dumps(manifest).encode("utf-8")
            return data

        self._rewrite_archive(archive, future, mutate)
        with self.assertRaises(UnsupportedArchiveSchema):
            import_project(self.target_store, future)

    def test_archive_limits_are_enforced(self) -> None:
        archive = self._export()
        limits = ArchiveLimits(
            max_entries=100,
            max_total_uncompressed_bytes=1024 * 1024,
            max_single_file_bytes=4,
            max_manifest_bytes=1024 * 1024,
        )
        with self.assertRaises(ProjectArchiveError):
            import_project(self.target_store, archive, limits=limits)


if __name__ == "__main__":
    unittest.main()
