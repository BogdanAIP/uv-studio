from __future__ import annotations

import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "vendor_videoclaw.py"
SPEC = importlib.util.spec_from_file_location("vendor_videoclaw", MODULE_PATH)
assert SPEC and SPEC.loader
vendor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vendor
SPEC.loader.exec_module(vendor)


class UpstreamLockTests(unittest.TestCase):
    def test_requires_full_commit_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repository": "owner/repo",
                        "commit": "main",
                        "subtree": "app",
                        "license": "MIT",
                        "license_path": "LICENSE",
                        "default_destination": "vendor/app",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                vendor.UpstreamLock.load(lock_path)


class PathSafetyTests(unittest.TestCase):
    def test_destination_must_stay_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            inside = root / "vendor" / "app"
            self.assertEqual(vendor.safe_destination(inside, root), inside.resolve())
            with self.assertRaises(vendor.VendorError):
                vendor.safe_destination(root, root)
            with self.assertRaises(vendor.VendorError):
                vendor.safe_destination(root.parent / "outside", root)

    def test_member_filter_only_selects_configured_subtree(self) -> None:
        root = "Repo-" + "a" * 40
        selected = vendor.member_relative_path(
            f"{root}/video-claw/video-claw/backend/api.py",
            root,
            "video-claw/video-claw",
        )
        self.assertEqual(selected, Path("backend/api.py"))
        self.assertIsNone(
            vendor.member_relative_path(
                f"{root}/FilmAgent/legacy.py",
                root,
                "video-claw/video-claw",
            )
        )

    def test_member_filter_rejects_parent_escape(self) -> None:
        root = "Repo-" + "a" * 40
        with self.assertRaises(vendor.VendorError):
            vendor.member_relative_path(
                f"{root}/video-claw/video-claw/../escape.txt",
                root,
                "video-claw/video-claw",
            )


class ArchiveExtractionTests(unittest.TestCase):
    def make_lock(self):
        return vendor.UpstreamLock(
            repository="owner/Repo",
            commit="a" * 40,
            subtree="video-claw/video-claw",
            license="MIT",
            license_path="LICENSE",
            default_destination="vendor/app",
        )

    def test_stage_subtree_extracts_only_modern_app(self) -> None:
        lock = self.make_lock()
        root = vendor.archive_root_name(lock.repository, lock.commit)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / "source.tar.gz"
            staging = tmp_path / "staging"
            staging.mkdir()

            with tarfile.open(archive_path, "w:gz") as archive:
                wanted = b"print('ok')\n"
                wanted_info = tarfile.TarInfo(
                    f"{root}/video-claw/video-claw/backend/api.py"
                )
                wanted_info.size = len(wanted)
                archive.addfile(wanted_info, io.BytesIO(wanted))

                legacy = b"legacy\n"
                legacy_info = tarfile.TarInfo(f"{root}/FilmAgent/legacy.py")
                legacy_info.size = len(legacy)
                archive.addfile(legacy_info, io.BytesIO(legacy))

            files = vendor.stage_subtree(archive_path, lock, staging)
            self.assertEqual(files, [Path("backend/api.py")])
            self.assertEqual(
                (staging / "backend/api.py").read_text(encoding="utf-8"),
                "print('ok')\n",
            )
            self.assertFalse((staging / "FilmAgent/legacy.py").exists())

    def test_stage_subtree_rejects_links(self) -> None:
        lock = self.make_lock()
        root = vendor.archive_root_name(lock.repository, lock.commit)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / "source.tar.gz"
            staging = tmp_path / "staging"
            staging.mkdir()

            with tarfile.open(archive_path, "w:gz") as archive:
                link = tarfile.TarInfo(
                    f"{root}/video-claw/video-claw/backend/link.py"
                )
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside.py"
                archive.addfile(link)

            with self.assertRaises(vendor.VendorError):
                vendor.stage_subtree(archive_path, lock, staging)


if __name__ == "__main__":
    unittest.main()
