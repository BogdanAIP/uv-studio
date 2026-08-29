#!/usr/bin/env python3
"""Verify the pinned donor frontend provenance without mutating product source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "upstream" / "video-claw.lock.json"
VENDOR_ROOT = ROOT / "vendor" / "videoclaw-app"
VENDOR_PROVENANCE_PATH = VENDOR_ROOT / ".uv-upstream.json"
SOURCE = VENDOR_ROOT / "frontend"
SOURCE_REPO_PATH = SOURCE.relative_to(ROOT).as_posix()
UPSTREAM_LICENSE = VENDOR_ROOT / "UPSTREAM_LICENSE"
FRONTEND = ROOT / "frontend"
PROVENANCE_PATH = FRONTEND / ".uv-derived.json"
FRONTEND_LICENSE = FRONTEND / "UPSTREAM_LICENSE"
GITHUB_API = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


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


def _valid_sha(value: object) -> bool:
    text = str(value)
    return len(text) == 40 and all(char in "0123456789abcdef" for char in text)


def _validate_repository_slug(value: object) -> str:
    repository = str(value)
    parts = repository.split("/")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if len(parts) != 2 or any(not part or any(char not in allowed for char in part) for part in parts):
        raise ProvenanceError(f"Pinned VideoClaw repository must be an owner/repo slug, got {repository!r}")
    return repository


def load_upstream_pin() -> dict[str, Any]:
    lock = read_json(LOCK_PATH)
    required = ("repository", "commit", "subtree", "license")
    missing = [key for key in required if not lock.get(key)]
    if missing:
        raise ProvenanceError(f"{LOCK_PATH.relative_to(ROOT)} is missing fields: {missing}")
    _validate_repository_slug(lock["repository"])
    commit = str(lock["commit"])
    if not _valid_sha(commit):
        raise ProvenanceError("Pinned VideoClaw commit must be a lowercase 40-character SHA")
    subtree_parts = str(lock["subtree"]).split("/")
    if any(not part or part in {".", ".."} for part in subtree_parts):
        raise ProvenanceError("Pinned VideoClaw subtree must be a normalized repository path")
    return lock


def validate_vendored_identity(lock: dict[str, Any], vendor_marker: dict[str, Any]) -> None:
    expected: dict[str, Any] = {
        "repository": lock["repository"],
        "commit": lock["commit"],
        "subtree": lock["subtree"],
        "license": lock["license"],
        "license_file": "UPSTREAM_LICENSE",
    }
    mismatches = [
        f"{key}: expected {value!r}, got {vendor_marker.get(key)!r}"
        for key, value in expected.items()
        if vendor_marker.get(key) != value
    ]
    file_count = vendor_marker.get("file_count")
    if not isinstance(file_count, int) or isinstance(file_count, bool) or file_count <= 0:
        mismatches.append(f"file_count: expected positive integer, got {file_count!r}")
    if mismatches:
        raise ProvenanceError("Vendored snapshot identity mismatch:\n- " + "\n- ".join(mismatches))


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


def local_source_tree_sha() -> str:
    """Return the exact Git tree identity of the checked-out vendored frontend."""
    if not SOURCE.is_dir():
        raise ProvenanceError(f"Pinned donor frontend is missing: {SOURCE.relative_to(ROOT)}")
    require_clean_source()
    result = run_git("rev-parse", f"HEAD:{SOURCE_REPO_PATH}")
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(f"Could not resolve local donor frontend Git tree: {detail or 'git rev-parse failed'}")
    tree_sha = result.stdout.decode("ascii", errors="strict").strip()
    if not _valid_sha(tree_sha):
        raise ProvenanceError(f"Local donor frontend returned invalid Git tree SHA: {tree_sha!r}")
    return tree_sha


def source_entries() -> list[tuple[str, str, str]]:
    """Return relative path, Git mode and Git blob SHA for the pinned local frontend."""
    if not SOURCE.is_dir():
        raise ProvenanceError(f"Pinned donor frontend is missing: {SOURCE.relative_to(ROOT)}")
    require_clean_source()
    listing = run_git("ls-files", "--stage", "-z", "--", SOURCE_REPO_PATH)
    if listing.returncode != 0:
        detail = listing.stderr.decode("utf-8", errors="replace").strip()
        raise ProvenanceError(f"Could not enumerate donor Git blobs: {detail or 'git ls-files failed'}")

    entries: list[tuple[str, str, str]] = []
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
        if not _valid_sha(blob_sha):
            raise ProvenanceError(f"Pinned donor frontend contains invalid Git blob SHA: {repo_path}")
        prefix = f"{SOURCE_REPO_PATH}/"
        if not repo_path.startswith(prefix):
            raise ProvenanceError(f"Unexpected donor path returned by Git: {repo_path}")
        entries.append((repo_path[len(prefix):], mode, blob_sha))

    if not entries:
        raise ProvenanceError("Pinned donor frontend contains no tracked files")
    return entries


def source_digest(entries: list[tuple[str, str, str]] | None = None) -> tuple[str, list[str]]:
    if entries is None:
        entries = source_entries()
    digest = hashlib.sha256()
    relative_files: list[str] = []
    for relative_text, _mode, blob_sha in sorted(entries):
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


def github_json(url: str) -> dict[str, Any]:
    """Read immutable public GitHub commit/tree evidence without touching the workspace."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "uv-studio-frontend-provenance",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"Could not resolve upstream GitHub evidence: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProvenanceError("Upstream GitHub response must contain a JSON object")
    return payload


