from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "promote_frontend.py"
SPEC = importlib.util.spec_from_file_location("promote_frontend", MODULE_PATH)
assert SPEC and SPEC.loader
promote = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = promote
SPEC.loader.exec_module(promote)


class FrontendPromotionTests(unittest.TestCase):
    def test_source_digest_is_stable(self) -> None:
        first_digest, first_files = promote.source_digest()
        second_digest, second_files = promote.source_digest()
        self.assertEqual(first_digest, second_digest)
        self.assertEqual(first_files, second_files)
        self.assertGreater(len(first_files), 0)
        self.assertEqual(len(first_digest), 64)

    def test_destination_must_stay_inside_repo(self) -> None:
        with self.assertRaises(promote.PromotionError):
            promote.safe_destination(promote.ROOT)
        with self.assertRaises(promote.PromotionError):
            promote.safe_destination(promote.ROOT.parent / "outside")

    def test_cannot_write_inside_vendor_source(self) -> None:
        with self.assertRaises(promote.PromotionError):
            promote.safe_destination(promote.SOURCE)
        with self.assertRaises(promote.PromotionError):
            promote.safe_destination(promote.SOURCE / "nested")

    def test_existing_destination_requires_force_even_when_managed(self) -> None:
        with tempfile.TemporaryDirectory(dir=promote.ROOT) as tmp:
            destination = Path(tmp) / "frontend"
            first = promote.promote(destination)
            self.assertEqual(first["managed_by"], "tools/promote_frontend.py")
            (destination / "product-change.txt").write_text("keep me", encoding="utf-8")

            with self.assertRaises(promote.PromotionError):
                promote.promote(destination)

            self.assertEqual(
                (destination / "product-change.txt").read_text(encoding="utf-8"),
                "keep me",
            )

    def test_unmanaged_existing_destination_requires_force(self) -> None:
        with tempfile.TemporaryDirectory(dir=promote.ROOT) as tmp:
            destination = Path(tmp) / "frontend"
            destination.mkdir()
            (destination / "custom.txt").write_text("keep me", encoding="utf-8")
            with self.assertRaises(promote.PromotionError):
                promote.promote(destination)
            self.assertEqual((destination / "custom.txt").read_text(encoding="utf-8"), "keep me")

    def test_promoted_copy_records_exact_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=promote.ROOT) as tmp:
            destination = Path(tmp) / "frontend"
            provenance = promote.promote(destination)
            marker = json.loads((destination / promote.PROVENANCE_FILE).read_text(encoding="utf-8"))
            lock = json.loads(promote.LOCK_PATH.read_text(encoding="utf-8"))
            self.assertEqual(marker, provenance)
            self.assertEqual(marker["source_commit"], lock["commit"])
            self.assertEqual(marker["source_subtree"], f"{lock['subtree']}/frontend")
            self.assertTrue((destination / "package.json").is_file())
            self.assertTrue((destination / "package-lock.json").is_file())
            self.assertTrue((destination / "UPSTREAM_LICENSE").is_file())

    def test_force_recreates_promoted_baseline(self) -> None:
        with tempfile.TemporaryDirectory(dir=promote.ROOT) as tmp:
            destination = Path(tmp) / "frontend"
            first = promote.promote(destination)
            (destination / "changed.txt").write_text("product change", encoding="utf-8")
            second = promote.promote(destination, force=True)
            self.assertEqual(first["source_tree_sha256"], second["source_tree_sha256"])
            self.assertFalse((destination / "changed.txt").exists())


if __name__ == "__main__":
    unittest.main()
