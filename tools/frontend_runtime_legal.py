#!/usr/bin/env python3
"""Inventory and stage legal evidence for the exact Next standalone runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Sequence

_LICENSE_NAME_RE = re.compile(r"^(license|licence|copying|notice)(?:[._-].*)?$", re.IGNORECASE)
_MAX_LICENSE_FILE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_LICENSE_BYTES = 16 * 1024 * 1024


class FrontendRuntimeLegalError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_package_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise FrontendRuntimeLegalError(f"{label} package.json must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FrontendRuntimeLegalError(f"{label} package.json is invalid") from exc
    if not isinstance(value, dict):
        raise FrontendRuntimeLegalError(f"{label} package.json root must be an object")
    return value


def _safe_slug(name: str, version: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9.+_-]+", "-", f"{name}-{version}").strip("-").lower()
    if not slug or not re.fullmatch(r"[a-z0-9][a-z0-9.+_-]*", slug):
        raise FrontendRuntimeLegalError(f"unsafe frontend legal component id: {name}@{version}")
    return slug


def _direct_package_roots(node_modules: Path) -> list[Path]:
    if node_modules.is_symlink() or not node_modules.is_dir():
        raise FrontendRuntimeLegalError("staged frontend node_modules must be a real directory")
    result: list[Path] = []
    for entry in sorted(node_modules.iterdir(), key=lambda item: item.name.casefold()):
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.name.startswith("@"):
            for package in sorted(entry.iterdir(), key=lambda item: item.name.casefold()):
                if not package.is_symlink() and package.is_dir() and (package / "package.json").is_file():
                    result.append(package)
        elif (entry / "package.json").is_file():
            result.append(entry)
    return result


def _license_files(package_root: Path) -> list[Path]:
    result: list[Path] = []
    for entry in sorted(package_root.iterdir(), key=lambda item: item.name.casefold()):
        if entry.is_symlink() or not entry.is_file():
            continue
        if _LICENSE_NAME_RE.fullmatch(entry.name) is None:
            continue
        size = entry.stat().st_size
        if size <= 0 or size > _MAX_LICENSE_FILE_BYTES:
            raise FrontendRuntimeLegalError(
                f"frontend package has invalid license file size: {package_root.name}/{entry.name}"
            )
        result.append(entry.resolve())
    return result


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


def stage_frontend_runtime_legal_bundle(
    *,
    release_root: Path | str,
    staged_frontend_root: Path | str,
    source_frontend_root: Path | str,
    require_compiled_license_expressions: bool = False,
) -> dict[str, Any]:
    release = Path(release_root)
    staged = Path(staged_frontend_root)
    source = Path(source_frontend_root)
    for candidate, label in (
        (release, "release root"),
        (staged, "staged frontend root"),
        (source, "source frontend root"),
    ):
        if candidate.is_symlink() or not candidate.is_dir():
            raise FrontendRuntimeLegalError(f"{label} must be a real directory")

    staged_modules = staged / "node_modules"
    source_modules = source / "node_modules"
    package_roots = _direct_package_roots(staged_modules)
    if not package_roots:
        raise FrontendRuntimeLegalError("Next standalone runtime contains no direct packages")

    legal_root = release / "legal" / "frontend-runtime"
    if legal_root.exists() or legal_root.is_symlink():
        raise FrontendRuntimeLegalError("frontend runtime legal output already exists")

    direct: list[dict[str, Any]] = []
    compiled: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        licenses_root = legal_root / "licenses"
        licenses_root.mkdir(parents=True)
        for package_root in package_roots:
            relative = package_root.relative_to(staged_modules)
            staged_package = _read_package_json(package_root / "package.json", relative.as_posix())
            name = staged_package.get("name")
            version = staged_package.get("version")
            license_expression = staged_package.get("license")
            if not isinstance(name, str) or not name:
                raise FrontendRuntimeLegalError(f"{relative.as_posix()}: package name is missing")
            if not isinstance(version, str) or not version:
                raise FrontendRuntimeLegalError(f"{name}: package version is missing")
            if not isinstance(license_expression, str) or not license_expression.strip():
                raise FrontendRuntimeLegalError(f"{name}@{version}: license expression is missing")

            source_root = source_modules.joinpath(*relative.parts)
            source_package = _read_package_json(source_root / "package.json", f"source {name}")
            if source_package.get("name") != name or source_package.get("version") != version:
                raise FrontendRuntimeLegalError(
                    f"source/staged package identity mismatch for {name}@{version}"
                )
            sources = _license_files(source_root)
            if not sources:
                raise FrontendRuntimeLegalError(
                    f"standalone package has no source license/notice file: {name}@{version}"
                )
            component_dir = licenses_root / _safe_slug(name, version)
            component_dir.mkdir()
            evidence: list[dict[str, Any]] = []
            for license_file in sources:
                target = component_dir / license_file.name
                shutil.copy2(license_file, target)
                total_bytes += target.stat().st_size
                if total_bytes > _MAX_TOTAL_LICENSE_BYTES:
                    raise FrontendRuntimeLegalError("frontend runtime legal bundle exceeded size limit")
                evidence.append(
                    {
                        "path": target.relative_to(release).as_posix(),
                        "bytes": target.stat().st_size,
                        "sha256": _sha256(target),
                    }
                )
            direct.append(
                {
                    "name": name,
                    "version": version,
                    "license_expression": license_expression.strip(),
                    "runtime_path": "frontend/node_modules/" + relative.as_posix(),
                    "license_files": evidence,
                }
            )

        next_root = staged_modules / "next" / "dist" / "compiled"
        missing_expressions: list[str] = []
        if next_root.is_dir() and not next_root.is_symlink():
            for package_json in sorted(next_root.rglob("package.json"), key=lambda item: item.as_posix().casefold()):
                if package_json.is_symlink() or not package_json.is_file():
                    raise FrontendRuntimeLegalError("Next compiled inventory contains invalid package.json")
                package = _read_package_json(package_json, "Next compiled")
                relative = package_json.relative_to(staged).as_posix()
                name = package.get("name")
                version = package.get("version")
                license_expression = package.get("license")
                if not isinstance(name, str) or not name:
                    raise FrontendRuntimeLegalError(f"{relative}: compiled package name is missing")
                if not isinstance(license_expression, str) or not license_expression.strip():
                    missing_expressions.append(relative)
                compiled.append(
                    {
                        "name": name,
                        "version": version if isinstance(version, str) and version else None,
                        "license_expression": (
                            license_expression.strip()
                            if isinstance(license_expression, str) and license_expression.strip()
                            else None
                        ),
                        "package_json_path": "frontend/" + relative,
                        "package_json_sha256": _sha256(package_json),
                    }
                )
        if require_compiled_license_expressions and missing_expressions:
            raise FrontendRuntimeLegalError(
                "Next compiled packages missing license expression: " + ", ".join(missing_expressions)
            )

        manifest = {
            "schema_version": 1,
            "platform": "windows-x86_64",
            "direct_package_count": len(direct),
            "next_compiled_package_count": len(compiled),
            "next_compiled_missing_license_expression_count": len(missing_expressions),
            "next_compiled_missing_license_expression_paths": missing_expressions,
            "direct_packages": sorted(direct, key=lambda item: item["name"].casefold()),
            "next_compiled_packages": compiled,
        }
        _atomic_json(legal_root / "components.windows-x86_64.json", manifest)
    except Exception:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise

    return {
        "ok": True,
        "direct_package_count": len(direct),
        "next_compiled_package_count": len(compiled),
        "next_compiled_missing_license_expression_count": len(missing_expressions),
        "license_bytes": total_bytes,
        "manifest": "legal/frontend-runtime/components.windows-x86_64.json",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--staged-frontend-root", type=Path, required=True)
    parser.add_argument("--source-frontend-root", type=Path, required=True)
    parser.add_argument("--require-compiled-license-expressions", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_frontend_runtime_legal_bundle(
            release_root=args.release_root,
            staged_frontend_root=args.staged_frontend_root,
            source_frontend_root=args.source_frontend_root,
            require_compiled_license_expressions=args.require_compiled_license_expressions,
        )
    except (OSError, UnicodeError, FrontendRuntimeLegalError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
