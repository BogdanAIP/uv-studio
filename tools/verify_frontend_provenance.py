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
    """Bind the lock identity to the provenance emitted when the vendor snapshot was created."""
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


def _tree_entries(repository: str, tree_sha: str, *, recursive: bool = False) -> dict[str, Any]:
    suffix = "?recursive=1" if recursive else ""
    payload = github_json(f"{GITHUB_API}/repos/{repository}/git/trees/{tree_sha}{suffix}")
    if payload.get("sha") != tree_sha:
        raise ProvenanceError(
            f"Upstream GitHub tree identity mismatch: requested {tree_sha}, got {payload.get('sha')!r}"
        )
    if payload.get("truncated") is True:
        raise ProvenanceError(f"Upstream GitHub tree {tree_sha} was truncated")
    if not isinstance(payload.get("tree"), list):
        raise ProvenanceError(f"Upstream GitHub tree {tree_sha} has no tree entries")
    return payload


def resolve_upstream_frontend(lock: dict[str, Any]) -> tuple[str, list[tuple[str, str, str]]]:
    """Resolve the claimed commit and frontend subtree from GitHub, independent of local markers."""
    repository = _validate_repository_slug(lock["repository"])
    commit = str(lock["commit"])
    commit_payload = github_json(f"{GITHUB_API}/repos/{repository}/commits/{commit}")
    if commit_payload.get("sha") != commit:
        raise ProvenanceError(
            f"Upstream commit identity mismatch: requested {commit}, got {commit_payload.get('sha')!r}"
        )
    try:
        tree_sha = commit_payload["commit"]["tree"]["sha"]
    except (KeyError, TypeError) as exc:
        raise ProvenanceError("Upstream commit response did not include a root tree SHA") from exc
    if not _valid_sha(tree_sha):
        raise ProvenanceError(f"Upstream commit returned invalid root tree SHA: {tree_sha!r}")

    current_tree = str(tree_sha)
    path_parts = [*str(lock["subtree"]).split("/"), "frontend"]
    walked: list[str] = []
    for part in path_parts:
        tree_payload = _tree_entries(repository, current_tree)
        candidates = [
            entry
            for entry in tree_payload["tree"]
            if isinstance(entry, dict) and entry.get("path") == part
        ]
        if len(candidates) != 1:
            joined = "/".join([*walked, part])
            raise ProvenanceError(f"Pinned upstream tree path is missing or ambiguous: {joined}")
        entry = candidates[0]
        if entry.get("type") != "tree" or entry.get("mode") != "040000" or not _valid_sha(entry.get("sha")):
            joined = "/".join([*walked, part])
            raise ProvenanceError(f"Pinned upstream path is not a normal Git tree: {joined}")
        current_tree = str(entry["sha"])
        walked.append(part)

    frontend_tree_sha = current_tree
    frontend_tree = _tree_entries(repository, frontend_tree_sha, recursive=True)
    entries: list[tuple[str, str, str]] = []
    for raw_entry in frontend_tree["tree"]:
        if not isinstance(raw_entry, dict):
            raise ProvenanceError("Upstream frontend tree contained a malformed entry")
        entry_type = raw_entry.get("type")
        if entry_type == "tree":
            continue
        relative = raw_entry.get("path")
        mode = raw_entry.get("mode")
        blob_sha = raw_entry.get("sha")
        if entry_type != "blob" or not isinstance(relative, str):
            raise ProvenanceError(f"Upstream frontend contains unsupported tree entry: {raw_entry!r}")
        if mode not in {"100644", "100755"} or not _valid_sha(blob_sha):
            raise ProvenanceError(f"Upstream frontend contains unsupported Git entry: {relative}")
        entries.append((relative, str(mode), str(blob_sha)))
    if not entries:
        raise ProvenanceError("Resolved upstream frontend tree contains no files")
    return frontend_tree_sha, entries


def validate_upstream_snapshot(lock: dict[str, Any], local_entries: list[tuple[str, str, str]]) -> str:
    """Bind every local vendored frontend Git blob to the independently resolved upstream tree."""
    frontend_tree_sha, upstream_entries = resolve_upstream_frontend(lock)
    local_map = {path: (mode, blob_sha) for path, mode, blob_sha in local_entries}
    upstream_map = {path: (mode, blob_sha) for path, mode, blob_sha in upstream_entries}
    if len(local_map) != len(local_entries) or len(upstream_map) != len(upstream_entries):
        raise ProvenanceError("Duplicate frontend paths detected while binding upstream provenance")

    missing = sorted(set(upstream_map) - set(local_map))
    extra = sorted(set(local_map) - set(upstream_map))
    changed = sorted(
        path
        for path in set(local_map) & set(upstream_map)
        if local_map[path] != upstream_map[path]
    )
    if missing or extra or changed:
        details: list[str] = []
        if missing:
            details.append(f"missing local paths: {missing[:10]}")
        if extra:
            details.append(f"extra local paths: {extra[:10]}")
        if changed:
            preview = [
                f"{path}: local={local_map[path]!r}, upstream={upstream_map[path]!r}"
                for path in changed[:10]
            ]
            details.append("blob/mode mismatches: " + "; ".join(preview))
        raise ProvenanceError("Vendored frontend does not match the resolved upstream commit:\n- " + "\n- ".join(details))
    return frontend_tree_sha


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
    upstream_frontend_tree_sha = validate_upstream_snapshot(lock, entries)
    digest, files = source_digest(entries)
    validate_provenance(lock, marker, digest=digest, file_count=len(files))
    return {
        "status": "ok",
        "mode": "read-only",
        "source_commit": lock["commit"],
        "source_file_count": len(files),
        "source_tree_sha256": digest,
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
