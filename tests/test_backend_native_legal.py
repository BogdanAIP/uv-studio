from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.backend_native_legal import BackendNativeLegalError, stage_backend_native_legal


def _blob_sha1(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


class BackendNativeLegalTests(unittest.TestCase):
    def _fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        release = root / "release"
        release.mkdir()
        manifest = json.loads(Path("packaging/backend-native-components.windows-x86_64.json").read_text(encoding="utf-8"))
        payloads = {manifest["source_recipe"]["url"]: b"recipe\n"}
        manifest["source_recipe"]["git_blob_sha1"] = _blob_sha1(b"recipe\n")
        for group in manifest["groups"]:
            for relative in group["files"]:
                target = release / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"pe")
            evidence = group["evidence"]
            if evidence["type"] == "remote-license":
                data = (group["id"] + " license\n").encode()
                payloads[evidence["url"]] = data
                evidence["git_blob_sha1"] = _blob_sha1(data)
        component_ids = sorted({group["evidence"]["component_id"] for group in manifest["groups"] if group["evidence"]["type"] == "python-component"})
        python_legal = release / "legal" / "python-runtime"
        python_legal.mkdir(parents=True)
        (python_legal / "components.windows-x86_64.json").write_text(json.dumps({"components": [{"id": component_id, "version": "1", "license_files": [{"path": "legal/example"}]} for component_id in component_ids]}), encoding="utf-8")
        manifest_file = root / "manifest.json"
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        return temporary, release, manifest_file, payloads

    def test_exact_closure_stages(self) -> None:
        temporary, release, manifest, payloads = self._fixture()
        self.addCleanup(temporary.cleanup)
        result = stage_backend_native_legal(release_root=release, manifest_file=manifest, downloader=lambda url: payloads[url])
        self.assertEqual(result["pe_count"], 78)
        self.assertEqual(result["group_count"], 14)
        self.assertTrue((release / "legal" / "backend-native" / "components.windows-x86_64.json").is_file())

    def test_unknown_pe_fails_closed(self) -> None:
        temporary, release, manifest, payloads = self._fixture()
        self.addCleanup(temporary.cleanup)
        (release / "backend" / "_internal" / "unknown.dll").write_bytes(b"unknown")
        with self.assertRaises(BackendNativeLegalError):
            stage_backend_native_legal(release_root=release, manifest_file=manifest, downloader=lambda url: payloads[url])
        self.assertFalse((release / "legal" / "backend-native").exists())

    def test_missing_python_evidence_fails_closed(self) -> None:
        temporary, release, manifest, payloads = self._fixture()
        self.addCleanup(temporary.cleanup)
        (release / "legal" / "python-runtime" / "components.windows-x86_64.json").write_text('{"components":[]}', encoding="utf-8")
        with self.assertRaises(BackendNativeLegalError):
            stage_backend_native_legal(release_root=release, manifest_file=manifest, downloader=lambda url: payloads[url])

    def test_remote_blob_drift_fails_closed(self) -> None:
        temporary, release, manifest, payloads = self._fixture()
        self.addCleanup(temporary.cleanup)
        first = next(group for group in json.loads(manifest.read_text(encoding="utf-8"))["groups"] if group["evidence"]["type"] == "remote-license")
        payloads[first["evidence"]["url"]] = b"drift\n"
        with self.assertRaises(BackendNativeLegalError):
            stage_backend_native_legal(release_root=release, manifest_file=manifest, downloader=lambda url: payloads[url])


if __name__ == "__main__":
    unittest.main()
