from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.source_code_legal import SourceCodeLegalError, stage_source_code_legal


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def _write_fixture(root: Path) -> Path:
    videoclaw = root / "vendor" / "videoclaw-app"
    videoclaw.mkdir(parents=True)
    video_license = videoclaw / "UPSTREAM_LICENSE"
    video_license.write_text("VideoClaw MIT\n", encoding="utf-8")
    video_provenance = videoclaw / ".uv-upstream.json"
    video_provenance.write_text(
        json.dumps(
            {
                "commit": "5a16ae23a4f1cb6886c44c0205f7b7e52a34c276",
                "file_count": 195,
                "license": "MIT",
                "license_file": "UPSTREAM_LICENSE",
                "repository": "HITsz-TMG/VideoClaw",
                "subtree": "video-claw/video-claw",
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    opencut = root / "third_party" / "opencut-classic"
    opencut.mkdir(parents=True)
    opencut_license = opencut / "LICENSE"
    opencut_license.write_text("OpenCut MIT\n", encoding="utf-8")

    manifest = root / "packaging" / "source-code-notices.windows-x86_64.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "components": [
                    {
                        "id": "videoclaw",
                        "source_root": "vendor/videoclaw-app",
                        "repository": "HITsz-TMG/VideoClaw",
                        "revision": "5a16ae23a4f1cb6886c44c0205f7b7e52a34c276",
                        "license_expression": "MIT",
                        "license_file": "vendor/videoclaw-app/UPSTREAM_LICENSE",
                        "license_git_blob_sha1": _git_blob_sha1(video_license),
                        "provenance_file": "vendor/videoclaw-app/.uv-upstream.json",
                        "provenance_git_blob_sha1": _git_blob_sha1(video_provenance),
                    },
                    {
                        "id": "opencut-classic",
                        "source_root": "third_party/opencut-classic",
                        "repository": "OpenCut-app/opencut-classic",
                        "revision": "cf5e79e919144200294fb9fed22a222592a0aeea",
                        "license_expression": "MIT",
                        "license_file": "third_party/opencut-classic/LICENSE",
                        "license_git_blob_sha1": _git_blob_sha1(opencut_license),
                        "provenance_file": None,
                        "provenance_git_blob_sha1": None,
                    },
                ],
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


class SourceCodeLegalTests(unittest.TestCase):
    def test_exact_two_donor_roots_are_staged_with_license_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = _write_fixture(root)
            release = root / "release"
            release.mkdir()

            result = stage_source_code_legal(
                output_root=release,
                repository_root=root,
                manifest_file=manifest,
            )

            self.assertEqual(result["component_count"], 2)
            legal = release / "legal" / "source-code"
            self.assertTrue((legal / "videoclaw" / "UPSTREAM_LICENSE").is_file())
            self.assertTrue((legal / "videoclaw" / "upstream.json").is_file())
            self.assertTrue((legal / "opencut-classic" / "LICENSE").is_file())
            data = json.loads(
                (legal / "components.windows-x86_64.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["component_count"], 2)
            self.assertEqual(
                {item["id"] for item in data["components"]},
                {"videoclaw", "opencut-classic"},
            )
            for component in data["components"]:
                license_item = component["license_file"]
                self.assertEqual(len(license_item["sha256"]), 64)
                self.assertEqual(len(license_item["git_blob_sha1"]), 40)
                self.assertTrue((release / license_item["path"]).is_file())

    def test_new_unlisted_donor_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = _write_fixture(root)
            (root / "vendor" / "new-donor").mkdir()
            release = root / "release"
            release.mkdir()

            with self.assertRaisesRegex(SourceCodeLegalError, "coverage drifted"):
                stage_source_code_legal(
                    output_root=release,
                    repository_root=root,
                    manifest_file=manifest,
                )
            self.assertFalse((release / "legal" / "source-code").exists())

    def test_stale_manifest_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = _write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["components"].append(
                {
                    "id": "stale",
                    "source_root": "vendor/stale",
                    "repository": "example/stale",
                    "revision": "1" * 40,
                    "license_expression": "MIT",
                    "license_file": "vendor/stale/LICENSE",
                    "license_git_blob_sha1": "2" * 40,
                    "provenance_file": None,
                    "provenance_git_blob_sha1": None,
                }
            )
            manifest.write_text(json.dumps(data), encoding="utf-8")
            release = root / "release"
            release.mkdir()

            with self.assertRaisesRegex(SourceCodeLegalError, "coverage drifted"):
                stage_source_code_legal(
                    output_root=release,
                    repository_root=root,
                    manifest_file=manifest,
                )

    def test_license_blob_drift_fails_closed_and_removes_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = _write_fixture(root)
            (root / "vendor" / "videoclaw-app" / "UPSTREAM_LICENSE").write_text(
                "tampered\n", encoding="utf-8"
            )
            release = root / "release"
            release.mkdir()

            with self.assertRaisesRegex(SourceCodeLegalError, "license Git blob identity drifted"):
                stage_source_code_legal(
                    output_root=release,
                    repository_root=root,
                    manifest_file=manifest,
                )
            self.assertFalse((release / "legal" / "source-code").exists())

    def test_videoclaw_provenance_identity_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = _write_fixture(root)
            provenance = root / "vendor" / "videoclaw-app" / ".uv-upstream.json"
            data = json.loads(provenance.read_text(encoding="utf-8"))
            data["commit"] = "0" * 40
            provenance.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_data["components"][0]["provenance_git_blob_sha1"] = _git_blob_sha1(provenance)
            manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
            release = root / "release"
            release.mkdir()

            with self.assertRaisesRegex(SourceCodeLegalError, "provenance identity"):
                stage_source_code_legal(
                    output_root=release,
                    repository_root=root,
                    manifest_file=manifest,
                )
            self.assertFalse((release / "legal" / "source-code").exists())


if __name__ == "__main__":
    unittest.main()
