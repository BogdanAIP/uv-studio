from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "verify_frontend_provenance.py"
SPEC = importlib.util.spec_from_file_location("verify_frontend_provenance", MODULE_PATH)
assert SPEC and SPEC.loader
provenance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = provenance
SPEC.loader.exec_module(provenance)


class FrontendProvenanceTests(unittest.TestCase):
    def test_repository_provenance_matches_pinned_snapshot(self) -> None:
        resolved_tree = "a" * 40
        with mock.patch.object(provenance, "validate_upstream_snapshot", return_value=resolved_tree):
            result = provenance.verify()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "read-only")
        self.assertEqual(len(result["source_commit"]), 40)
        self.assertGreater(result["source_file_count"], 0)
        self.assertEqual(len(result["source_tree_sha256"]), 64)
        self.assertEqual(result["upstream_frontend_tree_sha"], resolved_tree)

    def test_validation_rejects_vendored_identity_mismatch(self) -> None:
        lock = provenance.load_upstream_pin()
        vendor_marker = provenance.read_json(provenance.VENDOR_PROVENANCE_PATH)
        changed = dict(lock)
        changed["commit"] = "0" * 40
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_vendored_identity(changed, vendor_marker)

    def test_validation_rejects_marker_mismatch(self) -> None:
        lock = provenance.load_upstream_pin()
        marker = provenance.read_json(provenance.PROVENANCE_PATH)
        digest, files = provenance.source_digest()
        changed = dict(marker)
        changed["source_commit"] = "0" * 40
        with self.assertRaises(provenance.ProvenanceError):
            provenance.validate_provenance(lock, changed, digest=digest, file_count=len(files))

    def test_upstream_binding_compares_independently_resolved_git_blobs(self) -> None:
        commit = "1" * 40
        root_tree = "2" * 40
        first_tree = "3" * 40
        app_tree = "4" * 40
        frontend_tree = "5" * 40
        blob_a = "6" * 40
        nested_tree = "7" * 40
        blob_b = "8" * 40
        lock = {
            "repository": "HITsz-TMG/VideoClaw",
            "commit": commit,
            "subtree": "video-claw/video-claw",
            "license": "MIT",
        }

        def fake_github_json(url: str):
            if url.endswith(f"/commits/{commit}"):
                return {"sha": commit, "commit": {"tree": {"sha": root_tree}}}
            if url.endswith(f"/git/trees/{root_tree}"):
                return {
                    "sha": root_tree,
                    "truncated": False,
                    "tree": [{"path": "video-claw", "mode": "040000", "type": "tree", "sha": first_tree}],
                }
            if url.endswith(f"/git/trees/{first_tree}"):
                return {
                    "sha": first_tree,
                    "truncated": False,
                    "tree": [{"path": "video-claw", "mode": "040000", "type": "tree", "sha": app_tree}],
                }
            if url.endswith(f"/git/trees/{app_tree}"):
                return {
                    "sha": app_tree,
                    "truncated": False,
                    "tree": [{"path": "frontend", "mode": "040000", "type": "tree", "sha": frontend_tree}],
                }
            if url.endswith(f"/git/trees/{frontend_tree}?recursive=1"):
                return {
                    "sha": frontend_tree,
                    "truncated": False,
                    "tree": [
                        {"path": "a.txt", "mode": "100644", "type": "blob", "sha": blob_a},
                        {"path": "nested", "mode": "040000", "type": "tree", "sha": nested_tree},
                        {"path": "nested/b.txt", "mode": "100755", "type": "blob", "sha": blob_b},
                    ],
                }
            self.fail(f"unexpected GitHub URL: {url}")

        local_entries = [
            ("a.txt", "100644", blob_a),
            ("nested/b.txt", "100755", blob_b),
        ]
        with mock.patch.object(provenance, "github_json", side_effect=fake_github_json):
            self.assertEqual(provenance.validate_upstream_snapshot(lock, local_entries), frontend_tree)
            changed_entries = [
                ("a.txt", "100644", "9" * 40),
                ("nested/b.txt", "100755", blob_b),
            ]
            with self.assertRaises(provenance.ProvenanceError):
                provenance.validate_upstream_snapshot(lock, changed_entries)

    def test_synchronized_local_commit_forgery_still_requires_upstream_resolution(self) -> None:
        lock = provenance.load_upstream_pin()
        vendor_marker = provenance.read_json(provenance.VENDOR_PROVENANCE_PATH)
        marker = provenance.read_json(provenance.PROVENANCE_PATH)
        entries = provenance.source_entries()
        digest, files = provenance.source_digest(entries)

        forged_commit = "0" * 40
        forged_lock = dict(lock)
        forged_lock["commit"] = forged_commit
        forged_vendor = dict(vendor_marker)
        forged_vendor["commit"] = forged_commit
        forged_marker = dict(marker)
        forged_marker["source_commit"] = forged_commit

        provenance.validate_vendored_identity(forged_lock, forged_vendor)
        provenance.validate_provenance(forged_lock, forged_marker, digest=digest, file_count=len(files))
        with mock.patch.object(
            provenance,
            "github_json",
            side_effect=provenance.ProvenanceError("independent upstream commit did not resolve"),
        ):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.validate_upstream_snapshot(forged_lock, entries)

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
