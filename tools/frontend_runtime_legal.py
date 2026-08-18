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
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

_LICENSE_NAME_RE = re.compile(r"^(license|licence|copying|notice)(?:[._-].*)?$", re.IGNORECASE)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_MAX_LICENSE_FILE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_LICENSE_BYTES = 16 * 1024 * 1024
_NEXT_MONOREPO_FALLBACKS = frozenset({"@next/env", "client-only"})

# These are source-repository object identities, not guesses from the npm tarball.
# Next's published npm package intentionally omits devDependencies, so the exact
# v16.3.0 source blobs are the stable evidence for both the busboy version pin and
# the ncc vendoring recipe used to create next/dist/compiled/busboy.
_KNOWN_NEXT_COMPILED_RECIPES: dict[tuple[str, str, str], dict[str, str]] = {
    ("v16.3.0", "busboy", "1.6.0"): {
        "repository": "https://github.com/vercel/next.js",
        "taskfile_path": "packages/next/taskfile.js",
        "taskfile_git_blob_sha1": "5087c404ab47ee00d6b6da6ac96928e1927f5d00",
        "package_path": "packages/next/package.json",
        "package_git_blob_sha1": "034dfa8bad6783f96066927c60fb32397392625e",
    }
}


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


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise FrontendRuntimeLegalError(f"{label} must be a canonical relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise FrontendRuntimeLegalError(f"{label} must be a canonical relative path")
    if path.as_posix() != value:
        raise FrontendRuntimeLegalError(f"{label} must be canonical")
    return value


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise FrontendRuntimeLegalError(f"{label} must be a non-empty canonical string")
    if "\r" in value or "\n" in value:
        raise FrontendRuntimeLegalError(f"{label} must not contain line breaks")
    return value


def _required_sha256(value: Any, label: str) -> str:
    raw = _required_string(value, label)
    if _SHA256_RE.fullmatch(raw) is None:
        raise FrontendRuntimeLegalError(f"{label} must be 64 lowercase hexadecimal characters")
    return raw


def _required_git_sha1(value: Any, label: str) -> str:
    raw = _required_string(value, label)
    if _GIT_SHA1_RE.fullmatch(raw) is None:
        raise FrontendRuntimeLegalError(f"{label} must be 40 lowercase hexadecimal characters")
    return raw


def _exact_object(value: Any, label: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise FrontendRuntimeLegalError(f"{label} has unexpected fields")
    return value


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


def _next_monorepo_license_fallback(
    *,
    package_name: str,
    package_version: str,
    package_metadata: dict[str, Any],
    source_modules: Path,
) -> tuple[list[Path], dict[str, Any]] | None:
    if package_name not in _NEXT_MONOREPO_FALLBACKS:
        return None

    next_root = source_modules / "next"
    next_package = _read_package_json(next_root / "package.json", "next fallback provider")
    next_name = next_package.get("name")
    next_version = next_package.get("version")
    if next_name != "next" or not isinstance(next_version, str) or not next_version:
        raise FrontendRuntimeLegalError("Next monorepo fallback provider identity is invalid")

    if package_name == "@next/env":
        repository = package_metadata.get("repository")
        if not isinstance(repository, dict):
            raise FrontendRuntimeLegalError("@next/env fallback requires repository metadata")
        repository_url = repository.get("url")
        directory = repository.get("directory")
        if repository_url != "https://github.com/vercel/next.js" or directory != "packages/next-env":
            raise FrontendRuntimeLegalError("@next/env fallback repository metadata is not the pinned Next monorepo")
        if package_version != next_version:
            raise FrontendRuntimeLegalError(
                f"@next/env fallback requires matching next version: {package_version} != {next_version}"
            )
    else:
        compiled_metadata = _read_package_json(
            next_root / "dist" / "compiled" / "client-only" / "package.json",
            "next compiled client-only fallback proof",
        )
        for key in ("name", "version", "license"):
            if compiled_metadata.get(key) != package_metadata.get(key):
                raise FrontendRuntimeLegalError(
                    f"client-only fallback metadata mismatch for {key}"
                )

    licenses = _license_files(next_root)
    if not licenses:
        raise FrontendRuntimeLegalError("Next monorepo fallback provider has no LICENSE/NOTICE file")
    return licenses, {
        "kind": "next-monorepo-root-license",
        "provider_name": "next",
        "provider_version": next_version,
        "provider_runtime_path": "frontend/node_modules/next",
    }


def _validate_next_recipe(recipe: dict[str, Any], *, label: str) -> None:
    recipe["repository"] = _required_string(recipe["repository"], f"{label}.repository")
    recipe["ref"] = _required_string(recipe["ref"], f"{label}.ref")
    recipe["taskfile_path"] = _canonical_relative_path(
        recipe["taskfile_path"], f"{label}.taskfile_path"
    )
    recipe["taskfile_git_blob_sha1"] = _required_git_sha1(
        recipe["taskfile_git_blob_sha1"], f"{label}.taskfile_git_blob_sha1"
    )
    recipe["package_path"] = _canonical_relative_path(
        recipe["package_path"], f"{label}.package_path"
    )
    recipe["package_git_blob_sha1"] = _required_git_sha1(
        recipe["package_git_blob_sha1"], f"{label}.package_git_blob_sha1"
    )
    recipe["dependency_name"] = _required_string(
        recipe["dependency_name"], f"{label}.dependency_name"
    )
    recipe["dependency_version"] = _required_string(
        recipe["dependency_version"], f"{label}.dependency_version"
    )
    key = (recipe["ref"], recipe["dependency_name"], recipe["dependency_version"])
    known = _KNOWN_NEXT_COMPILED_RECIPES.get(key)
    if known is None:
        raise FrontendRuntimeLegalError(
            f"{label} is not an audited Next compiled recipe: {key[0]} {key[1]}@{key[2]}"
        )
    actual = {
        "repository": recipe["repository"],
        "taskfile_path": recipe["taskfile_path"],
        "taskfile_git_blob_sha1": recipe["taskfile_git_blob_sha1"],
        "package_path": recipe["package_path"],
        "package_git_blob_sha1": recipe["package_git_blob_sha1"],
    }
    if actual != known:
        raise FrontendRuntimeLegalError(f"{label} source Git object identities drifted")


def _load_compiled_overrides(
    path: Path | str | None,
    *,
    repository_root: Path,
) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise FrontendRuntimeLegalError("frontend compiled override manifest must be a regular file")
    try:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FrontendRuntimeLegalError("frontend compiled override manifest is invalid JSON") from exc
    root = _exact_object(raw, "frontend compiled override manifest", {"schema_version", "platform", "overrides"})
    if root["schema_version"] != 1 or isinstance(root["schema_version"], bool):
        raise FrontendRuntimeLegalError("frontend compiled override schema_version must be integer 1")
    if root["platform"] != "windows-x86_64":
        raise FrontendRuntimeLegalError("frontend compiled override platform must be windows-x86_64")
    if not isinstance(root["overrides"], list):
        raise FrontendRuntimeLegalError("frontend compiled override list must be an array")

    overrides: dict[str, dict[str, Any]] = {}
    fields = {
        "runtime_package_json",
        "runtime_package_json_sha256",
        "name",
        "version",
        "license_expression",
        "license_file",
        "license_file_sha256",
        "next_recipe",
        "upstream_license",
    }
    recipe_fields = {
        "repository",
        "ref",
        "taskfile_path",
        "taskfile_git_blob_sha1",
        "package_path",
        "package_git_blob_sha1",
        "dependency_name",
        "dependency_version",
    }
    for index, raw_item in enumerate(root["overrides"]):
        item = _exact_object(raw_item, f"frontend compiled override[{index}]", fields)
        runtime_path = _canonical_relative_path(
            item["runtime_package_json"], f"frontend compiled override[{index}].runtime_package_json"
        )
        prefix = "node_modules/next/dist/compiled/"
        if not runtime_path.startswith(prefix) or not runtime_path.endswith("/package.json"):
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] must target next/dist/compiled package.json"
            )
        if runtime_path in overrides:
            raise FrontendRuntimeLegalError(f"duplicate frontend compiled override: {runtime_path}")
        item["runtime_package_json_sha256"] = _required_sha256(
            item["runtime_package_json_sha256"],
            f"frontend compiled override[{index}].runtime_package_json_sha256",
        )
        item["name"] = _required_string(item["name"], f"frontend compiled override[{index}].name")
        item["version"] = _required_string(item["version"], f"frontend compiled override[{index}].version")
        item["license_expression"] = _required_string(
            item["license_expression"], f"frontend compiled override[{index}].license_expression"
        )
        license_relative = _canonical_relative_path(
            item["license_file"], f"frontend compiled override[{index}].license_file"
        )
        item["license_file_sha256"] = _required_sha256(
            item["license_file_sha256"], f"frontend compiled override[{index}].license_file_sha256"
        )
        license_path = repository_root.joinpath(*PurePosixPath(license_relative).parts)
        try:
            license_resolved = license_path.resolve(strict=True)
            repository_resolved = repository_root.resolve(strict=True)
        except OSError as exc:
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] license file is missing"
            ) from exc
        if license_path.is_symlink() or not license_resolved.is_file():
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] license file must be regular"
            )
        try:
            license_resolved.relative_to(repository_resolved)
        except ValueError as exc:
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] license file escapes repository root"
            ) from exc
        if license_resolved.stat().st_size <= 0 or license_resolved.stat().st_size > _MAX_LICENSE_FILE_BYTES:
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] license file has invalid size"
            )
        if _sha256(license_resolved) != item["license_file_sha256"]:
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] license SHA-256 mismatch"
            )

        recipe = _exact_object(
            item["next_recipe"],
            f"frontend compiled override[{index}].next_recipe",
            recipe_fields,
        )
        _validate_next_recipe(
            recipe,
            label=f"frontend compiled override[{index}].next_recipe",
        )
        if recipe["dependency_name"] != item["name"] or recipe["dependency_version"] != item["version"]:
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] recipe dependency identity does not match override"
            )

        upstream = _exact_object(
            item["upstream_license"],
            f"frontend compiled override[{index}].upstream_license",
            {"repository", "ref", "path", "git_blob_sha1", "local_copy_normalized"},
        )
        upstream["repository"] = _required_string(
            upstream["repository"], f"frontend compiled override[{index}].upstream_license.repository"
        )
        upstream["ref"] = _required_string(
            upstream["ref"], f"frontend compiled override[{index}].upstream_license.ref"
        )
        upstream["path"] = _canonical_relative_path(
            upstream["path"], f"frontend compiled override[{index}].upstream_license.path"
        )
        upstream["git_blob_sha1"] = _required_git_sha1(
            upstream["git_blob_sha1"], f"frontend compiled override[{index}].upstream_license.git_blob_sha1"
        )
        if upstream["local_copy_normalized"] is not True:
            raise FrontendRuntimeLegalError(
                f"frontend compiled override[{index}] must declare normalized local license copy"
            )
        overrides[runtime_path] = item
    return overrides


