from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "verify_frontend_provenance.py"
SPEC = importlib.util.spec_from_file_location("verify_frontend_provenance", MODULE_PATH)
assert SPEC and SPEC.loader
provenance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = provenance
SPEC.loader.exec_module(provenance)


class FrontendProvenanceTests(unittest.TestCase):
    def test_repository_provenance_matches_pinned_snapshot(self) -> None:
        result = provenance.verify()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "read-only")
        self.assertEqual(len(result["source_commit"]), 40)
        self.assertGreater(result["source_file_count"], 0)
        self.assertEqual(len(result["source_tree_sha256"]), 64)

    def test_validation_rejects_marker_mismatch(self) -> None:
        lock = provenance.load_upstream_pin()
        marker = provenance.read_json(provenance.PROVENANCE_PATH)
        digest, files = provenance.source_digest()
        changed = dict(marker)
        changed["source_commit"] = "0" * 40
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_provenance(lock, changed, digest=digest, file_count=len(files))

    def test_verifier_exposes_no_restore_arguments(self) -> None:
        parser = provenance.build_parser()
        options = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        self.assertNotIn("--force", options)
        self.assertNotIn("--destination", options)
        self.assertNotIn("--write", options)

    def test_verifier_uses_no_filesystem_write_primitives(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        forbidden_imports = {"shutil", "tempfile"}
        imported = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(forbidden_imports.isdisjoint(imported))

        forbidden_calls = {
            "write_text",
            "write_bytes",
            "mkdir",
            "unlink",
            "rename",
            "replace",
            "rmdir",
        }
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(called_attributes))


if __name__ == "__main__":
    unittest.main()
