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
        local_tree = provenance.local_source_tree_sha()
        vendor_license_blob = provenance.local_tracked_blob_sha(
            provenance.UPSTREAM_LICENSE,
            label="Pinned VideoClaw UPSTREAM_LICENSE",
        )
        with mock.patch.object(
            provenance,
            "validate_upstream_snapshot",
            return_value=(local_tree, vendor_license_blob),
        ):
            result = provenance.verify()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "read-only")
        self.assertEqual(len(result["source_commit"]), 40)
        self.assertGreater(result["source_file_count"], 0)
        self.assertEqual(len(result["source_tree_sha256"]), 64)
        self.assertEqual(result["local_frontend_tree_sha"], local_tree)
        self.assertEqual(result["upstream_frontend_tree_sha"], local_tree)
        self.assertEqual(result["upstream_license_blob_sha"], vendor_license_blob)

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

    def test_upstream_evidence_walks_exact_commit_frontend_and_license(self) -> None:
        commit = "1" * 40
        root_tree = "2" * 40
        first_tree = "3" * 40
        app_tree = "4" * 40
        frontend_tree = "5" * 40
        license_blob = "6" * 40
        lock = {
            "repository": "HITsz-TMG/VideoClaw",
            "commit": commit,
            "subtree": "video-claw/video-claw",
            "license": "MIT",
            "license_path": "LICENSE",
        }

        def fake_github_json(url: str):
            if url.endswith(f"/git/commits/{commit}"):
                return {"sha": commit, "tree": {"sha": root_tree}}
            if url.endswith(f"/git/trees/{root_tree}"):
                return {
                    "sha": root_tree,
                    "truncated": False,
                    "tree": [
                        {"path": "LICENSE", "mode": "100644", "type": "blob", "sha": license_blob},
                        {"path": "video-claw", "mode": "040000", "type": "tree", "sha": first_tree},
                    ],
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
            self.fail(f"unexpected GitHub URL: {url}")

        with mock.patch.object(provenance, "github_json", side_effect=fake_github_json):
            self.assertEqual(
                provenance.resolve_upstream_evidence(lock),
                (frontend_tree, license_blob),
            )
            self.assertEqual(
                provenance.validate_upstream_snapshot(
                    lock,
                    local_tree_sha=frontend_tree,
                    vendor_license_blob_sha=license_blob,
                    frontend_license_blob_sha=license_blob,
                ),
                (frontend_tree, license_blob),
            )

    def test_upstream_binding_rejects_frontend_tree_mismatch(self) -> None:
        lock = provenance.load_upstream_pin()
        local_license = "6" * 40
        with mock.patch.object(
            provenance,
            "resolve_upstream_evidence",
            return_value=("5" * 40, local_license),
        ):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.validate_upstream_snapshot(
                    lock,
                    local_tree_sha="9" * 40,
                    vendor_license_blob_sha=local_license,
                    frontend_license_blob_sha=local_license,
                )

    def test_synchronized_local_license_forgery_is_rejected(self) -> None:
        lock = provenance.load_upstream_pin()
        local_tree = "5" * 40
        forged_local_license = "9" * 40
        real_upstream_license = "6" * 40
        with mock.patch.object(
            provenance,
            "resolve_upstream_evidence",
            return_value=(local_tree, real_upstream_license),
        ):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.validate_upstream_snapshot(
                    lock,
                    local_tree_sha=local_tree,
                    vendor_license_blob_sha=forged_local_license,
                    frontend_license_blob_sha=forged_local_license,
                )

    def test_synchronized_local_commit_forgery_still_requires_upstream_resolution(self) -> None:
        lock = provenance.load_upstream_pin()
        vendor_marker = provenance.read_json(provenance.VENDOR_PROVENANCE_PATH)
        marker = provenance.read_json(provenance.PROVENANCE_PATH)
        digest, files = provenance.source_digest()

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
            "resolve_upstream_evidence",
            side_effect=provenance.ProvenanceError("independent upstream commit did not resolve"),
        ):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.validate_upstream_snapshot(
                    forged_lock,
                    local_tree_sha=provenance.local_source_tree_sha(),
                    vendor_license_blob_sha=provenance.local_tracked_blob_sha(
                        provenance.UPSTREAM_LICENSE,
                        label="Pinned VideoClaw UPSTREAM_LICENSE",
                    ),
                    frontend_license_blob_sha=provenance.local_tracked_blob_sha(
                        provenance.FRONTEND_LICENSE,
                        label="frontend/UPSTREAM_LICENSE",
                    ),
                )

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
