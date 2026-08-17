"""Fail-closed Project Store migration preparation and metadata recovery snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .migrations import migrate_project_data
from .models import PROJECT_SCHEMA_VERSION, ProjectDocument, ProjectValidationError, utc_now_iso, validate_identifier
from .store import PROJECT_FILENAME, ProjectStore

MIGRATION_RECOVERY_SCHEMA_VERSION = 1
MIGRATION_RECOVERY_MANIFEST = "migration-recovery.json"
_SAFE_SET_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class ProjectMaintenanceError(RuntimeError):
    """Project Store preparation could not complete without risking canonical state."""


@dataclass(frozen=True)
class ProjectStorePreparation:
    target_schema_version: int
    migrated_project_ids: tuple[str, ...]
    recovery_snapshot: Path | None


@dataclass(frozen=True)
class _MigrationPlan:
    project_id: str
    project_path: Path
    original_bytes: bytes
    original_schema_version: int
    migrated_data: dict[str, Any]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(data: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _validated_recovery_root(store: ProjectStore, recovery_root: Path | str) -> Path:
    candidate = Path(recovery_root).expanduser()
    if candidate.exists() and candidate.is_symlink():
        raise ProjectMaintenanceError("migration recovery root must not be a symlink")
    root = candidate.resolve()
    if _paths_overlap(root, store.root):
        raise ProjectMaintenanceError(
            "migration recovery root must not overlap the canonical Project Store"
        )
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise ProjectMaintenanceError("migration recovery root must be a real directory")
    return root


def _read_raw_project(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        payload = path.read_bytes()
        decoded = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectMaintenanceError(
            f"project metadata is not readable valid UTF-8 JSON: {path}"
        ) from exc
    if not isinstance(decoded, dict):
        raise ProjectMaintenanceError(f"project metadata must be a JSON object: {path}")
    return payload, decoded


def _plan_project_store_migrations(store: ProjectStore) -> tuple[_MigrationPlan, ...]:
    plans: list[_MigrationPlan] = []
    try:
        children = sorted(store.root.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        raise ProjectMaintenanceError("canonical Project Store could not be enumerated") from exc

    for child in children:
        if child.is_symlink():
            raise ProjectMaintenanceError("canonical Project Store must not contain symlinks")
        project_file = child / PROJECT_FILENAME
        if not child.is_dir() or not project_file.is_file():
            continue
        if project_file.is_symlink():
            raise ProjectMaintenanceError(f"project metadata must not be a symlink: {child.name}")
        try:
            validate_identifier(child.name, field_name="project_id")
            canonical_path = store.project_path(child.name)
        except ProjectValidationError as exc:
            raise ProjectMaintenanceError(
                f"invalid project directory in canonical Store: {child.name!r}"
            ) from exc
        try:
            resolved_project_file = project_file.resolve(strict=True)
        except OSError as exc:
            raise ProjectMaintenanceError(f"project metadata cannot be resolved: {child.name}") from exc
        if canonical_path != resolved_project_file:
            raise ProjectMaintenanceError(f"project metadata escaped canonical Store: {child.name!r}")

        original_bytes, original_data = _read_raw_project(canonical_path)
        source_schema = original_data.get("schema_version")
        if not isinstance(source_schema, int) or isinstance(source_schema, bool):
            raise ProjectMaintenanceError(f"project has invalid schema_version: {child.name}")
        try:
            migrated = migrate_project_data(original_data)
            document = ProjectDocument.from_dict(migrated)
        except Exception as exc:
            raise ProjectMaintenanceError(
                f"project cannot be prepared for schema v{PROJECT_SCHEMA_VERSION}: {child.name}"
            ) from exc
        if document.project_id != child.name:
            raise ProjectMaintenanceError(
                f"project identity mismatch during migration preflight: {child.name!r}"
            )
        if document.schema_version != PROJECT_SCHEMA_VERSION:
            raise ProjectMaintenanceError(
                f"migration preflight did not reach schema v{PROJECT_SCHEMA_VERSION}: {child.name}"
            )
        if migrated != original_data:
            plans.append(
                _MigrationPlan(
                    project_id=child.name,
                    project_path=canonical_path,
                    original_bytes=original_bytes,
                    original_schema_version=source_schema,
                    migrated_data=migrated,
                )
            )
    return tuple(plans)


def _snapshot_relative_path(project_id: str) -> str:
    return f"projects/{project_id}/{PROJECT_FILENAME}"


def verify_migration_recovery_snapshot(path: Path | str) -> dict[str, Any]:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise ProjectMaintenanceError("migration recovery snapshot must not be a symlink")
    try:
        root = candidate.resolve(strict=True)
    except OSError as exc:
        raise ProjectMaintenanceError("migration recovery snapshot does not exist") from exc
    if not root.is_dir():
        raise ProjectMaintenanceError("migration recovery snapshot must be a directory")

    manifest_path = root / MIGRATION_RECOVERY_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectMaintenanceError("migration recovery manifest is not readable valid JSON") from exc
    expected_keys = {
        "recovery_schema_version",
        "set_id",
        "created_at",
        "reason",
        "target_project_schema_version",
        "projects",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected_keys:
        raise ProjectMaintenanceError("migration recovery manifest has unexpected fields")
    if manifest["recovery_schema_version"] != MIGRATION_RECOVERY_SCHEMA_VERSION:
        raise ProjectMaintenanceError("unsupported migration recovery schema version")
    set_id = manifest["set_id"]
    if not isinstance(set_id, str) or not _SAFE_SET_ID.fullmatch(set_id):
        raise ProjectMaintenanceError("migration recovery set_id is invalid")
    allowed_directory_names = {set_id, f".{set_id}.staging"}
    if root.name not in allowed_directory_names:
        raise ProjectMaintenanceError("migration recovery set_id does not match its directory")
    for field in ("created_at", "reason"):
        value = manifest[field]
        if not isinstance(value, str) or not value.strip() or value != value.strip() or "\n" in value or "\r" in value:
            raise ProjectMaintenanceError(f"migration recovery {field} is invalid")
    target_schema = manifest["target_project_schema_version"]
    if not isinstance(target_schema, int) or isinstance(target_schema, bool) or target_schema < 1:
        raise ProjectMaintenanceError("migration recovery target schema is invalid")
    records = manifest["projects"]
    if not isinstance(records, list) or not records:
        raise ProjectMaintenanceError("migration recovery snapshot must contain project metadata")

    expected_files = {MIGRATION_RECOVERY_MANIFEST}
    seen_projects: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "project_id",
            "path",
            "size",
            "sha256",
            "source_schema_version",
        }:
            raise ProjectMaintenanceError("invalid migration recovery project record")
        project_id = record["project_id"]
        relative = record["path"]
        size = record["size"]
        sha256 = record["sha256"]
        source_schema = record["source_schema_version"]
        if not isinstance(project_id, str):
            raise ProjectMaintenanceError("invalid migration recovery project id")
        try:
            validate_identifier(project_id, field_name="project_id")
        except ProjectValidationError as exc:
            raise ProjectMaintenanceError("invalid migration recovery project id") from exc
        if project_id in seen_projects:
            raise ProjectMaintenanceError("duplicate project in migration recovery snapshot")
        seen_projects.add(project_id)
        if not isinstance(relative, str) or relative != _snapshot_relative_path(project_id):
            raise ProjectMaintenanceError("migration recovery path is not canonical")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ProjectMaintenanceError("invalid migration recovery file size")
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or sha256 != sha256.lower()
            or any(character not in "0123456789abcdef" for character in sha256)
        ):
            raise ProjectMaintenanceError("invalid migration recovery SHA-256")
        if not isinstance(source_schema, int) or isinstance(source_schema, bool) or source_schema < 1:
            raise ProjectMaintenanceError("invalid migration recovery source schema")
        file_path = root.joinpath(*PurePosixPath(relative).parts)
        if file_path.is_symlink() or not file_path.is_file():
            raise ProjectMaintenanceError(f"migration recovery file is missing: {relative}")
        if file_path.stat().st_size != size:
            raise ProjectMaintenanceError(f"migration recovery size mismatch: {relative}")
        if _sha256_file(file_path) != sha256:
            raise ProjectMaintenanceError(f"migration recovery SHA-256 mismatch: {relative}")
        expected_files.add(relative)

    actual_files: set[str] = set()
    for entry in root.rglob("*"):
        if entry.is_symlink():
            raise ProjectMaintenanceError("migration recovery snapshot contains a symlink")
        if entry.is_file():
            actual_files.add(entry.relative_to(root).as_posix())
        elif not entry.is_dir():
            raise ProjectMaintenanceError("migration recovery snapshot contains a special entry")
    if actual_files != expected_files:
        raise ProjectMaintenanceError("migration recovery inventory does not match its manifest")
    return manifest


def create_migration_recovery_snapshot(
    store: ProjectStore,
    plans: tuple[_MigrationPlan, ...],
    recovery_root: Path | str,
) -> Path:
    if not plans:
        raise ProjectMaintenanceError("cannot create an empty migration recovery snapshot")
    root = _validated_recovery_root(store, recovery_root)
    set_id = f"schema-v{PROJECT_SCHEMA_VERSION}-{uuid.uuid4().hex}"
    staging = root / f".{set_id}.staging"
    final = root / set_id
    if staging.exists() or final.exists():
        raise ProjectMaintenanceError("migration recovery destination already exists")
    staging.mkdir()
    try:
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for plan in sorted(plans, key=lambda item: item.project_id):
            if plan.project_id in seen:
                raise ProjectMaintenanceError("duplicate project in migration recovery plan")
            seen.add(plan.project_id)
            relative = _snapshot_relative_path(plan.project_id)
            destination = staging.joinpath(*PurePosixPath(relative).parts)
            _atomic_write_bytes(destination, plan.original_bytes)
            records.append(
                {
                    "project_id": plan.project_id,
                    "path": relative,
                    "size": len(plan.original_bytes),
                    "sha256": _sha256_bytes(plan.original_bytes),
                    "source_schema_version": plan.original_schema_version,
                }
            )
        manifest = {
            "recovery_schema_version": MIGRATION_RECOVERY_SCHEMA_VERSION,
            "set_id": set_id,
            "created_at": utc_now_iso(),
            "reason": f"project-schema-migration-to-v{PROJECT_SCHEMA_VERSION}",
            "target_project_schema_version": PROJECT_SCHEMA_VERSION,
            "projects": records,
        }
        _atomic_write_bytes(staging / MIGRATION_RECOVERY_MANIFEST, _canonical_json_bytes(manifest))
        verify_migration_recovery_snapshot(staging)
        os.replace(staging, final)
        verify_migration_recovery_snapshot(final)
        return final
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def prepare_project_store_for_current_schema(
    store: ProjectStore,
    recovery_root: Path | str,
) -> ProjectStorePreparation:
    """Preflight, snapshot, migrate and roll back Project Store metadata fail-closed.

    No snapshot is created when every canonical project is already on the current
    schema. When migration changes are required, exact original project.json
    bytes for every changed project are published before the first canonical
    write. Media/assets are not duplicated because schema migration never mutates
    them; full user-requested project backup/restore continues to use .uvproj.zip.
    """

    with store._lock:
        plans = _plan_project_store_migrations(store)
        if not plans:
            return ProjectStorePreparation(PROJECT_SCHEMA_VERSION, (), None)

        recovery_snapshot = create_migration_recovery_snapshot(store, plans, recovery_root)
        attempted: list[_MigrationPlan] = []
        try:
            for plan in plans:
                attempted.append(plan)
                _atomic_write_bytes(plan.project_path, _canonical_json_bytes(plan.migrated_data))
            for plan in plans:
                document = store.load_project(plan.project_id)
                if document.schema_version != PROJECT_SCHEMA_VERSION:
                    raise ProjectMaintenanceError(
                        f"post-migration validation failed for {plan.project_id}"
                    )
        except Exception as exc:
            rollback_failures: list[str] = []
            for plan in reversed(attempted):
                try:
                    _atomic_write_bytes(plan.project_path, plan.original_bytes)
                except Exception:
                    rollback_failures.append(plan.project_id)
            if rollback_failures:
                raise ProjectMaintenanceError(
                    "Project Store migration failed and automatic metadata rollback was incomplete; "
                    f"recovery snapshot is {recovery_snapshot}; affected={','.join(sorted(rollback_failures))}"
                ) from exc
            raise ProjectMaintenanceError(
                "Project Store migration failed; original metadata was restored and "
                f"recovery snapshot is {recovery_snapshot}"
            ) from exc

        return ProjectStorePreparation(
            PROJECT_SCHEMA_VERSION,
            tuple(plan.project_id for plan in plans),
            recovery_snapshot,
        )
