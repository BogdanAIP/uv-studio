from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.diagnostics import DIAGNOSTICS_SCHEMA_VERSION, build_diagnostics
from uv_studio.projects.maintenance import MIGRATION_RECOVERY_MANIFEST
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "release"
        self.root.mkdir()
        self.payloads = {
            "backend/uv-studio-server.exe": b"backend-runtime",
            "frontend/server.js": b"frontend-runtime",
            "runtime/node/node.exe": b"node-runtime",
            "media/ffmpeg.exe": b"ffmpeg-runtime",
            "media/ffprobe.exe": b"ffprobe-runtime",
            "media/melt.exe": b"mlt-runtime",
        }
        for relative, body in self.payloads.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        self.components = (
            ReleaseComponent("backend", "0.1.0", "backend/uv-studio-server.exe"),
            ReleaseComponent("frontend", "16.2.12", "frontend/server.js"),
            ReleaseComponent("node", "20.0.0", "runtime/node/node.exe"),
            ReleaseComponent("ffmpeg", "test", "media/ffmpeg.exe"),
            ReleaseComponent("ffprobe", "test", "media/ffprobe.exe"),
            ReleaseComponent("mlt", "test", "media/melt.exe"),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_manifest(self) -> None:
        manifest = build_release_manifest(
            self.root,
            product_version="0.1.0",
            build_id="diagnostics-test",
            target_arch="x86_64",
            components=self.components,
        )
        write_release_manifest(manifest, self.root)

    def _storage_environment(self, user_data: Path) -> dict[str, str]:
        return {
            "UV_STUDIO_RELEASE_ROOT": "",
            "UV_STUDIO_USER_DATA_DIR": str(user_data),
            "UV_STUDIO_PROJECTS_DIR": str(Path(self.tmp.name) / "projects"),
            "UV_STUDIO_CONFIG_DIR": str(Path(self.tmp.name) / "config"),
        }

    def _write_recovery_snapshot(
        self,
        user_data: Path,
        *,
        set_id: str,
        created_at: str,
    ) -> Path:
        root = user_data / "recovery" / "migrations" / set_id
        project_id = "diagnostics-project"
        relative = f"projects/{project_id}/project.json"
        payload = b'{"schema_version":1}\n'
        project_file = root / relative
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_bytes(payload)
        manifest = {
            "recovery_schema_version": 1,
            "set_id": set_id,
            "created_at": created_at,
            "reason": "project-schema-migration-to-v2",
            "target_project_schema_version": 2,
            "projects": [
                {
                    "project_id": project_id,
                    "path": relative,
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "source_schema_version": 1,
                }
            ],
        }
        (root / MIGRATION_RECOVERY_MANIFEST).write_text(
            json.dumps(manifest, sort_keys=True),
            encoding="utf-8",
        )
        return root

    def test_development_diagnostics_do_not_expose_secret_or_absolute_tool_paths(self) -> None:
        with mock.patch.dict(os.environ, {"UV_STUDIO_RELEASE_ROOT": ""}, clear=False):
            snapshot = build_diagnostics(
                tool_lookup=lambda tool: f"/private/developer/bin/{tool}"
            )
        self.assertEqual(snapshot["schema_version"], DIAGNOSTICS_SCHEMA_VERSION)
        self.assertEqual(snapshot["mode"], "development")
        self.assertEqual(snapshot["overall_status"], "ok")
        self.assertFalse(snapshot["storage"]["probe_performed"])
        self.assertFalse(snapshot["recovery"]["checked"])
        encoded = json.dumps(snapshot, sort_keys=True).lower()
        self.assertNotIn("/private/developer", encoded)
        self.assertNotIn("api_key", encoded)
        self.assertNotIn("bearer ", encoded)
        self.assertNotIn("secret_status", encoded)

    def test_packaged_diagnostics_deep_verify_exact_manifest(self) -> None:
        self._write_manifest()
        with mock.patch.dict(
            os.environ,
            {"UV_STUDIO_RELEASE_ROOT": str(self.root)},
            clear=False,
        ):
            snapshot = build_diagnostics(verify_release=True, tool_lookup=lambda _: None)
        self.assertEqual(snapshot["mode"], "packaged")
        self.assertEqual(snapshot["overall_status"], "ok")
        self.assertTrue(snapshot["release"]["manifest_valid"])
        self.assertTrue(snapshot["release"]["integrity"]["ok"])
        self.assertTrue(snapshot["release"]["integrity"]["verify_hashes"])
        self.assertEqual(snapshot["release"]["build_id"], "diagnostics-test")
        self.assertEqual(snapshot["release"]["components"]["ffmpeg"]["entrypoint"], "media/ffmpeg.exe")
        self.assertTrue(snapshot["media_tools"]["ffmpeg"]["available"])
        self.assertEqual(snapshot["media_tools"]["ffmpeg"]["source"], "release_manifest")

    def test_packaged_diagnostics_fail_closed_on_corrupt_manifest(self) -> None:
        (self.root / "release-manifest.json").write_text("{not json", encoding="utf-8")
        with mock.patch.dict(
            os.environ,
            {"UV_STUDIO_RELEASE_ROOT": str(self.root)},
            clear=False,
        ):
            snapshot = build_diagnostics(verify_release=True, tool_lookup=lambda _: None)
        self.assertEqual(snapshot["overall_status"], "invalid_release")
        self.assertFalse(snapshot["release"]["manifest_valid"])
        self.assertFalse(snapshot["release"]["integrity"]["ok"])
        self.assertTrue(snapshot["release"]["problems"])

    def test_packaged_diagnostics_report_same_size_substitution_on_deep_check(self) -> None:
        self._write_manifest()
        target = self.root / "media" / "ffprobe.exe"
        target.write_bytes(b"X" * len(self.payloads["media/ffprobe.exe"]))
        with mock.patch.dict(
            os.environ,
            {"UV_STUDIO_RELEASE_ROOT": str(self.root)},
            clear=False,
        ):
            shallow = build_diagnostics(verify_release=False, tool_lookup=lambda _: None)
            deep = build_diagnostics(verify_release=True, tool_lookup=lambda _: None)
        self.assertEqual(shallow["overall_status"], "ok")
        self.assertEqual(deep["overall_status"], "invalid_release")
        self.assertTrue(any("sha256 mismatch" in item for item in deep["release"]["problems"]))

    def test_storage_probe_is_secret_safe_writable_and_leaves_no_marker(self) -> None:
        user_data = Path(self.tmp.name) / "user-data-private-path"
        environment = self._storage_environment(user_data)
        with mock.patch.dict(os.environ, environment, clear=False):
            snapshot = build_diagnostics(
                probe_storage=True,
                tool_lookup=lambda tool: f"/private/developer/bin/{tool}",
            )

        self.assertEqual(snapshot["overall_status"], "ok")
        self.assertTrue(snapshot["storage"]["probe_performed"])
        for key in ("user_data", "project_store", "configuration"):
            self.assertTrue(snapshot["storage"][key]["writable"])
            self.assertIsInstance(snapshot["storage"][key]["free_bytes"], int)
            self.assertGreaterEqual(snapshot["storage"][key]["free_bytes"], 0)
        self.assertTrue(snapshot["recovery"]["checked"])
        self.assertEqual(snapshot["recovery"]["snapshot_count"], 0)
        self.assertEqual(snapshot["issues"], [])
        self.assertEqual(list(Path(self.tmp.name).rglob(".uv-diagnostics-*.tmp")), [])

        encoded = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn(str(Path(self.tmp.name)), encoded)
        self.assertNotIn("user-data-private-path", encoded)

    def test_storage_probe_reports_recovery_validation_without_exposing_snapshot_paths(self) -> None:
        user_data = Path(self.tmp.name) / "user-data-recovery-private"
        environment = self._storage_environment(user_data)
        valid = self._write_recovery_snapshot(
            user_data,
            set_id="schema-v2-valid",
            created_at="2026-08-17T12:00:00+00:00",
        )
        recovery_root = valid.parent
        broken = recovery_root / "schema-v2-broken"
        broken.mkdir()
        (broken / MIGRATION_RECOVERY_MANIFEST).write_text("{broken", encoding="utf-8")
        (recovery_root / ".schema-v2-crashed.staging").mkdir()

        with mock.patch.dict(os.environ, environment, clear=False):
            snapshot = build_diagnostics(
                probe_storage=True,
                tool_lookup=lambda tool: f"/private/developer/bin/{tool}",
            )

        recovery = snapshot["recovery"]
        self.assertTrue(recovery["checked"])
        self.assertEqual(recovery["snapshot_count"], 2)
        self.assertEqual(recovery["valid_snapshot_count"], 1)
        self.assertEqual(recovery["invalid_snapshot_count"], 1)
        self.assertEqual(recovery["incomplete_staging_count"], 1)
        self.assertEqual(recovery["latest_created_at"], "2026-08-17T12:00:00+00:00")
        self.assertEqual(snapshot["overall_status"], "degraded")
        codes = {issue["code"] for issue in snapshot["issues"]}
        self.assertIn("recovery.invalid_snapshots", codes)
        self.assertIn("recovery.incomplete_staging", codes)
        encoded = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn(str(recovery_root), encoded)
        self.assertNotIn("schema-v2-valid", encoded)
        self.assertNotIn("schema-v2-broken", encoded)


if __name__ == "__main__":
    unittest.main()
