#!/usr/bin/env python3
"""Validate and stage the exact Stage 9 Windows media component provenance map."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = 1
_PLATFORM = "windows-x86_64"
_COMPONENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_PE_SUFFIXES = frozenset({".dll", ".exe"})


class MediaRuntimeLegalError(RuntimeError):
    pass


def _normalised_pe_path(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        raise MediaRuntimeLegalError("component file path must be a non-empty string")
    if "\\" in raw:
        raise MediaRuntimeLegalError(f"component file path must use '/': {raw}")
    path = Path(raw)
    if path.is_absolute() or not path.parts:
        raise MediaRuntimeLegalError(f"component file path must be relative: {raw}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise MediaRuntimeLegalError(f"component file path is not normalised: {raw}")
    if path.suffix.casefold() not in _PE_SUFFIXES:
        raise MediaRuntimeLegalError(f"component file is not a PE runtime file: {raw}")
    return path.as_posix()


def _require_https(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise MediaRuntimeLegalError(f"{label} must be an HTTPS URL")
    return value


def _validate_source(component_id: str, raw: object, *, require_complete: bool) -> str:
    if not isinstance(raw, dict):
        raise MediaRuntimeLegalError(f"{component_id}: source must be an object")
    status = raw.get("status")
    if status not in {"complete", "pending"}:
        raise MediaRuntimeLegalError(
            f"{component_id}: source.status must be 'complete' or 'pending'"
        )
    if require_complete and status != "complete":
        raise MediaRuntimeLegalError(f"{component_id}: source provenance is still pending")
    if status == "pending":
        return status

    kind = raw.get("kind")
    if not isinstance(kind, str) or not kind:
        raise MediaRuntimeLegalError(f"{component_id}: complete source requires kind")
    upstream = raw.get("upstream")
    if not isinstance(upstream, dict):
        raise MediaRuntimeLegalError(
            f"{component_id}: complete source requires upstream object"
        )
    _require_https(upstream.get("url"), f"{component_id}: upstream.url")
    sha256 = upstream.get("sha256")
    commit = upstream.get("commit")
    if sha256 is None and commit is None:
        raise MediaRuntimeLegalError(
            f"{component_id}: upstream source requires sha256 or commit"
        )
    if sha256 is not None and (
        not isinstance(sha256, str) or _SHA256_RE.fullmatch(sha256) is None
    ):
        raise MediaRuntimeLegalError(f"{component_id}: upstream.sha256 is invalid")
    if commit is not None and (
        not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None
    ):
        raise MediaRuntimeLegalError(f"{component_id}: upstream.commit is invalid")

    recipe = raw.get("recipe")
    if recipe is not None:
        if not isinstance(recipe, dict):
            raise MediaRuntimeLegalError(f"{component_id}: recipe must be an object")
        _require_https(recipe.get("repository"), f"{component_id}: recipe.repository")
        recipe_commit = recipe.get("commit")
        if (
            not isinstance(recipe_commit, str)
            or _COMMIT_RE.fullmatch(recipe_commit) is None
        ):
            raise MediaRuntimeLegalError(f"{component_id}: recipe.commit is invalid")
        recipe_path = recipe.get("path")
        if not isinstance(recipe_path, str) or not recipe_path or "\\" in recipe_path:
            raise MediaRuntimeLegalError(f"{component_id}: recipe.path is invalid")
        recipe_parts = Path(recipe_path).parts
        if any(part in {"", ".", ".."} for part in recipe_parts):
            raise MediaRuntimeLegalError(f"{component_id}: recipe.path is invalid")
    return status


def load_and_validate_manifest(
    manifest_file: Path | str,
    *,
    expected_pe_files: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(manifest_file)
    if path.is_symlink() or not path.is_file():
        raise MediaRuntimeLegalError("media component manifest must be a regular file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MediaRuntimeLegalError("media component manifest is not valid UTF-8 JSON") from exc
    if not isinstance(raw, dict):
        raise MediaRuntimeLegalError("media component manifest root must be an object")
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise MediaRuntimeLegalError(
            f"unsupported media component manifest schema: {raw.get('schema_version')!r}"
        )
    if raw.get("platform") != _PLATFORM:
        raise MediaRuntimeLegalError(
            f"unexpected media component manifest platform: {raw.get('platform')!r}"
        )
    expected_count = raw.get("expected_pe_file_count")
    if not isinstance(expected_count, int) or expected_count <= 0:
        raise MediaRuntimeLegalError("expected_pe_file_count must be a positive integer")

    release_gate = raw.get("release_gate")
    if not isinstance(release_gate, dict):
        raise MediaRuntimeLegalError("release_gate must be an object")
    require_complete = release_gate.get("require_all_sources_complete")
    if not isinstance(require_complete, bool):
        raise MediaRuntimeLegalError(
            "release_gate.require_all_sources_complete must be boolean"
        )

    components = raw.get("components")
    if not isinstance(components, list) or not components:
        raise MediaRuntimeLegalError("components must be a non-empty list")

    ids: set[str] = set()
    mapped: dict[str, str] = {}
    pending: list[str] = []
    for component in components:
        if not isinstance(component, dict):
            raise MediaRuntimeLegalError("every component must be an object")
        component_id = component.get("id")
        if (
            not isinstance(component_id, str)
            or _COMPONENT_ID_RE.fullmatch(component_id) is None
        ):
            raise MediaRuntimeLegalError(f"invalid component id: {component_id!r}")
        if component_id in ids:
            raise MediaRuntimeLegalError(f"duplicate component id: {component_id}")
        ids.add(component_id)
        for key in ("name", "version", "license_expression", "version_evidence"):
            value = component.get(key)
            if not isinstance(value, str) or not value.strip():
                raise MediaRuntimeLegalError(
                    f"{component_id}: {key} must be a non-empty string"
                )
        status = _validate_source(
            component_id, component.get("source"), require_complete=require_complete
        )
        if status == "pending":
            pending.append(component_id)

        files = component.get("files")
        if not isinstance(files, list) or not files:
            raise MediaRuntimeLegalError(
                f"{component_id}: files must be a non-empty list"
            )
        for item in files:
            relative = _normalised_pe_path(item)
            folded = relative.casefold()
            previous = mapped.get(folded)
            if previous is not None:
                raise MediaRuntimeLegalError(
                    f"PE file is mapped more than once: {relative} "
                    f"({previous}, {component_id})"
                )
            mapped[folded] = component_id

    if len(mapped) != expected_count:
        raise MediaRuntimeLegalError(
            f"manifest maps {len(mapped)} PE files, expected {expected_count}"
        )

    if expected_pe_files is not None:
        expected = {_normalised_pe_path(item).casefold() for item in expected_pe_files}
        actual = set(mapped)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing or extra:
            pieces: list[str] = []
            if missing:
                pieces.append("unmapped=" + ",".join(missing))
            if extra:
                pieces.append("not-retained=" + ",".join(extra))
            raise MediaRuntimeLegalError(
                "media component manifest does not match retained PE closure: "
                + "; ".join(pieces)
            )

    summary = {
        "component_count": len(components),
        "pe_file_count": len(mapped),
        "pending_source_components": sorted(pending),
        "all_sources_complete": not pending,
    }
    return raw, summary


def enumerate_media_pe_files(media_root: Path | str) -> list[str]:
    root = Path(media_root)
    if root.is_symlink() or not root.is_dir():
        raise MediaRuntimeLegalError("staged media root must be a real directory")
    files: list[str] = []
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise MediaRuntimeLegalError(
                "staged media root contains a symlink: "
                + candidate.relative_to(root).as_posix()
            )
        if candidate.is_file() and candidate.suffix.casefold() in _PE_SUFFIXES:
            files.append(candidate.relative_to(root).as_posix())
    return sorted(files, key=str.casefold)


def verify_staged_media_runtime(
    media_root: Path | str,
    manifest_file: Path | str,
) -> dict[str, Any]:
    actual = enumerate_media_pe_files(media_root)
    _, summary = load_and_validate_manifest(manifest_file, expected_pe_files=actual)
    return summary


def stage_media_runtime_legal_bundle(
    *,
    release_root: Path | str,
    media_root: Path | str,
    manifest_file: Path | str,
    notice_file: Path | str,
) -> dict[str, Any]:
    release = Path(release_root)
    media = Path(media_root)
    manifest = Path(manifest_file)
    notice = Path(notice_file)
    if release.is_symlink() or not release.is_dir():
        raise MediaRuntimeLegalError("release root must be a real directory")
    if notice.is_symlink() or not notice.is_file() or notice.stat().st_size <= 0:
        raise MediaRuntimeLegalError("media runtime notice must be a non-empty regular file")

    summary = verify_staged_media_runtime(media, manifest)
    legal_root = release / "legal" / "media-runtime"
    legal_root.mkdir(parents=True, exist_ok=True)
    targets = {
        "manifest": legal_root / "components.windows-x86_64.json",
        "notice": legal_root / "NOTICE.md",
    }
    shutil.copy2(manifest, targets["manifest"])
    shutil.copy2(notice, targets["notice"])
    for target in targets.values():
        if target.is_symlink() or not target.is_file() or target.stat().st_size <= 0:
            raise MediaRuntimeLegalError(
                f"staged media legal file is missing or empty: {target.name}"
            )
    return {
        **summary,
        "legal_files": [
            "legal/media-runtime/components.windows-x86_64.json",
            "legal/media-runtime/NOTICE.md",
        ],
    }
