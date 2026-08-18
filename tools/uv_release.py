#!/usr/bin/env python3
"""Release-manifest and diagnostics utility for Stage 9 packaging/support flows."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uv_studio.diagnostics import build_diagnostics  # noqa: E402
from uv_studio.release_manifest import (  # noqa: E402
    REQUIRED_RELEASE_COMPONENT_IDS,
    ReleaseComponent,
    ReleaseManifestError,
    build_release_manifest,
    load_release_manifest,
    verify_release_tree,
    write_release_manifest,
)

_DEFAULT_FRONTEND_SOURCE_ROOT = ROOT / "frontend"
_DEFAULT_FRONTEND_COMPILED_OVERRIDES = (
    ROOT / "packaging" / "frontend-compiled-licenses.windows-x86_64.json"
)
_EXPECTED_FRONTEND_NODE_LOCK = "frontend/package-lock.json"
_EXPECTED_FRONTEND_DIRECT_PACKAGES = 12
_EXPECTED_FRONTEND_DIRECT_FALLBACKS = 2
_EXPECTED_NEXT_COMPILED_PACKAGES = 53
_EXPECTED_NEXT_COMPILED_OVERRIDES = 1
_EXPECTED_NSIS_VERSION = "3.12"


def _component(value: str) -> ReleaseComponent:
    parts = value.split("=", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            "component must use COMPONENT_ID=VERSION=RELATIVE_ENTRYPOINT"
        )
    component_id, version, entrypoint = parts
    try:
        return ReleaseComponent.from_dict(
            {
                "component_id": component_id,
                "version": version,
                "entrypoint": entrypoint,
            },
            location="--component",
        )
    except ReleaseManifestError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def _stage_frontend_legal_before_manifest(root: Path) -> dict[str, object] | None:
    """Stage exact Next standalone legal evidence before D-044 hashes the tree.

    The normal release workflow exports UV_NODE_LOCK from the already validated
    runtime profile. Ad-hoc manifest tooling keeps the historical contract when
    that marker is absent.
    """
    node_lock = os.environ.get("UV_NODE_LOCK")
    if not node_lock:
        return None
    if node_lock != _EXPECTED_FRONTEND_NODE_LOCK:
        raise ReleaseManifestError(
            "frontend legal gate requires validated node lock "
            f"{_EXPECTED_FRONTEND_NODE_LOCK}, got {node_lock}"
        )

    legal_root = root / "legal" / "frontend-runtime"
    try:
        from tools.frontend_runtime_legal import (
            FrontendRuntimeLegalError,
            stage_frontend_runtime_legal_bundle,
        )

        result = stage_frontend_runtime_legal_bundle(
            release_root=root,
            staged_frontend_root=root / "frontend",
            source_frontend_root=_DEFAULT_FRONTEND_SOURCE_ROOT,
            compiled_overrides_file=_DEFAULT_FRONTEND_COMPILED_OVERRIDES,
            require_compiled_license_expressions=True,
        )
    except (OSError, UnicodeError, FrontendRuntimeLegalError) as exc:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise ReleaseManifestError(
            f"frontend runtime legal/provenance gate failed: {exc}"
        ) from exc

    expected = {
        "direct_package_count": _EXPECTED_FRONTEND_DIRECT_PACKAGES,
        "direct_license_fallback_count": _EXPECTED_FRONTEND_DIRECT_FALLBACKS,
        "next_compiled_package_count": _EXPECTED_NEXT_COMPILED_PACKAGES,
        "next_compiled_override_count": _EXPECTED_NEXT_COMPILED_OVERRIDES,
        "next_compiled_missing_license_expression_count": 0,
    }
    mismatches = [
        f"{key}: expected {value}, got {result.get(key)!r}"
        for key, value in expected.items()
        if result.get(key) != value
    ]
    if mismatches:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise ReleaseManifestError(
            "frontend runtime legal/provenance counts drifted: " + "; ".join(mismatches)
        )
    return result


def _stage_nsis_legal_before_manifest(root: Path) -> dict[str, object] | None:
    """Stage exact NSIS source/COPYING evidence before D-044 hashes the tree."""
    version = os.environ.get("UV_NSIS_VERSION")
    source_url = os.environ.get("UV_NSIS_SOURCE_URL")
    source_sha = os.environ.get("UV_NSIS_SOURCE_SHA256")
    markers = (version, source_url, source_sha)
    if not any(markers):
        return None
    if not all(markers):
        raise ReleaseManifestError("NSIS legal gate requires version, source URL and source SHA-256 together")
    assert version is not None and source_url is not None and source_sha is not None
    if version != _EXPECTED_NSIS_VERSION:
        raise ReleaseManifestError(
            f"NSIS legal gate requires version {_EXPECTED_NSIS_VERSION}, got {version}"
        )

    legal_root = root / "legal" / "nsis"
    try:
        from tools.nsis_runtime_legal import NSISLegalError, stage_nsis_legal

        result = stage_nsis_legal(
            output_root=root,
            version=version,
            source_url=source_url,
            expected_sha256=source_sha,
        )
    except (OSError, NSISLegalError) as exc:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise ReleaseManifestError(f"NSIS legal/provenance gate failed: {exc}") from exc

    if result.get("expected_sha256_enforced") is not True:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise ReleaseManifestError("NSIS legal/provenance gate did not enforce the pinned source SHA-256")
    if result.get("source_archive_sha256") != source_sha:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise ReleaseManifestError("NSIS legal/provenance gate returned a different source SHA-256")
    if result.get("version") != version:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise ReleaseManifestError("NSIS legal/provenance gate returned a different version")
    return result


def _build(args: argparse.Namespace) -> int:
    try:
        frontend_legal = _stage_frontend_legal_before_manifest(args.root)
        nsis_legal = _stage_nsis_legal_before_manifest(args.root)
        manifest = build_release_manifest(
            args.root,
            product_version=args.product_version,
            build_id=args.build_id,
            target_arch=args.arch,
            components=args.component,
        )
        path = write_release_manifest(manifest, args.root)
    except (OSError, ReleaseManifestError) as exc:
        _json({"ok": False, "error": str(exc)})
        return 2
    result: dict[str, object] = {
        "ok": True,
        "manifest": path.name,
        "files": len(manifest.files),
    }
    if frontend_legal is not None:
        result["frontend_legal"] = frontend_legal
    if nsis_legal is not None:
        result["nsis_legal"] = nsis_legal
    _json(result)
    return 0


def _verify(args: argparse.Namespace) -> int:
    try:
        manifest = load_release_manifest(args.root)
        result = verify_release_tree(
            manifest,
            args.root,
            verify_hashes=args.deep,
        )
    except (OSError, ReleaseManifestError) as exc:
        result = {
            "ok": False,
            "verify_hashes": args.deep,
            "checked_files": 0,
            "problems": [str(exc)],
        }
    _json(result)
    return 0 if result["ok"] else 2


def _diagnostics(args: argparse.Namespace) -> int:
    previous = os.environ.get("UV_STUDIO_RELEASE_ROOT")
    try:
        if args.root is not None:
            os.environ["UV_STUDIO_RELEASE_ROOT"] = str(Path(args.root).expanduser())
        snapshot = build_diagnostics(verify_release=args.deep)
    finally:
        if args.root is not None:
            if previous is None:
                os.environ.pop("UV_STUDIO_RELEASE_ROOT", None)
            else:
                os.environ["UV_STUDIO_RELEASE_ROOT"] = previous
    _json(snapshot)
    return 0 if snapshot["overall_status"] != "invalid_release" else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-manifest", help="hash an exact Windows release payload")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--product-version", required=True)
    build.add_argument("--build-id", required=True)
    build.add_argument("--arch", choices=("x86_64", "arm64"), required=True)
    build.add_argument(
        "--component",
        action="append",
        type=_component,
        required=True,
        help=(
            "repeat exactly once for each required component "
            f"({', '.join(REQUIRED_RELEASE_COMPONENT_IDS)})"
        ),
    )
    build.set_defaults(func=_build)

    verify = sub.add_parser("verify", help="verify an existing release manifest and payload")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--deep", action="store_true", help="also verify every SHA-256")
    verify.set_defaults(func=_verify)

    diagnostics = sub.add_parser("diagnostics", help="print secret-safe product diagnostics")
    diagnostics.add_argument("--root", type=Path)
    diagnostics.add_argument("--deep", action="store_true", help="deep-verify configured release payload")
    diagnostics.set_defaults(func=_diagnostics)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
