#!/usr/bin/env python3
"""Verify the pinned donor frontend provenance without mutating product source."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "upstream" / "video-claw.lock.json"
SOURCE = ROOT / "vendor" / "videoclaw-app" / "frontend"
SOURCE_REPO_PATH = SOURCE.relative_to(ROOT).as_posix()
UPSTREAM_LICENSE = ROOT / "vendor" / "videoclaw-app" / "UPSTREAM_LICENSE"
FRONTEND = ROOT / "frontend"
PROVENANCE_PATH = FRONTEND / ".uv-derived.json"
FRONTEND_LICENSE = FRONTEND / "UPSTREAM_LICENSE"


class ProvenanceError(RuntimeError):
    """Raised when frontend provenance cannot be verified exactly."""


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ProvenanceError(f"Required provenance file is missing: {path.relative_to(ROOT)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"Could not read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProvenanceError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return payload


def load_upstream_pin() -> dict[str, Any]:
    lock = read_json(LOCK_PATH)
    required = ("repository", "commit", "subtree", "license")
    missing = [key for key in required if not lock.get(key)]
    if missing:
        raise ProvenanceError(f"{LOCK_PATH.relative_to(ROOT)} is missing fields: {missing}")
    commit = str(lock["commit"])
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ProvenanceError("Pinned VideoClaw commit must be a lowercase 40-character SHA")
    return lock


def run_git(*args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ProvenanceError(f"Git is required for provenance verification: {exc}") from exc


def require_clean_source() -> None:
    diff = run_git("diff", "--quiet", "--", SOURCE_REPO_PATH)
    if diff.returncode == 1:
        raise ProvenanceError("Pinned donor frontend has tracked working-tree changes")
    if diff.returncode != 0:
        detail = diff.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(f"Could not verify donor working-tree state: {detail or 'git diff failed'}")

    staged = run_git("diff", "--cached", "--quiet", "--", SOURCE_REPO_PATH)
    if staged.returncode == 1:
        raise ProvenanceError("Pinned donor frontend has staged changes")
    if staged.returncode != 0:
        detail = staged.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(f"Could not verify donor index state: {detail or 'git diff --cached failed'}")

    untracked = run_git("ls-files", "--others", "--exclude-standard", "-z", "--", SOURCE_REPO_PATH)
    if untracked.returncode != 0:
        detail = untracked.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(f"Could not inspect donor untracked files: {detail or 'git ls-files failed'}")
    if untracked.stdout:
        paths = [item.decode("utf-8", errors="replace") for item in untracked.stdout.split(b"\0") if item]
        raise ProvenanceError(f"Pinned donor frontend contains untracked files: {paths}")


def source_digest() -> tuple[str, list[str]]:
    if not SOURCE.is_dir():
        raise ProvenanceError(f"Pinned donor frontend is missing: {SOURCE.relative_to(ROOT)}")

    require_clean_source()
    listing = run_git("ls-files", "--stage", "-z", "--", SOURCE_REPO_PATH)
    if listing.returncode != 0:
        detail = listing.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(f"Could not enumerate donor Git blobs: {detail or 'git ls-files failed'}")

    entries: list[tuple[str, str]] = []
    for raw in listing.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, raw_path = raw.split(b"\t", 1)
            mode, blob_sha, stage = metadata.decode("ascii").split(" ")
            repo_path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProvenanceError("Could not parse donor Git index entry") from exc
        if stage != "0":
            raise ProvenanceError(f"Pinned donor frontend has an unmerged index entry: {repo_path}")
        if mode not in {"100644", "100755"}:
            raise ProvenanceError(f"Pinned donor frontend contains unsupported Git mode {mode}: {repo_path}")
        prefix = f"{SOURCE_REPO_PATH}/"
        if not repo_path.startswith(prefix):
            raise ProvenanceError(f"Unexpected donor path returned by Git: {repo_path}")
        entries.append((repo_path[len(prefix):], blob_sha))

    if not entries:
        raise ProvenanceError("Pinned donor frontend contains no tracked files")

    digest = hashlib.sha256()
    relative_files: list[str] = []
    for relative_text, blob_sha in sorted(entries):
        blob = run_git("cat-file", "blob", blob_sha)
        if blob.returncode != 0:
            detail = blob.stderr.decode("utf-8", errors="replace").strip()
            raise ProvenanceError(f"Could not read donor Git blob {blob_sha}: {detail or 'git cat-file failed'}")
        relative = relative_text.encode("utf-8")
        content = blob.stdout
        relative_files.append(relative_text)
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), relative_files


def validate_provenance(
    lock: dict[str, Any],
    marker: dict[str, Any],
    *,
    digest: str,
    file_count: int,
) -> None:
    expected: dict[str, Any] = {
        "schema_version": 2,
        "record_type": "read_only_provenance",
        "verified_by": "tools/verify_frontend_provenance.py",
        "source_repository": lock["repository"],
        "source_commit": lock["commit"],
        "source_subtree": f"{lock['subtree']}/frontend",
        "license": lock["license"],
        "license_file": "UPSTREAM_LICENSE",
        "source_tree_sha256": digest,
        "source_file_count": file_count,
    }
    mismatches = [
        f"{key}: expected {value!r}, got {marker.get(key)!r}"
        for key, value in expected.items()
        if marker.get(key) != value
    ]
    if mismatches:
        raise ProvenanceError("Frontend provenance mismatch:\n- " + "\n- ".join(mismatches))


def verify() -> dict[str, Any]:
    lock = load_upstream_pin()
    marker = read_json(PROVENANCE_PATH)
    if not UPSTREAM_LICENSE.is_file():
        raise ProvenanceError("Pinned VideoClaw UPSTREAM_LICENSE is missing")
    if not FRONTEND_LICENSE.is_file():
        raise ProvenanceError("frontend/UPSTREAM_LICENSE is missing")
    if FRONTEND_LICENSE.read_bytes() != UPSTREAM_LICENSE.read_bytes():
        raise ProvenanceError("frontend/UPSTREAM_LICENSE does not match the pinned donor license")

    digest, files = source_digest()
    validate_provenance(lock, marker, digest=digest, file_count=len(files))
    return {
        "status": "ok",
        "mode": "read-only",
        "source_commit": lock["commit"],
        "source_file_count": len(files),
        "source_tree_sha256": digest,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit verification result as JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = verify()
    except ProvenanceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "frontend provenance ok: "
            f"{result['source_commit']} ({result['source_file_count']} pinned files, read-only)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