def _apply_compiled_override(
    *,
    override: dict[str, Any],
    runtime_package_json: Path,
    package_metadata: dict[str, Any],
    runtime_relative: str,
    source_modules: Path,
    repository_root: Path,
    licenses_root: Path,
    release_root: Path,
) -> tuple[str, str, dict[str, Any], int]:
    if _sha256(runtime_package_json) != override["runtime_package_json_sha256"]:
        raise FrontendRuntimeLegalError(
            f"compiled override runtime package SHA-256 mismatch: {runtime_relative}"
        )
    if package_metadata.get("name") != override["name"]:
        raise FrontendRuntimeLegalError(
            f"compiled override package name mismatch: {runtime_relative}"
        )
    runtime_version = package_metadata.get("version")
    if isinstance(runtime_version, str) and runtime_version and runtime_version != override["version"]:
        raise FrontendRuntimeLegalError(
            f"compiled override package version mismatch: {runtime_relative}"
        )
    runtime_license = package_metadata.get("license")
    if isinstance(runtime_license, str) and runtime_license.strip() and runtime_license.strip() != override["license_expression"]:
        raise FrontendRuntimeLegalError(
            f"compiled override license expression mismatch: {runtime_relative}"
        )

    next_package = _read_package_json(source_modules / "next" / "package.json", "Next compiled override provider")
    next_version = next_package.get("version")
    if next_package.get("name") != "next" or not isinstance(next_version, str) or not next_version:
        raise FrontendRuntimeLegalError("Next compiled override provider identity is invalid")
    recipe = override["next_recipe"]
    if recipe["ref"] != f"v{next_version}":
        raise FrontendRuntimeLegalError(
            f"compiled override Next recipe ref does not match installed next version: {recipe['ref']} != v{next_version}"
        )
    # The published Next npm tarball omits source-only devDependencies. Their exact
    # version and the ncc recipe are therefore anchored by the audited source Git
    # object identities validated in _validate_next_recipe(), not inferred here.
    if recipe["dependency_name"] != override["name"] or recipe["dependency_version"] != override["version"]:
        raise FrontendRuntimeLegalError("compiled override recipe dependency identity drifted")

    license_path = repository_root.joinpath(*PurePosixPath(override["license_file"]).parts).resolve(strict=True)
    component_dir = licenses_root / "compiled" / _safe_slug(override["name"], override["version"])
    component_dir.mkdir(parents=True, exist_ok=False)
    target = component_dir / license_path.name
    shutil.copy2(license_path, target)
    size = target.stat().st_size
    evidence = {
        "kind": "checked-in-compiled-override",
        "next_recipe": override["next_recipe"],
        "upstream_license": override["upstream_license"],
        "license_file": {
            "path": target.relative_to(release_root).as_posix(),
            "bytes": size,
            "sha256": _sha256(target),
        },
    }
    return override["version"], override["license_expression"], evidence, size


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
    compiled_overrides_file: Path | str | None = None,
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

    repository_root = source.resolve().parent
    staged_modules = staged / "node_modules"
    source_modules = source / "node_modules"
    package_roots = _direct_package_roots(staged_modules)
    if not package_roots:
        raise FrontendRuntimeLegalError("Next standalone runtime contains no direct packages")
    overrides = _load_compiled_overrides(
        compiled_overrides_file,
        repository_root=repository_root,
    )

    legal_root = release / "legal" / "frontend-runtime"
    if legal_root.exists() or legal_root.is_symlink():
        raise FrontendRuntimeLegalError("frontend runtime legal output already exists")

    direct: list[dict[str, Any]] = []
    compiled: list[dict[str, Any]] = []
    fallback_packages: list[str] = []
    applied_override_paths: list[str] = []
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
            license_source: dict[str, Any] = {"kind": "package-root"}
            if not sources:
                fallback = _next_monorepo_license_fallback(
                    package_name=name,
                    package_version=version,
                    package_metadata=source_package,
                    source_modules=source_modules,
                )
                if fallback is None:
                    raise FrontendRuntimeLegalError(
                        f"standalone package has no source license/notice file: {name}@{version}"
                    )
                sources, license_source = fallback
                fallback_packages.append(name)

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
                    "license_source": license_source,
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
                runtime_override_path = package_json.relative_to(staged).as_posix()
                name = package.get("name")
                version = package.get("version")
                license_expression = package.get("license")
                if not isinstance(name, str) or not name:
                    raise FrontendRuntimeLegalError(f"{relative}: compiled package name is missing")

                override_source: dict[str, Any] | None = None
                override = overrides.get(runtime_override_path)
                if override is not None:
                    version, license_expression, override_source, added_bytes = _apply_compiled_override(
                        override=override,
                        runtime_package_json=package_json,
                        package_metadata=package,
                        runtime_relative=runtime_override_path,
                        source_modules=source_modules,
                        repository_root=repository_root,
                        licenses_root=licenses_root,
                        release_root=release,
                    )
                    total_bytes += added_bytes
                    if total_bytes > _MAX_TOTAL_LICENSE_BYTES:
                        raise FrontendRuntimeLegalError("frontend runtime legal bundle exceeded size limit")
                    applied_override_paths.append(runtime_override_path)

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
                        "license_source": override_source,
                    }
                )

        unused_overrides = sorted(set(overrides) - set(applied_override_paths), key=str.casefold)
        if unused_overrides:
            raise FrontendRuntimeLegalError(
                "frontend compiled overrides were not matched by the exact runtime: "
                + ", ".join(unused_overrides)
            )
        if require_compiled_license_expressions and missing_expressions:
            raise FrontendRuntimeLegalError(
                "Next compiled packages missing license expression: " + ", ".join(missing_expressions)
            )

        manifest = {
            "schema_version": 2,
            "platform": "windows-x86_64",
            "direct_package_count": len(direct),
            "direct_license_fallback_count": len(fallback_packages),
            "direct_license_fallback_packages": sorted(fallback_packages, key=str.casefold),
            "next_compiled_package_count": len(compiled),
            "next_compiled_override_count": len(applied_override_paths),
            "next_compiled_override_paths": sorted(applied_override_paths, key=str.casefold),
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
        "direct_license_fallback_count": len(fallback_packages),
        "next_compiled_package_count": len(compiled),
        "next_compiled_override_count": len(applied_override_paths),
        "next_compiled_missing_license_expression_count": len(missing_expressions),
        "license_bytes": total_bytes,
        "manifest": "legal/frontend-runtime/components.windows-x86_64.json",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--staged-frontend-root", type=Path, required=True)
    parser.add_argument("--source-frontend-root", type=Path, required=True)
    parser.add_argument("--compiled-overrides", type=Path)
    parser.add_argument("--require-compiled-license-expressions", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_frontend_runtime_legal_bundle(
            release_root=args.release_root,
            staged_frontend_root=args.staged_frontend_root,
            source_frontend_root=args.source_frontend_root,
            compiled_overrides_file=args.compiled_overrides,
            require_compiled_license_expressions=args.require_compiled_license_expressions,
        )
    except (OSError, UnicodeError, FrontendRuntimeLegalError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