def _tree_payload(repository: str, tree_sha: str) -> dict[str, Any]:
    payload = github_json(f"{GITHUB_API}/repos/{repository}/git/trees/{tree_sha}")
    if payload.get("sha") != tree_sha:
        raise ProvenanceError(
            f"Upstream GitHub tree identity mismatch: requested {tree_sha}, got {payload.get('sha')!r}"
        )
    if payload.get("truncated") is True:
        raise ProvenanceError(f"Upstream GitHub tree {tree_sha} was truncated")
    if not isinstance(payload.get("tree"), list):
        raise ProvenanceError(f"Upstream GitHub tree {tree_sha} has no tree entries")
    return payload


def resolve_upstream_frontend_tree(lock: dict[str, Any]) -> str:
    """Resolve the exact frontend tree from the claimed public upstream commit."""
    repository = _validate_repository_slug(lock["repository"])
    commit = str(lock["commit"])
    commit_payload = github_json(f"{GITHUB_API}/repos/{repository}/git/commits/{commit}")
    if commit_payload.get("sha") != commit:
        raise ProvenanceError(
            f"Upstream commit identity mismatch: requested {commit}, got {commit_payload.get('sha')!r}"
        )
    try:
        root_tree_sha = commit_payload["tree"]["sha"]
    except (KeyError, TypeError) as exc:
        raise ProvenanceError("Upstream commit response did not include a root tree SHA") from exc
    if not _valid_sha(root_tree_sha):
        raise ProvenanceError(f"Upstream commit returned invalid root tree SHA: {root_tree_sha!r}")

    current_tree = str(root_tree_sha)
    walked: list[str] = []
    for part in [*str(lock["subtree"]).split("/"), "frontend"]:
        tree_payload = _tree_payload(repository, current_tree)
        matches = [
            entry
            for entry in tree_payload["tree"]
            if isinstance(entry, dict) and entry.get("path") == part
        ]
        if len(matches) != 1:
            joined = "/".join([*walked, part])
            raise ProvenanceError(f"Pinned upstream tree path is missing or ambiguous: {joined}")
        entry = matches[0]
        if entry.get("type") != "tree" or entry.get("mode") != "040000" or not _valid_sha(entry.get("sha")):
            joined = "/".join([*walked, part])
            raise ProvenanceError(f"Pinned upstream path is not a normal Git tree: {joined}")
        current_tree = str(entry["sha"])
        walked.append(part)
    return current_tree


def validate_upstream_snapshot(lock: dict[str, Any], *, local_tree_sha: str | None = None) -> str:
    """Bind local vendored bytes to the independently resolved upstream Git tree."""
    local_tree = local_tree_sha or local_source_tree_sha()
    if not _valid_sha(local_tree):
        raise ProvenanceError(f"Local donor frontend returned invalid Git tree SHA: {local_tree!r}")
    upstream_tree = resolve_upstream_frontend_tree(lock)
    if local_tree != upstream_tree:
        raise ProvenanceError(
            "Vendored frontend Git tree does not match the pinned upstream commit: "
            f"local={local_tree}, upstream={upstream_tree}"
        )
    return upstream_tree


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
    vendor_marker = read_json(VENDOR_PROVENANCE_PATH)
    validate_vendored_identity(lock, vendor_marker)
    marker = read_json(PROVENANCE_PATH)
    if not UPSTREAM_LICENSE.is_file():
        raise ProvenanceError("Pinned VideoClaw UPSTREAM_LICENSE is missing")
    if not FRONTEND_LICENSE.is_file():
        raise ProvenanceError("frontend/UPSTREAM_LICENSE is missing")
    if FRONTEND_LICENSE.read_bytes() != UPSTREAM_LICENSE.read_bytes():
        raise ProvenanceError("frontend/UPSTREAM_LICENSE does not match the pinned donor license")

    entries = source_entries()
    local_tree_sha = local_source_tree_sha()
    upstream_frontend_tree_sha = validate_upstream_snapshot(lock, local_tree_sha=local_tree_sha)
    digest, files = source_digest(entries)
    validate_provenance(lock, marker, digest=digest, file_count=len(files))
    return {
        "status": "ok",
        "mode": "read-only",
        "source_commit": lock["commit"],
        "source_file_count": len(files),
        "source_tree_sha256": digest,
        "local_frontend_tree_sha": local_tree_sha,
        "upstream_frontend_tree_sha": upstream_frontend_tree_sha,
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
            f"{result['source_commit']} ({result['source_file_count']} pinned files, read-only, "
            f"upstream tree {result['upstream_frontend_tree_sha']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
