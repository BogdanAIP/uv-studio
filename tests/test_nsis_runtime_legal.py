from __future__ import annotations

import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.nsis_runtime_legal import NSISLegalError, _read_copying, stage_nsis_legal


def _archive(path: Path, members: list[tuple[str, bytes, str]]) -> None:
    with tarfile.open(path, "w:bz2") as bundle:
        for name, content, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(content)
                bundle.addfile(info, io.BytesIO(content))
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                bundle.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                bundle.addfile(info)
            else:
                raise AssertionError(kind)


class NSISRuntimeLegalTests(unittest.TestCase):
    def test_exact_copying_is_staged_with_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tar.bz2"
            copying = b"NSIS COPYING\n"
            _archive(
                source,
                [
                    ("nsis-3.12-src", b"", "dir"),
                    ("nsis-3.12-src/COPYING", copying, "file"),
                    ("nsis-3.12-src/SConstruct", b"build\n", "file"),
                ],
            )
            digest = hashlib.sha256(source.read_bytes()).hexdigest()

            def fake_download(url: str, target: Path) -> tuple[int, str]:
                del url
                data = source.read_bytes()
                target.write_bytes(data)
                return len(data), hashlib.sha256(data).hexdigest()

            output = root / "release"
            output.mkdir()
            with patch("tools.nsis_runtime_legal._download", side_effect=fake_download):
                result = stage_nsis_legal(
                    output_root=output,
                    version="3.12",
                    source_url="https://example.invalid/nsis-3.12-src.tar.bz2",
                    expected_sha256=digest,
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["source_archive_sha256"], digest)
            self.assertTrue(result["expected_sha256_enforced"])
            self.assertEqual((output / "legal" / "nsis" / "COPYING.txt").read_bytes(), copying)
            self.assertTrue((output / "legal" / "nsis" / "source-evidence.json").is_file())

    def test_hash_mismatch_fails_closed_and_removes_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tar.bz2"
            _archive(source, [("nsis-3.12-src/COPYING", b"license\n", "file")])

            def fake_download(url: str, target: Path) -> tuple[int, str]:
                del url
                data = source.read_bytes()
                target.write_bytes(data)
                return len(data), hashlib.sha256(data).hexdigest()

            output = root / "release"
            output.mkdir()
            with patch("tools.nsis_runtime_legal._download", side_effect=fake_download):
                with self.assertRaises(NSISLegalError):
                    stage_nsis_legal(
                        output_root=output,
                        version="3.12",
                        source_url="https://example.invalid/nsis-3.12-src.tar.bz2",
                        expected_sha256="0" * 64,
                    )
            self.assertFalse((output / "legal" / "nsis").exists())

    def test_archive_rejects_traversal_symlink_and_missing_exact_copying(self) -> None:
        cases = (
            [("../COPYING", b"bad\n", "file")],
            [("nsis-3.12-src/COPYING", b"", "symlink")],
            [("nsis-3.12-src/LICENSE", b"wrong\n", "file")],
        )
        for members in cases:
            with self.subTest(members=members), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "bad.tar.bz2"
                _archive(archive, list(members))
                with self.assertRaises(NSISLegalError):
                    _read_copying(archive, "3.12")

    def test_duplicate_copying_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "dup.tar.bz2"
            _archive(
                archive,
                [
                    ("nsis-3.12-src/COPYING", b"one\n", "file"),
                    ("nsis-3.12-src/COPYING", b"two\n", "file"),
                ],
            )
            with self.assertRaises(NSISLegalError):
                _read_copying(archive, "3.12")


if __name__ == "__main__":
    unittest.main()
