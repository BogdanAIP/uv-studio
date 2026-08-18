#!/usr/bin/env python3
"""Validate and stage exact license/notice files for the Windows media runtime."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Sequence
from urllib.request import Request, urlopen

if __package__:
    from tools.media_runtime_legal import load_and_validate_manifest
else:
    from media_runtime_legal import load_and_validate_manifest

_SCHEMA_VERSION = 1
_PLATFORM = "windows-x86_64"
_SHA256_HEX = frozenset("0123456789abcdef")


class MediaRuntimeLicenseError(RuntimeError):
    pass


def _load_json(path: Path | str, label: str) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise MediaRuntimeLicenseError(f"{label} must be a regular file")
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MediaRuntimeLicenseError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise MediaRuntimeLicenseError(f"{label} root must be an object")
    return value


def _safe_relative(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise MediaRuntimeLicenseError(f"{label} must be a non-empty '/' path")
    path = Path(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise MediaRuntimeLicenseError(f"{label} is not a normalized relative path: {raw}")
    return path


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_sha256(raw: object, label: str, *, required: bool) -> str | None:
    if raw is None:
        if required:
            raise MediaRuntimeLicenseError(f"{label} is not pinned")
        return None
    if (
        not isinstance(raw, str)
        or len(raw) != 64
        or any(ch not in _SHA256_HEX for ch in raw)
    ):
        raise MediaRuntimeLicenseError(f"{label} must be lowercase SHA-256")
    return raw


def _component_ids(component_manifest_file: Path | str) -> set[str]:
    raw, _ = load_and_validate_manifest(component_manifest_file)
    return {component["id"] for component in raw["components"]}


def load_and_validate_license_manifest(
    license_manifest_file: Path | str,
    *,
    component_manifest_file: Path | str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _load_json(license_manifest_file, "media license-file manifest")
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise MediaRuntimeLicenseError(
            f"unsupported media license-file schema: {raw.get('schema_version')!r}"
        )
    if raw.get("platform") != _PLATFORM:
        raise MediaRuntimeLicenseError(
            f"unexpected media license-file platform: {raw.get('platform')!r}"
        )
    gate = raw.get("release_gate")
    if not isinstance(gate, dict):
        raise MediaRuntimeLicenseError("release_gate must be an object")
    require_hashes = gate.get("require_hashes")
    max_asset_bytes = gate.get("max_asset_bytes")
    max_total_bytes = gate.get("max_total_bytes")
    if not isinstance(require_hashes, bool):
        raise MediaRuntimeLicenseError("release_gate.require_hashes must be boolean")
    if not isinstance(max_asset_bytes, int) or not 1 <= max_asset_bytes <= 2 * 1024 * 1024:
        raise MediaRuntimeLicenseError("release_gate.max_asset_bytes is invalid")
    if not isinstance(max_total_bytes, int) or not max_asset_bytes <= max_total_bytes <= 16 * 1024 * 1024:
        raise MediaRuntimeLicenseError("release_gate.max_total_bytes is invalid")

    known_components = _component_ids(component_manifest_file)
    assets = raw.get("assets")
    if not isinstance(assets, list) or not assets:
        raise MediaRuntimeLicenseError("assets must be a non-empty list")

    ids: set[str] = set()
    targets: set[str] = set()
    covered: set[str] = set()
    unpinned: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise MediaRuntimeLicenseError("every license asset must be an object")
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in ids:
            raise MediaRuntimeLicenseError(f"invalid or duplicate license asset id: {asset_id!r}")
        ids.add(asset_id)
        target = _safe_relative(asset.get("target"), f"{asset_id}: target").as_posix()
        folded_target = target.casefold()
        if folded_target in targets:
            raise MediaRuntimeLicenseError(f"duplicate license asset target: {target}")
        targets.add(folded_target)

        components = asset.get("components")
        if not isinstance(components, list) or not components:
            raise MediaRuntimeLicenseError(f"{asset_id}: components must be a non-empty list")
        local_components: set[str] = set()
        for component in components:
            if not isinstance(component, str) or component not in known_components:
                raise MediaRuntimeLicenseError(f"{asset_id}: unknown component {component!r}")
            if component in local_components:
                raise MediaRuntimeLicenseError(f"{asset_id}: duplicate component {component}")
            local_components.add(component)
            covered.add(component)

        source = asset.get("source")
        if not isinstance(source, dict):
            raise MediaRuntimeLicenseError(f"{asset_id}: source must be an object")
        kind = source.get("kind")
        if kind == "carrier":
            _safe_relative(source.get("path"), f"{asset_id}: carrier path")
            if source.get("encoding") is not None:
                raise MediaRuntimeLicenseError(f"{asset_id}: carrier source cannot set encoding")
        elif kind == "url":
            url = source.get("url")
            if not isinstance(url, str) or not url.startswith("https://"):
                raise MediaRuntimeLicenseError(f"{asset_id}: source URL must be HTTPS")
            encoding = source.get("encoding")
            if encoding not in {None, "base64"}:
                raise MediaRuntimeLicenseError(f"{asset_id}: unsupported source encoding")
        else:
            raise MediaRuntimeLicenseError(f"{asset_id}: source.kind must be carrier or url")

        if _validate_sha256(
            asset.get("sha256"), f"{asset_id}: sha256", required=require_hashes
        ) is None:
            unpinned.append(asset_id)

    missing = sorted(known_components - covered)
    if missing:
        raise MediaRuntimeLicenseError(
            "license assets do not cover every retained component: " + ", ".join(missing)
        )
    return raw, {
        "asset_count": len(assets),
        "component_count": len(known_components),
        "unpinned_assets": sorted(unpinned),
        "all_hashes_pinned": not unpinned,
        "max_asset_bytes": max_asset_bytes,
        "max_total_bytes": max_total_bytes,
    }


def _read_url(url: str, *, max_bytes: int) -> bytes:
    request = Request(url, headers={"User-Agent": "UV-Studio-Stage9-License-Audit/1"})
    fetch_limit = max_bytes * 2 + 4096
    try:
        with urlopen(request, timeout=30) as response:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(65536, fetch_limit - total + 1))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > fetch_limit:
                    raise MediaRuntimeLicenseError("remote license asset exceeded bounded fetch size")
    except MediaRuntimeLicenseError:
        raise
    except Exception as exc:
        raise MediaRuntimeLicenseError(f"could not fetch license asset: {url}") from exc
    return b"".join(chunks)


def _asset_bytes(asset: dict[str, Any], *, media_root: Path, max_bytes: int) -> bytes:
    source = asset["source"]
    if source["kind"] == "carrier":
        relative = _safe_relative(source["path"], f"{asset['id']}: carrier path")
        candidate = media_root.joinpath(*relative.parts)
        if candidate.is_symlink() or not candidate.is_file():
            raise MediaRuntimeLicenseError(
                f"{asset['id']}: carrier license file is missing: {relative.as_posix()}"
            )
        if candidate.stat().st_size > max_bytes:
            raise MediaRuntimeLicenseError(f"{asset['id']}: carrier license asset is too large")
        data = candidate.read_bytes()
    else:
        data = _read_url(source["url"], max_bytes=max_bytes)
        if source.get("encoding") == "base64":
            try:
                data = base64.b64decode(b"".join(data.split()), validate=True)
            except ValueError as exc:
                raise MediaRuntimeLicenseError(
                    f"{asset['id']}: remote asset is not valid base64"
                ) from exc
    if not data:
        raise MediaRuntimeLicenseError(f"{asset['id']}: license asset is empty")
    if len(data) > max_bytes:
        raise MediaRuntimeLicenseError(f"{asset['id']}: decoded license asset is too large")
    return data


def stage_media_runtime_license_bundle(
    *,
    release_root: Path | str,
    media_root: Path | str,
    component_manifest_file: Path | str,
    license_manifest_file: Path | str,
) -> dict[str, Any]:
    release = Path(release_root)
    media = Path(media_root)
    if release.is_symlink() or not release.is_dir():
        raise MediaRuntimeLicenseError("release root must be a real directory")
    if media.is_symlink() or not media.is_dir():
        raise MediaRuntimeLicenseError("media root must be a real directory")

    manifest, summary = load_and_validate_license_manifest(
        license_manifest_file, component_manifest_file=component_manifest_file
    )
    legal_root = release / "legal" / "media-runtime"
    output = legal_root / "licenses"
    if output.exists() or output.is_symlink():
        raise MediaRuntimeLicenseError("media runtime license output must not already exist")

    max_asset = summary["max_asset_bytes"]
    max_total = summary["max_total_bytes"]
    report_assets: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        output.mkdir(parents=True)
        for asset in sorted(manifest["assets"], key=lambda item: item["id"]):
            data = _asset_bytes(asset, media_root=media, max_bytes=max_asset)
            total_bytes += len(data)
            if total_bytes > max_total:
                raise MediaRuntimeLicenseError("media runtime license bundle exceeded total size limit")
            actual_hash = _sha256(data)
            expected_hash = asset.get("sha256")
            if expected_hash is not None and actual_hash != expected_hash:
                raise MediaRuntimeLicenseError(
                    f"{asset['id']}: SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
                )
            target_relative = _safe_relative(asset["target"], f"{asset['id']}: target")
            target = output.joinpath(*target_relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if target.is_symlink() or not target.is_file() or target.stat().st_size != len(data):
                raise MediaRuntimeLicenseError(f"{asset['id']}: staged license asset is invalid")
            report_assets.append(
                {
                    "id": asset["id"],
                    "target": f"legal/media-runtime/licenses/{target_relative.as_posix()}",
                    "bytes": len(data),
                    "sha256": actual_hash,
                    "hash_pinned": expected_hash is not None,
                }
            )

        manifest_target = legal_root / "license-files.windows-x86_64.json"
        shutil.copy2(license_manifest_file, manifest_target)
        if manifest_target.is_symlink() or not manifest_target.is_file():
            raise MediaRuntimeLicenseError("staged media license-file manifest is invalid")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        manifest_target = legal_root / "license-files.windows-x86_64.json"
        if manifest_target.exists():
            manifest_target.unlink()
        raise

    return {
        "ok": True,
        "asset_count": len(report_assets),
        "component_count": summary["component_count"],
        "total_bytes": total_bytes,
        "all_hashes_pinned": summary["all_hashes_pinned"],
        "unpinned_assets": summary["unpinned_assets"],
        "assets": report_assets,
        "legal_files": [
            "legal/media-runtime/license-files.windows-x86_64.json",
            *[item["target"] for item in report_assets],
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--component-manifest", type=Path, required=True)
    parser.add_argument("--license-manifest", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_media_runtime_license_bundle(
            release_root=args.release_root,
            media_root=args.media_root,
            component_manifest_file=args.component_manifest,
            license_manifest_file=args.license_manifest,
        )
    except (OSError, MediaRuntimeLicenseError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
