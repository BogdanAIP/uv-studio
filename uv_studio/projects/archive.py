"""Portable, validated UV Studio project archives.

Archive imports are staged and fully validated before a project directory is
committed into the canonical Project Store. The format is intentionally owned by
UV Studio rather than by the pinned VideoClaw runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .models import PROJECT_SCHEMA_VERSION, ProjectDocument, utc_now_iso
from .store import PROJECT_DIRECTORIES, ProjectAlreadyExists, ProjectStore

ARCHIVE_SCHEMA_VERSION = 1
ARCHIVE_MANIFEST = ".uv-project-archive.json"
PROJECT_PREFIX = "project"


class ProjectArchiveError(RuntimeError):
    pass


class UnsupportedArchiveSchema(ProjectArchiveError):
    pass


@dataclass(frozen=True)
class ArchiveLimits:
    max_entries: int = 100_000
    max_total_uncompressed_bytes: int = 100 * 1024**3
    max_single_file_bytes: int = 50 * 1024**3
    max_manifest_bytes: int = 4 * 1024**2


DEFAULT_LIMITS = ArchiveLimits()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_stream(handle, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while chunk := handle.read(chunk_size):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _safe_archive_output(project_dir: Path, archive_path: Path) -> Path:
    resolved = archive_path.expanduser().resolve()
    if resolved == project_dir or project_dir in resolved.parents:
        raise ProjectArchiveError("Archive output cannot be inside the project being archived")
    return resolved


def _iter_project_entries(project_dir: Path) -> tuple[list[Path], list[Path]]:
    directories: list[Path] = []
    files: list[Path] = []
    for path in sorted(project_dir.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ProjectArchiveError(f"Project archive does not allow symlinks: {path}")
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            files.append(path)
        else:
            raise ProjectArchiveError(f"Unsupported project filesystem entry: {path}")
    return directories, files


def _archive_relative_name(project_dir: Path, path: Path) -> str:
    relative = path.relative_to(project_dir).as_posix()
    return f"{PROJECT_PREFIX}/{relative}"


def _write_zip_directory(archive: zipfile.ZipFile, name: str) -> None:
    info = zipfile.ZipInfo(name.rstrip("/") + "/")
    info.create_system = 3
    info.external_attr = (stat.S_IFDIR | 0o755) << 16
    archive.writestr(info, b"")


def export_project(
    store: ProjectStore,
    project_id: str,
    archive_path: Path | str,
) -> Path:
    """Export a complete canonical project directory to a validated ZIP format."""
    document = store.load_project(project_id)
    project_dir = store.project_path(project_id).parent
    destination = _safe_archive_output(project_dir, Path(archive_path))
    destination.parent.mkdir(parents=True, exist_ok=True)

    directories, files = _iter_project_entries(project_dir)
    file_records: list[dict[str, Any]] = []
    for path in files:
        file_records.append(
            {
                "path": _archive_relative_name(project_dir, path),
                "size": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )

    manifest = {
        "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
        "project_id": document.project_id,
        "project_schema_version": document.schema_version,
        "created_at": utc_now_iso(),
        "files": file_records,
    }

    temp_path = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(
            temp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
        ) as archive:
            archive.writestr(
                ARCHIVE_MANIFEST,
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
            _write_zip_directory(archive, PROJECT_PREFIX)
            for directory in directories:
                _write_zip_directory(archive, _archive_relative_name(project_dir, directory))
            for path in files:
                archive.write(path, _archive_relative_name(project_dir, path))
        os.replace(temp_path, destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return destination


def create_backup(
    store: ProjectStore,
    project_id: str,
    backup_root: Path | str,
) -> Path:
    """Create a timestamped portable project backup and return its exact path."""
    store.load_project(project_id)
    root = Path(backup_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = root / f"{project_id}-{timestamp}-{uuid.uuid4().hex[:8]}.uvproj.zip"
    return export_project(store, project_id, destination)


def _normalize_member_name(name: str) -> str:
    if not isinstance(name, str) or not name:
        raise ProjectArchiveError("Archive contains an empty member name")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ProjectArchiveError(f"Unsafe archive path: {name!r}")
    if len(path.parts) and len(path.parts[0]) == 2 and path.parts[0][1:] == ":":
        raise ProjectArchiveError(f"Windows absolute archive path is not allowed: {name!r}")
    if any(part in {"", "."} for part in path.parts):
        raise ProjectArchiveError(f"Non-canonical archive path: {name!r}")
    return path.as_posix()


def _validate_zip_file_type(info: zipfile.ZipInfo) -> None:
    if info.flag_bits & 0x1:
        raise ProjectArchiveError(f"Encrypted ZIP entries are not supported: {info.filename}")
    if info.create_system != 3:
        return
    mode = info.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ProjectArchiveError(f"Links/special files are not allowed: {info.filename}")


def _validated_members(
    archive: zipfile.ZipFile,
    limits: ArchiveLimits,
) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > limits.max_entries:
        raise ProjectArchiveError(
            f"Archive has too many entries ({len(infos)} > {limits.max_entries})"
        )

    normalized: dict[str, zipfile.ZipInfo] = {}
    casefolded: set[str] = set()
    total = 0
    for info in infos:
        _validate_zip_file_type(info)
        name = _normalize_member_name(info.filename.rstrip("/"))
        folded = name.casefold()
        if name in normalized or folded in casefolded:
            raise ProjectArchiveError(f"Duplicate/case-colliding archive path: {info.filename}")
        casefolded.add(folded)
        normalized[name] = info

        if not info.is_dir():
            if info.file_size > limits.max_single_file_bytes:
                raise ProjectArchiveError(f"Archive member is too large: {info.filename}")
            total += info.file_size
            if total > limits.max_total_uncompressed_bytes:
                raise ProjectArchiveError("Archive exceeds maximum uncompressed size")

        if name != ARCHIVE_MANIFEST and name != PROJECT_PREFIX and not name.startswith(f"{PROJECT_PREFIX}/"):
            raise ProjectArchiveError(f"Unexpected archive entry outside project/: {info.filename}")

    return normalized


def _read_manifest(
    archive: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    limits: ArchiveLimits,
) -> dict[str, Any]:
    info = members.get(ARCHIVE_MANIFEST)
    if info is None or info.is_dir():
        raise ProjectArchiveError(f"Archive is missing {ARCHIVE_MANIFEST}")
    if info.file_size > limits.max_manifest_bytes:
        raise ProjectArchiveError("Archive manifest is too large")
    try:
        data = json.loads(archive.read(info).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectArchiveError("Archive manifest is not valid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise ProjectArchiveError("Archive manifest must be a JSON object")
    version = data.get("archive_schema_version")
    if version != ARCHIVE_SCHEMA_VERSION:
        raise UnsupportedArchiveSchema(
            f"Unsupported archive schema: {version!r}; supported={ARCHIVE_SCHEMA_VERSION}"
        )
    return data


def _manifest_file_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = manifest.get("files")
    if not isinstance(raw, list):
        raise ProjectArchiveError("Archive manifest files must be a list")
    records: dict[str, dict[str, Any]] = {}
    folded: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ProjectArchiveError("Archive manifest file record must be an object")
        try:
            path = _normalize_member_name(str(item["path"]))
            size = item["size"]
            sha256 = item["sha256"]
        except KeyError as exc:
            raise ProjectArchiveError(f"Archive manifest file record missing {exc.args[0]}") from exc
        if not path.startswith(f"{PROJECT_PREFIX}/"):
            raise ProjectArchiveError(f"Manifest file is outside project/: {path}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ProjectArchiveError(f"Invalid file size in manifest: {path}")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise ProjectArchiveError(f"Invalid SHA-256 in manifest: {path}")
        try:
            int(sha256, 16)
        except ValueError as exc:
            raise ProjectArchiveError(f"Invalid SHA-256 in manifest: {path}") from exc
        folded_path = path.casefold()
        if path in records or folded_path in folded:
            raise ProjectArchiveError(f"Duplicate manifest file path: {path}")
        folded.add(folded_path)
        records[path] = {"path": path, "size": size, "sha256": sha256.lower()}
    return records


def _validate_declared_files(
    members: dict[str, zipfile.ZipInfo],
    records: dict[str, dict[str, Any]],
) -> None:
    actual_files = {
        name
        for name, info in members.items()
        if name.startswith(f"{PROJECT_PREFIX}/") and not info.is_dir()
    }
    declared = set(records)
    missing = declared - actual_files
    undeclared = actual_files - declared
    if missing:
        raise ProjectArchiveError(f"Archive is missing declared files: {sorted(missing)!r}")
    if undeclared:
        raise ProjectArchiveError(f"Archive contains undeclared files: {sorted(undeclared)!r}")
    if f"{PROJECT_PREFIX}/project.json" not in declared:
        raise ProjectArchiveError("Archive does not declare project/project.json")


def _extract_project(
    archive: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    records: dict[str, dict[str, Any]],
    staging_project: Path,
) -> None:
    staging_project.mkdir(parents=True, exist_ok=False)

    # Create declared project directories first, including empty ones.
    for name, info in sorted(members.items()):
        if not info.is_dir() or name == PROJECT_PREFIX:
            continue
        if not name.startswith(f"{PROJECT_PREFIX}/"):
            continue
        relative = PurePosixPath(name).relative_to(PROJECT_PREFIX)
        target = staging_project.joinpath(*relative.parts).resolve()
        if staging_project.resolve() not in target.parents and target != staging_project.resolve():
            raise ProjectArchiveError(f"Archive directory escaped staging: {name}")
        target.mkdir(parents=True, exist_ok=True)

    for name, record in sorted(records.items()):
        info = members[name]
        relative = PurePosixPath(name).relative_to(PROJECT_PREFIX)
        target = staging_project.joinpath(*relative.parts).resolve()
        if staging_project.resolve() not in target.parents:
            raise ProjectArchiveError(f"Archive file escaped staging: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        with archive.open(info, "r") as source, target.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if size != record["size"]:
            raise ProjectArchiveError(
                f"Size mismatch for {name}: expected={record['size']} actual={size}"
            )
        if digest.hexdigest() != record["sha256"]:
            raise ProjectArchiveError(f"SHA-256 mismatch for {name}")


def import_project(
    store: ProjectStore,
    archive_path: Path | str,
    *,
    limits: ArchiveLimits = DEFAULT_LIMITS,
) -> ProjectDocument:
    """Validate and atomically import one portable UV Studio project archive."""
    source = Path(archive_path).expanduser().resolve()
    if not source.is_file():
        raise ProjectArchiveError(f"Project archive does not exist: {source}")

    try:
        archive = zipfile.ZipFile(source, "r")
    except zipfile.BadZipFile as exc:
        raise ProjectArchiveError(f"Invalid ZIP archive: {source}") from exc

    with archive:
        members = _validated_members(archive, limits)
        manifest = _read_manifest(archive, members, limits)
        records = _manifest_file_records(manifest)
        _validate_declared_files(members, records)

        project_id = manifest.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ProjectArchiveError("Archive manifest has no project_id")
        if (store.root / project_id).exists():
            raise ProjectAlreadyExists(project_id)

        with tempfile.TemporaryDirectory(prefix=".uv-import-", dir=store.root) as temp:
            temp_root = Path(temp)
            staging_project = temp_root / project_id
            _extract_project(archive, members, records, staging_project)

            # Ensure standard directories exist even when they were empty and an
            # archive producer omitted explicit directory entries.
            for name in PROJECT_DIRECTORIES:
                (staging_project / name).mkdir(parents=True, exist_ok=True)

            staged_store = ProjectStore(temp_root)
            document = staged_store.load_project(project_id)
            if document.project_id != project_id:
                raise ProjectArchiveError("Manifest project_id does not match project.json")
            if manifest.get("project_schema_version") != document.schema_version:
                raise ProjectArchiveError(
                    "Manifest project_schema_version does not match project.json"
                )
            if document.schema_version != PROJECT_SCHEMA_VERSION:
                raise ProjectArchiveError(
                    f"Unsupported imported project schema: {document.schema_version}"
                )

            store.commit_staged_project(staging_project, project_id)
            return store.load_project(project_id)
