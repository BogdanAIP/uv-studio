#!/usr/bin/env python3
"""Vendor the pinned modern VideoClaw application into UV Studio.

The tool intentionally uses only Python's standard library so it can run before
project dependencies are installed. It downloads an exact Git commit archive,
selects only the configured subtree, rejects links/path traversal, preserves the
upstream license, stages files in a temporary directory, and replaces the
destination only after validation.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "upstream" / "video-claw.lock.json"
PRODUCT_FRONTEND = ROOT / "frontend"


@dataclass(frozen=True)
class UpstreamLock:
    repository: str
    commit: str
    subtree: str
    license: str
    license_path: str
    default_destination: str

    @classmethod
    def load(cls, path: Path) -> "UpstreamLock":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported upstream lock schema_version")
        required = [
            "repository",
            "commit",
            "subtree",
            "license",
            "license_path",
            "default_destination",
        ]
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"Missing lock fields: {', '.join(missing)}")
        commit = str(data["commit"])
        if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit.lower()):
            raise ValueError("Upstream commit must be a full 40-character SHA")
        return cls(**{key: str(data[key]) for key in required})

    @property
    def archive_url(self) -> str:
        return f"https://github.com/{self.repository}/archive/{self.commit}.tar.gz"


class VendorError(RuntimeError):
    pass


def safe_destination(path: Path, root: Path = ROOT) -> Path:
    """Resolve a destination and reject writes outside repository/vendor authority."""
    resolved = path.resolve()
    root_resolved = root.resolve()
    frontend_resolved = PRODUCT_FRONTEND.resolve()
    if resolved == root_resolved:
        raise VendorError("Destination cannot be the repository root")
    if resolved == frontend_resolved or frontend_resolved in resolved.parents:
        raise VendorError(
            "Destination cannot target UV Studio product frontend; "
            "vendor snapshots must remain outside top-level frontend/"
        )
    if root_resolved in resolved.parents:
        return resolved
    raise VendorError(f"Destination must stay inside repository root: {resolved}")


def member_relative_path(member_name: str, archive_root: str, subtree: str) -> Path | None:
    """Map one archive member to its destination-relative path."""
    member = PurePosixPath(member_name)
    prefix = PurePosixPath(archive_root) / PurePosixPath(subtree)
    try:
        relative = member.relative_to(prefix)
    except ValueError:
        return None
    if str(relative) in {"", "."}:
        return None
    if relative.is_absolute() or ".." in relative.parts:
        raise VendorError(f"Unsafe archive member: {member_name}")
    return Path(*relative.parts)


def archive_root_name(repository: str, commit: str) -> str:
    repo_name = repository.rsplit("/", 1)[-1]
    return f"{repo_name}-{commit}"


def download_archive(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "uv-studio-vendor/1"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def stage_subtree(archive_path: Path, lock: UpstreamLock, staging_dir: Path) -> list[Path]:
    root_name = archive_root_name(lock.repository, lock.commit)
    written: list[Path] = []
    staging_resolved = staging_dir.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            relative = member_relative_path(member.name, root_name, lock.subtree)
            if relative is None:
                continue
            if member.issym() or member.islnk():
                raise VendorError(f"Links are not allowed in vendored subtree: {member.name}")
            target = (staging_dir / relative).resolve()
            if staging_resolved not in target.parents and target != staging_resolved:
                raise VendorError(f"Archive member escapes staging directory: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise VendorError(f"Could not read archive member: {member.name}")
            with source, target.open("wb") as out:
                shutil.copyfileobj(source, out)
            written.append(relative)
    if not written:
        raise VendorError(f"No files found for subtree {lock.subtree!r}")
    return sorted(written)


def stage_license(archive_path: Path, lock: UpstreamLock, staging_dir: Path) -> Path:
    root_name = archive_root_name(lock.repository, lock.commit)
    expected = str(PurePosixPath(root_name) / PurePosixPath(lock.license_path))
    with tarfile.open(archive_path, "r:gz") as archive:
        try:
            member = archive.getmember(expected)
        except KeyError as exc:
            raise VendorError(f"Upstream license not found in archive: {lock.license_path}") from exc
        if not member.isfile() or member.issym() or member.islnk():
            raise VendorError("Upstream license must be a regular file")
        source = archive.extractfile(member)
        if source is None:
            raise VendorError("Could not read upstream license")
        target = staging_dir / "UPSTREAM_LICENSE"
        with source, target.open("wb") as out:
            shutil.copyfileobj(source, out)
        return target


def write_provenance(staging_dir: Path, lock: UpstreamLock, files: list[Path]) -> None:
    provenance = {
        "repository": lock.repository,
        "commit": lock.commit,
        "subtree": lock.subtree,
        "license": lock.license,
        "license_file": "UPSTREAM_LICENSE",
        "file_count": len(files),
    }
    (staging_dir / ".uv-upstream.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def vendor(lock_path: Path, destination: Path, *, dry_run: bool = False) -> list[Path]:
    lock = UpstreamLock.load(lock_path)
    destination = safe_destination(destination)

    with tempfile.TemporaryDirectory(prefix="uv-vendor-") as temp:
        temp_dir = Path(temp)
        archive_path = temp_dir / "upstream.tar.gz"
        staging_dir = temp_dir / "staging"
        staging_dir.mkdir()

        download_archive(lock.archive_url, archive_path)
        files = stage_subtree(archive_path, lock, staging_dir)
        stage_license(archive_path, lock, staging_dir)
        write_provenance(staging_dir, lock, files)

        if dry_run:
            return files

        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staging_dir, destination)
        return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--destination",
        type=Path,
        default=None,
        help="Destination inside repository root; top-level frontend/ is forbidden.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download and validate the pinned subtree without modifying repository files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock = UpstreamLock.load(args.lock)
    destination = args.destination or (ROOT / lock.default_destination)
    files = vendor(args.lock, destination, dry_run=args.dry_run)
    action = "validated" if args.dry_run else "vendored"
    print(f"{action} {len(files)} files from {lock.repository}@{lock.commit}")
    if not args.dry_run:
        print(f"destination: {safe_destination(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
