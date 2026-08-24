#!/usr/bin/env python3
"""Stage exact legal/provenance evidence for vendored or adapted source-code donors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MANIFEST = ROOT / "packaging" / "source-code-notices.windows-x86_64.json"
_SCAN_ROOTS = ("vendor", "third_party")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MAX_FILE_BYTES = 2 * 1024 * 1024


class SourceCodeLegalError(RuntimeError):
    pass


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SourceCodeLegalError(f"{label} must be a non-empty canonical string")
    if "\r" in value or "\n" in value:
        raise SourceCodeLegalError(f"{label} must not contain line breaks")
    return value


def _relative(value: Any, label: str) -> str:
    raw = _string(value, label)
    if "\\" in raw:
        raise SourceCodeLegalError(f"{label} must use forward slashes")
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise SourceCodeLegalError(f"{label} must be a canonical relative path")
    if path.as_posix() != raw:
        raise SourceCodeLegalError(f"{label} must be canonical")
    return raw


def _git_sha1(value: Any, label: str) -> str:
    raw = _string(value, label)
    if _SHA1_RE.fullmatch(raw) is None:
        raise SourceCodeLegalError(f"{label} must be 40 lowercase hexadecimal characters")
    return raw


def _regular_repo_file(root: Path, relative: str, label: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    if candidate.is_symlink():
        raise SourceCodeLegalError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        repo = root.resolve(strict=True)
    except OSError as exc:
        raise SourceCodeLegalError(f"{label} is missing") from exc
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise SourceCodeLegalError(f"{label} escapes repository root") from exc
    if not resolved.is_file():
        raise SourceCodeLegalError(f"{label} must be a regular file")
    size = resolved.stat().st_size
    if size <= 0 or size > _MAX_FILE_BYTES:
        raise SourceCodeLegalError(f"{label} has invalid size")
    return resolved


def _actual_source_roots(root: Path) -> set[str]:
    result: set[str] = set()
    for scan_root in _SCAN_ROOTS:
        directory = root / scan_root
        if not directory.exists():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise SourceCodeLegalError(f"{scan_root}/ must be a real directory")
        for entry in directory.iterdir():
            if entry.is_symlink():
                raise SourceCodeLegalError(f"{scan_root}/ contains symlink: {entry.name}")
            if entry.is_dir():
                result.add(f"{scan_root}/{entry.name}")
    return result


def _load_manifest(path: Path, repository_root: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise SourceCodeLegalError("source-code notice manifest must be a regular file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceCodeLegalError("source-code notice manifest is invalid JSON") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "components"}:
        raise SourceCodeLegalError("source-code notice manifest has unexpected fields")
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise SourceCodeLegalError("source-code notice manifest schema_version must be integer 1")
    if not isinstance(raw["components"], list) or not raw["components"]:
        raise SourceCodeLegalError("source-code notice manifest components must be a non-empty array")

    expected_fields = {
        "id",
        "source_root",
        "repository",
        "revision",
        "license_expression",
        "license_file",
        "license_git_blob_sha1",
        "provenance_file",
        "provenance_git_blob_sha1",
    }
    components: list[dict[str, Any]] = []
    ids: set[str] = set()
    roots: set[str] = set()
    for index, item in enumerate(raw["components"]):
        if not isinstance(item, dict) or set(item) != expected_fields:
            raise SourceCodeLegalError(f"source-code component[{index}] has unexpected fields")
        component_id = _string(item["id"], f"component[{index}].id")
        if _ID_RE.fullmatch(component_id) is None or component_id in ids:
            raise SourceCodeLegalError(f"component[{index}].id is unsafe or duplicate")
        ids.add(component_id)
        source_root = _relative(item["source_root"], f"component[{index}].source_root")
        if source_root in roots or source_root.split("/", 1)[0] not in _SCAN_ROOTS:
            raise SourceCodeLegalError(f"component[{index}].source_root is duplicate or outside audited roots")
        roots.add(source_root)
        item["repository"] = _string(item["repository"], f"component[{index}].repository")
        item["revision"] = _git_sha1(item["revision"], f"component[{index}].revision")
        item["license_expression"] = _string(
            item["license_expression"], f"component[{index}].license_expression"
        )
        item["license_file"] = _relative(item["license_file"], f"component[{index}].license_file")
        item["license_git_blob_sha1"] = _git_sha1(
            item["license_git_blob_sha1"], f"component[{index}].license_git_blob_sha1"
        )
        if not item["license_file"].startswith(source_root + "/"):
            raise SourceCodeLegalError(f"component[{index}].license_file must be inside source_root")

        provenance_file = item["provenance_file"]
        provenance_sha = item["provenance_git_blob_sha1"]
        if provenance_file is None or provenance_sha is None:
            if provenance_file is not None or provenance_sha is not None:
                raise SourceCodeLegalError(
                    f"component[{index}] provenance file/hash must be both present or both null"
                )
            item["provenance_file"] = None
            item["provenance_git_blob_sha1"] = None
        else:
            item["provenance_file"] = _relative(
                provenance_file, f"component[{index}].provenance_file"
            )
            item["provenance_git_blob_sha1"] = _git_sha1(
                provenance_sha, f"component[{index}].provenance_git_blob_sha1"
            )
            if not item["provenance_file"].startswith(source_root + "/"):
                raise SourceCodeLegalError(
                    f"component[{index}].provenance_file must be inside source_root"
                )
        components.append(item)

    actual_roots = _actual_source_roots(repository_root)
    if roots != actual_roots:
        missing = sorted(actual_roots - roots)
        stale = sorted(roots - actual_roots)
        raise SourceCodeLegalError(
            f"vendored/adapted source-root coverage drifted: unlisted={missing}, stale={stale}"
        )
    return components


def _validate_videoclaw_provenance(component: dict[str, Any], path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceCodeLegalError("VideoClaw provenance file is invalid JSON") from exc
    expected = {
        "repository": component["repository"],
        "commit": component["revision"],
        "license": component["license_expression"],
        "license_file": Path(component["license_file"]).name,
    }
    if not isinstance(data, dict) or any(data.get(key) != value for key, value in expected.items()):
        raise SourceCodeLegalError("VideoClaw provenance identity does not match source-code notice manifest")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def stage_source_code_legal(
    *,
    output_root: Path | str,
    repository_root: Path | str = ROOT,
    manifest_file: Path | str = _DEFAULT_MANIFEST,
) -> dict[str, Any]:
    output = Path(output_root)
    repo = Path(repository_root)
    if output.is_symlink() or not output.is_dir():
        raise SourceCodeLegalError("release root must be a real directory")
    if repo.is_symlink() or not repo.is_dir():
        raise SourceCodeLegalError("repository root must be a real directory")
    components = _load_manifest(Path(manifest_file), repo)
    legal_root = output / "legal" / "source-code"
    if legal_root.exists() or legal_root.is_symlink():
        raise SourceCodeLegalError("source-code legal output already exists")

    staged: list[dict[str, Any]] = []
    try:
        legal_root.mkdir(parents=True)
        for component in sorted(components, key=lambda item: item["id"]):
            license_source = _regular_repo_file(
                repo, component["license_file"], f"{component['id']} license"
            )
            if _git_blob_sha1(license_source) != component["license_git_blob_sha1"]:
                raise SourceCodeLegalError(f"{component['id']} license Git blob identity drifted")

            component_root = legal_root / component["id"]
            component_root.mkdir()
            license_target = component_root / license_source.name
            shutil.copy2(license_source, license_target)
            entry: dict[str, Any] = {
                "id": component["id"],
                "source_root": component["source_root"],
                "repository": component["repository"],
                "revision": component["revision"],
                "license_expression": component["license_expression"],
                "license_file": {
                    "path": license_target.relative_to(output).as_posix(),
                    "bytes": license_target.stat().st_size,
                    "sha256": _sha256(license_target),
                    "git_blob_sha1": component["license_git_blob_sha1"],
                },
            }
            if component["provenance_file"] is not None:
                provenance_source = _regular_repo_file(
                    repo,
                    component["provenance_file"],
                    f"{component['id']} provenance",
                )
                if _git_blob_sha1(provenance_source) != component["provenance_git_blob_sha1"]:
                    raise SourceCodeLegalError(
                        f"{component['id']} provenance Git blob identity drifted"
                    )
                if component["id"] == "videoclaw":
                    _validate_videoclaw_provenance(component, provenance_source)
                provenance_target = component_root / "upstream.json"
                shutil.copy2(provenance_source, provenance_target)
                entry["provenance_file"] = {
                    "path": provenance_target.relative_to(output).as_posix(),
                    "bytes": provenance_target.stat().st_size,
                    "sha256": _sha256(provenance_target),
                    "git_blob_sha1": component["provenance_git_blob_sha1"],
                }
            else:
                entry["provenance_file"] = None
            staged.append(entry)

        manifest = {
            "schema_version": 1,
            "platform": "windows-x86_64",
            "component_count": len(staged),
            "components": staged,
        }
        _atomic_json(legal_root / "components.windows-x86_64.json", manifest)
    except Exception:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise
    return {
        "ok": True,
        "component_count": len(staged),
        "manifest": "legal/source-code/components.windows-x86_64.json",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_source_code_legal(
            output_root=args.output_root,
            repository_root=args.repository_root,
            manifest_file=args.manifest,
        )
    except (OSError, UnicodeError, SourceCodeLegalError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
