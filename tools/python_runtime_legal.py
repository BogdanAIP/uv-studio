#!/usr/bin/env python3
"""Stage exact Python/frozen-backend license evidence into a Windows release."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

_LOCK_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$")
_LICENSE_NAME_RE = re.compile(r"^(license|licence|copying|notice)(?:[._-].*)?$", re.IGNORECASE)
_MAX_LICENSE_FILE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_LICENSE_BYTES = 16 * 1024 * 1024


class PythonRuntimeLegalError(RuntimeError):
    pass


def _canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_exact_lock(lock_file: Path | str) -> dict[str, tuple[str, str]]:
    path = Path(lock_file)
    if path.is_symlink() or not path.is_file():
        raise PythonRuntimeLegalError("Python release lock must be a regular file")
    result: dict[str, tuple[str, str]] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LOCK_RE.fullmatch(line)
        if match is None:
            raise PythonRuntimeLegalError(
                f"Python release lock line {line_number} is not an exact name==version pin"
            )
        display_name, version = match.groups()
        canonical = _canonical_name(display_name)
        if canonical in result:
            raise PythonRuntimeLegalError(f"duplicate Python release lock entry: {display_name}")
        result[canonical] = (display_name, version)
    if not result:
        raise PythonRuntimeLegalError("Python release lock is empty")
    return result


def _safe_component_dir(name: str, version: str) -> str:
    raw = f"{_canonical_name(name)}-{version}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9.+_-]*", raw):
        raise PythonRuntimeLegalError(f"unsafe Python legal component id: {raw}")
    return raw


def _distribution_license_paths(dist: metadata.Distribution) -> list[Path]:
    declared = {
        str(value).replace("\\", "/").casefold()
        for value in (dist.metadata.get_all("License-File") or [])
        if value
    }
    candidates: list[Path] = []
    seen: set[str] = set()
    for file in dist.files or []:
        relative = Path(str(file))
        folded = relative.as_posix().casefold()
        is_declared = folded in declared or any(
            folded.endswith("/" + item) for item in declared
        )
        is_generic = _LICENSE_NAME_RE.fullmatch(relative.name) is not None
        if not (is_declared or is_generic):
            continue
        source = Path(dist.locate_file(file))
        if source.is_symlink() or not source.is_file():
            continue
        resolved = source.resolve()
        key = str(resolved).casefold()
        if key in seen:
            continue
        size = resolved.stat().st_size
        if size <= 0 or size > _MAX_LICENSE_FILE_BYTES:
            raise PythonRuntimeLegalError(
                f"{dist.metadata.get('Name', dist.name)} has invalid license file size: {relative.name}"
            )
        seen.add(key)
        candidates.append(resolved)
    return sorted(candidates, key=lambda item: (item.name.casefold(), str(item).casefold()))


def _license_expression(dist: metadata.Distribution) -> str:
    value = dist.metadata.get("License-Expression") or dist.metadata.get("License")
    if not value or str(value).strip().upper() in {"UNKNOWN", "NONE"}:
        classifiers = [
            item
            for item in (dist.metadata.get_all("Classifier") or [])
            if str(item).startswith("License ::")
        ]
        value = " | ".join(classifiers)
    return str(value or "").strip()


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


def _python_license(explicit: Path | str | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    candidates.extend((Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"))
    for candidate in candidates:
        if candidate.is_symlink():
            continue
        if candidate.is_file() and 0 < candidate.stat().st_size <= _MAX_LICENSE_FILE_BYTES:
            return candidate.resolve()
    raise PythonRuntimeLegalError("CPython runtime license file was not found")


def stage_python_runtime_legal_bundle(
    *,
    release_root: Path | str,
    lock_file: Path | str,
    pyinstaller_version: str,
    python_license_file: Path | str | None = None,
) -> dict[str, Any]:
    release = Path(release_root)
    if release.is_symlink() or not release.is_dir():
        raise PythonRuntimeLegalError("release root must be a real directory")
    if not isinstance(pyinstaller_version, str) or not pyinstaller_version:
        raise PythonRuntimeLegalError("PyInstaller version must be non-empty")

    locked = parse_exact_lock(lock_file)
    requested = list(locked.values()) + [("pyinstaller", pyinstaller_version)]
    canonical_requested = [_canonical_name(name) for name, _ in requested]
    if len(set(canonical_requested)) != len(canonical_requested):
        raise PythonRuntimeLegalError("PyInstaller unexpectedly duplicates shipping lock")

    legal_root = release / "legal" / "python-runtime"
    if legal_root.exists() or legal_root.is_symlink():
        raise PythonRuntimeLegalError("Python runtime legal output already exists")

    components: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        licenses_root = legal_root / "licenses"
        licenses_root.mkdir(parents=True)

        python_version = sys.version.split()[0]
        python_license = _python_license(python_license_file)
        python_target = licenses_root / f"cpython-{python_version}-LICENSE.txt"
        shutil.copy2(python_license, python_target)
        total_bytes += python_target.stat().st_size
        components.append(
            {
                "id": "cpython-runtime",
                "name": "CPython",
                "version": python_version,
                "role": "language-runtime",
                "license_expression": "PSF-2.0",
                "license_files": [
                    {
                        "path": python_target.relative_to(release).as_posix(),
                        "bytes": python_target.stat().st_size,
                        "sha256": _sha256(python_target),
                    }
                ],
            }
        )

        for display_name, expected_version in requested:
            try:
                dist = metadata.distribution(display_name)
            except metadata.PackageNotFoundError as exc:
                raise PythonRuntimeLegalError(
                    f"required Python distribution is not installed: {display_name}"
                ) from exc
            actual_name = dist.metadata.get("Name") or display_name
            actual_version = dist.version
            if _canonical_name(actual_name) != _canonical_name(display_name):
                raise PythonRuntimeLegalError(
                    f"Python distribution identity mismatch: expected {display_name}, got {actual_name}"
                )
            if actual_version != expected_version:
                raise PythonRuntimeLegalError(
                    f"Python distribution version mismatch for {display_name}: "
                    f"expected {expected_version}, got {actual_version}"
                )
            sources = _distribution_license_paths(dist)
            if not sources:
                raise PythonRuntimeLegalError(
                    f"Python distribution has no packaged license/notice file: {display_name}=={expected_version}"
                )
            component_dir = licenses_root / _safe_component_dir(actual_name, actual_version)
            component_dir.mkdir()
            evidence: list[dict[str, Any]] = []
            used_names: set[str] = set()
            for index, source in enumerate(sources, 1):
                target_name = source.name
                if target_name.casefold() in used_names:
                    target_name = f"{index:02d}-{source.name}"
                used_names.add(target_name.casefold())
                target = component_dir / target_name
                shutil.copy2(source, target)
                total_bytes += target.stat().st_size
                if total_bytes > _MAX_TOTAL_LICENSE_BYTES:
                    raise PythonRuntimeLegalError("Python runtime legal bundle exceeded size limit")
                evidence.append(
                    {
                        "path": target.relative_to(release).as_posix(),
                        "bytes": target.stat().st_size,
                        "sha256": _sha256(target),
                    }
                )
            components.append(
                {
                    "id": _canonical_name(actual_name),
                    "name": actual_name,
                    "version": actual_version,
                    "role": "freezer" if _canonical_name(actual_name) == "pyinstaller" else "shipping-distribution",
                    "license_expression": _license_expression(dist),
                    "license_files": evidence,
                }
            )

        manifest = {
            "schema_version": 1,
            "platform": "windows-x86_64",
            "python_version": python_version,
            "shipping_distribution_count": len(locked),
            "embedded_build_tool_count": 1,
            "components": sorted(components, key=lambda item: item["id"]),
        }
        _atomic_json(legal_root / "components.windows-x86_64.json", manifest)
    except Exception:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise

    return {
        "ok": True,
        "component_count": len(components),
        "shipping_distribution_count": len(locked),
        "license_bytes": total_bytes,
        "manifest": "legal/python-runtime/components.windows-x86_64.json",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--pyinstaller-version", required=True)
    parser.add_argument("--python-license", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_python_runtime_legal_bundle(
            release_root=args.release_root,
            lock_file=args.lock,
            pyinstaller_version=args.pyinstaller_version,
            python_license_file=args.python_license,
        )
    except (OSError, UnicodeError, PythonRuntimeLegalError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
