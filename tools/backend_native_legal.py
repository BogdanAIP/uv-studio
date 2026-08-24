#!/usr/bin/env python3
"""Validate and stage legal/provenance evidence for the frozen Windows backend native closure."""
from __future__ import annotations
import argparse, hashlib, json, shutil, urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "packaging" / "backend-native-components.windows-x86_64.json"
MAX_REMOTE_BYTES = 256 * 1024

class BackendNativeLegalError(RuntimeError):
    pass

def _git_blob_sha1(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BackendNativeLegalError("unsafe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or path.as_posix() != value:
        raise BackendNativeLegalError("unsafe relative path")
    return value

def _download(url: str) -> bytes:
    if not url.startswith("https://raw.githubusercontent.com/"):
        raise BackendNativeLegalError("remote evidence must use raw.githubusercontent.com HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "UV-Studio-release-audit/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(MAX_REMOTE_BYTES + 1)
    if not data or len(data) > MAX_REMOTE_BYTES:
        raise BackendNativeLegalError("remote evidence size invalid")
    return data

def _load_python_components(release: Path) -> dict[str, dict[str, Any]]:
    path = release / "legal" / "python-runtime" / "components.windows-x86_64.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackendNativeLegalError("python runtime legal manifest is missing or invalid") from exc
    components = raw.get("components")
    if not isinstance(components, list):
        raise BackendNativeLegalError("python runtime legal manifest components invalid")
    return {item["id"]: item for item in components if isinstance(item, dict) and isinstance(item.get("id"), str)}

def stage_backend_native_legal(*, release_root: Path | str, manifest_file: Path | str = DEFAULT_MANIFEST, downloader: Callable[[str], bytes] = _download) -> dict[str, Any]:
    release = Path(release_root)
    backend = release / "backend"
    if release.is_symlink() or not release.is_dir() or backend.is_symlink() or not backend.is_dir():
        raise BackendNativeLegalError("release/backend roots must be real directories")
    try:
        raw = json.loads(Path(manifest_file).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackendNativeLegalError("backend native manifest invalid") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "platform", "expected_pe_count", "source_recipe", "groups"} or raw["schema_version"] != 1 or raw["platform"] != "windows-x86_64":
        raise BackendNativeLegalError("backend native manifest shape invalid")
    groups = raw["groups"]
    expected = raw["expected_pe_count"]
    if not isinstance(expected, int) or expected <= 0 or not isinstance(groups, list) or not groups:
        raise BackendNativeLegalError("backend native manifest counts invalid")
    actual = sorted(path.relative_to(release).as_posix() for path in backend.rglob("*") if path.is_file() and not path.is_symlink() and path.suffix.lower() in {".exe", ".dll", ".pyd"})
    assigned: dict[str, str] = {}
    normalized: list[tuple[str, list[str], dict[str, Any]]] = []
    for group in groups:
        if not isinstance(group, dict) or set(group) != {"id", "files", "evidence"}:
            raise BackendNativeLegalError("backend native group shape invalid")
        group_id, files, evidence = group["id"], group["files"], group["evidence"]
        if not isinstance(group_id, str) or not group_id or not isinstance(files, list) or not files or not isinstance(evidence, dict):
            raise BackendNativeLegalError("backend native group invalid")
        clean: list[str] = []
        for relative in files:
            relative = _relative(relative)
            if not relative.startswith("backend/") or relative in assigned:
                raise BackendNativeLegalError(f"backend native path duplicate/outside backend: {relative}")
            assigned[relative] = group_id
            clean.append(relative)
        normalized.append((group_id, clean, evidence))
    if len(assigned) != expected or sorted(assigned) != actual:
        unlisted = sorted(set(actual) - set(assigned))
        stale = sorted(set(assigned) - set(actual))
        raise BackendNativeLegalError(f"backend native coverage drifted: actual={len(actual)} mapped={len(assigned)} unlisted={unlisted} stale={stale}")
    python_components = _load_python_components(release)
    legal_root = release / "legal" / "backend-native"
    if legal_root.exists() or legal_root.is_symlink():
        raise BackendNativeLegalError("backend native legal output already exists")
    try:
        legal_root.mkdir(parents=True)
        recipe = raw["source_recipe"]
        if not isinstance(recipe, dict) or set(recipe) != {"url", "git_blob_sha1", "versions"}:
            raise BackendNativeLegalError("source recipe shape invalid")
        recipe_data = downloader(recipe["url"])
        if _git_blob_sha1(recipe_data) != recipe["git_blob_sha1"]:
            raise BackendNativeLegalError("CPython source recipe Git blob drifted")
        recipe_target = legal_root / "CPython-PCbuild-get_externals.bat"
        recipe_target.write_bytes(recipe_data)
        staged = []
        for group_id, files, evidence in normalized:
            evidence_type = evidence.get("type")
            item: dict[str, Any] = {"id": group_id, "files": files, "file_count": len(files)}
            if evidence_type == "uv-owned":
                if set(evidence) != {"type"}:
                    raise BackendNativeLegalError(f"{group_id}: uv-owned evidence shape invalid")
                item["evidence"] = evidence
            elif evidence_type == "python-component":
                component_id = evidence.get("component_id")
                if set(evidence) != {"type", "component_id"} or component_id not in python_components:
                    raise BackendNativeLegalError(f"{group_id}: missing Python legal component")
                component = python_components[component_id]
                if not component.get("license_files"):
                    raise BackendNativeLegalError(f"{group_id}: Python legal component has no license files")
                item["evidence"] = {"type": "python-component", "component_id": component_id, "version": component.get("version"), "license_files": component["license_files"]}
            elif evidence_type == "remote-license":
                if set(evidence) != {"type", "license_expression", "url", "git_blob_sha1"}:
                    raise BackendNativeLegalError(f"{group_id}: remote evidence shape invalid")
                data = downloader(evidence["url"])
                if _git_blob_sha1(data) != evidence["git_blob_sha1"]:
                    raise BackendNativeLegalError(f"{group_id}: remote license Git blob drifted")
                target = legal_root / f"{group_id}-LICENSE.txt"
                target.write_bytes(data)
                item["evidence"] = {**evidence, "staged_path": target.relative_to(release).as_posix(), "bytes": len(data), "sha256": _sha256(data)}
            else:
                raise BackendNativeLegalError(f"{group_id}: unknown evidence type")
            staged.append(item)
        output = {"schema_version": 1, "platform": "windows-x86_64", "pe_count": len(actual), "group_count": len(staged), "source_recipe": {**recipe, "staged_path": recipe_target.relative_to(release).as_posix(), "bytes": len(recipe_data), "sha256": _sha256(recipe_data)}, "groups": staged}
        manifest_target = legal_root / "components.windows-x86_64.json"
        manifest_target.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    except Exception:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise
    return {"ok": True, "pe_count": len(actual), "group_count": len(staged), "manifest": "legal/backend-native/components.windows-x86_64.json"}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        result = stage_backend_native_legal(release_root=args.release_root, manifest_file=args.manifest)
    except (OSError, BackendNativeLegalError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
