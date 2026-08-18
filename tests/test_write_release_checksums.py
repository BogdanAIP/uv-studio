from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.write_release_checksums import (
    ReleaseChecksumError,
    verify_checksums,
    write_checksums,
)


class ReleaseChecksumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.portable = self.root / "uv-studio-windows-x86_64.zip"
        self.installer = self.root / "uv-studio-windows-x86_64-setup.exe"
        self.portable.write_bytes(b"portable-final-bytes")
        self.installer.write_bytes(b"installer-final-bytes")
        self.manifest = self.root / "SHA256SUMS"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_write_is_deterministic_sorted_and_verifiable(self) -> None:
        write_checksums([self.portable, self.installer], self.manifest)
        expected = (
            f"{hashlib.sha256(self.installer.read_bytes()).hexdigest()}  {self.installer.name}\n"
            f"{hashlib.sha256(self.portable.read_bytes()).hexdigest()}  {self.portable.name}\n"
        )
        self.assertEqual(self.manifest.read_text(encoding="utf-8"), expected)
        self.assertEqual(
            verify_checksums(self.manifest),
            [self.installer.name, self.portable.name],
        )

    def test_verify_rejects_tampered_artifact(self) -> None:
        write_checksums([self.portable, self.installer], self.manifest)
        self.installer.write_bytes(b"tampered")
        with self.assertRaisesRegex(ReleaseChecksumError, "SHA-256 mismatch"):
            verify_checksums(self.manifest)

    def test_duplicate_basenames_are_rejected_case_insensitively(self) -> None:
        other = self.root / "other"
        other.mkdir()
        duplicate = other / self.portable.name.upper()
        duplicate.write_bytes(b"other")
        with self.assertRaisesRegex(ReleaseChecksumError, "duplicate artifact basename"):
            write_checksums([self.portable, duplicate], self.manifest)

    def test_symlink_input_is_rejected_when_supported(self) -> None:
        link = self.root / "portable-link.zip"
        try:
            link.symlink_to(self.portable)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaisesRegex(ReleaseChecksumError, "must not be a symlink"):
            write_checksums([link, self.installer], self.manifest)

    def test_manifest_rejects_path_traversal(self) -> None:
        digest = hashlib.sha256(b"anything").hexdigest()
        self.manifest.write_text(f"{digest}  ../outside.exe\n", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseChecksumError, "must be a basename"):
            verify_checksums(self.manifest)

    def test_output_cannot_be_an_input(self) -> None:
        self.manifest.write_text("placeholder\n", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseChecksumError, "cannot also be an input"):
            write_checksums([self.manifest, self.installer], self.manifest)


if __name__ == "__main__":
    unittest.main()
