from __future__ import annotations

import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "vendor_videoclaw.py"
SPEC = importlib.util.spec_from_file_location("vendor_videoclaw_license", MODULE_PATH)
assert SPEC and SPEC.loader
vendor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vendor
SPEC.loader.exec_module(vendor)


class LicensePreservationTests(unittest.TestCase):
    def test_root_license_is_copied_next_to_vendored_source(self) -> None:
        lock = vendor.UpstreamLock(
            repository="owner/Repo",
            commit="a" * 40,
            subtree="video-claw/video-claw",
            license="MIT",
            license_path="LICENSE",
            default_destination="vendor/app",
        )
        root = vendor.archive_root_name(lock.repository, lock.commit)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / "source.tar.gz"
            staging = tmp_path / "staging"
            staging.mkdir()

            with tarfile.open(archive_path, "w:gz") as archive:
                license_bytes = b"MIT License\n"
                info = tarfile.TarInfo(f"{root}/LICENSE")
                info.size = len(license_bytes)
                archive.addfile(info, io.BytesIO(license_bytes))

            target = vendor.stage_license(archive_path, lock, staging)
            self.assertEqual(target.name, "UPSTREAM_LICENSE")
            self.assertEqual(target.read_text(encoding="utf-8"), "MIT License\n")


if __name__ == "__main__":
    unittest.main()
