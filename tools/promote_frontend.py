#!/usr/bin/env python3
"""Promote the pinned VideoClaw frontend into UV Studio-owned derived source.

The untouched vendored frontend remains the upstream comparison snapshot. This
tool creates a reproducible starting copy at top-level `frontend/`, records the
exact upstream pin and source-tree digest, and preserves the MIT license.

Once UV Studio has product changes in `frontend/`, replacing that directory is
intentionally destructive and therefore always requires explicit `--force`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "upstream" / "video-claw.lock.json"
SOURCE = ROOT / "vendor" / "videoclaw-app" / "frontend"
UPSTREAM_LICENSE = ROOT / "vendor" / "videoclaw-app" / "UPSTREAM_LICENSE"
DEFAULT_DESTINATION = ROOT / "frontend"
PROVENANCE_FILE = ".uv-derived.json"


class PromotionError(RuntimeError):
    pass


def load_upstream_pin() -> dict[str, str]:
    data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    required = ("repository", "commit", "subtree", "license")
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise PromotionError(f"Upstream lock missing: {', '.join(missing)}")
    return {key: str(data[key]) for key in required}


def safe_destination(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root:
        raise PromotionError("Frontend destination cannot be repository root")
    if root not in resolved.parents:
        raise PromotionError("Frontend destination must stay inside repository root")
    if resolved == SOURCE.resolve() or SOURCE.resolve() in resolved.parents:
        raise PromotionError("Cannot promote frontend into the vendored source tree")
    return resolved


def iter_source_files(source: Path = SOURCE) -> list[Path]:
    if not source.is_dir():
        raise PromotionError(f"Pinned frontend source is missing: {source}")
    files: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise PromotionError(f"Symlink is not allowed in promoted frontend: {path}")
        if path.is_file():
            files.append(path)
    if not files:
        raise PromotionError("Pinned frontend contains no files")
    return files


def source_digest(source: Path = SOURCE) -> tuple[str, list[Path]]:
    files = iter_source_files(source)
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(source).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), files


def copy_frontend(source: Path, staging: Path) -> list[Path]:
    written: list[Path] = []
    for source_file in iter_source_files(source):
        relative = source_file.relative_to(source)
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target)
        written.append(relative)
    return written


def promote(destination: Path = DEFAULT_DESTINATION, *, force: bool = False) -> dict[str, object]:
    destination = safe_destination(destination)
    pin = load_upstream_pin()
    digest, source_files = source_digest(SOURCE)

    if destination.exists() and not force:
        raise PromotionError(
            f"Destination already exists: {destination}. "
            "Refusing to replace UV Studio frontend changes without explicit --force."
        )
    if not UPSTREAM_LICENSE.is_file():
        raise PromotionError(f"Upstream license is missing: {UPSTREAM_LICENSE}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    # Create staging on the destination filesystem so the final rename works on
    # Windows runners where the system temporary directory may be on C: while
    # the checkout is on D:.
    with tempfile.TemporaryDirectory(
        prefix=".uv-frontend-",
        dir=destination.parent,
    ) as temp:
        staging = Path(temp) / "frontend"
        staging.mkdir()
        copy_frontend(SOURCE, staging)
        shutil.copy2(UPSTREAM_LICENSE, staging / "UPSTREAM_LICENSE")

        provenance: dict[str, object] = {
            "schema_version": 1,
            "managed_by": "tools/promote_frontend.py",
            "source_repository": pin["repository"],
            "source_commit": pin["commit"],
            "source_subtree": f"{pin['subtree']}/frontend",
            "source_tree_sha256": digest,
            "source_file_count": len(source_files),
            "license": pin["license"],
            "license_file": "UPSTREAM_LICENSE",
        }
        (staging / PROVENANCE_FILE).write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if destination.exists():
            shutil.rmtree(destination)
        os.replace(staging, destination)

    return provenance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicitly replace an existing frontend directory. This deletes UV Studio frontend changes.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only print source digest/count and do not create or replace frontend files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        digest, files = source_digest()
        print(json.dumps({"source_tree_sha256": digest, "source_file_count": len(files)}, indent=2))
        return 0
    provenance = promote(args.destination, force=args.force)
    print(json.dumps(provenance, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PromotionError as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2)
