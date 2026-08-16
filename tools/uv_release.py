#!/usr/bin/env python3
"""Release-manifest and diagnostics utility for Stage 9 packaging/support flows."""

from __future__ import annotations

import argparse
import json
import os
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


def _build(args: argparse.Namespace) -> int:
    try:
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
    _json({"ok": True, "manifest": path.name, "files": len(manifest.files)})
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
