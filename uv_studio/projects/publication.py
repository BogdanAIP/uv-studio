"""Durable markers for consequence-bearing managed-output publication.

A project OS lock serializes live publishers and archive snapshots, but the lock is
released automatically when a process dies. A tiny durable marker written inside
that same lock immediately before canonical ``os.replace`` bridges the crash gap:
normal completion removes the marker before unlocking, while startup/archive can
identify an interrupted arbitrary-path publication after a crash.

The marker is recovery/coordination state only. ProjectReference metadata remains
the canonical media authority and user Undo/Redo history remains owned by
ProjectUnitOfWork.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .models import utc_now_iso, validate_identifier, validate_project_relative_path
from .store import ProjectStore, ProjectStoreError
from .task_records import ProjectTaskRecordStore

PUBLICATION_RECORD_TYPE = "managed_publication"
PUBLICATION_SCHEMA_VERSION = 1
PUBLICATION_RECORD_PREFIX = "pub_"
_PUBLICATION_ROOTS = frozenset({"artifacts", "exports"})


class ManagedPublicationError(ProjectStoreError):
    """A durable managed-output publication marker is invalid or unrecoverable."""


def _canonical_output_path(value: str) -> str:
    try:
        canonical = validate_project_relative_path(value)
    except Exception as exc:
        raise ManagedPublicationError(f"invalid managed publication path: {value!r}") from exc
    parts = PurePosixPath(canonical).parts
    if not parts or parts[0] not in _PUBLICATION_ROOTS:
        raise ManagedPublicationError(
            f"managed publication path must be under {sorted(_PUBLICATION_ROOTS)!r}"
        )
    return canonical


def _record(
    *,
    publication_id: str,
    project_id: str,
    relative_path: str,
    purpose: str,
    reference_id: str | None,
) -> dict[str, Any]:
    if not isinstance(purpose, str) or not purpose.strip() or len(purpose.strip()) > 200:
        raise ManagedPublicationError("publication purpose must be 1..200 characters")
    if reference_id is not None:
        reference_id = validate_identifier(reference_id, field_name="publication reference_id")
    return {
        "record_type": PUBLICATION_RECORD_TYPE,
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "publication_id": validate_identifier(publication_id, field_name="publication_id"),
        "project_id": validate_identifier(project_id, field_name="project_id"),
        "relative_path": _canonical_output_path(relative_path),
        "purpose": purpose.strip(),
        "reference_id": reference_id,
        "created_at": utc_now_iso(),
    }


def begin_managed_publication(
    store: ProjectStore,
    project_id: str,
    *,
    relative_path: str,
    purpose: str,
    reference_id: str | None = None,
) -> str:
    """Persist one prepared publication marker and reserve its canonical path.

    A canonical output path may have at most one unresolved publication marker.
    Reservation validation and marker creation are serialized under the same shared
    cross-runtime project lock so a process that crashes after marker creation but
    before ``os.replace`` cannot be bypassed by another publisher reusing the still
    absent path. Callers may already hold the project lock; it is re-entrant.
    """

    publication_id = f"{PUBLICATION_RECORD_PREFIX}{uuid.uuid4().hex}"
    record = _record(
        publication_id=publication_id,
        project_id=project_id,
        relative_path=relative_path,
        purpose=purpose,
        reference_id=reference_id,
    )
    canonical_path = record["relative_path"]
    records = ProjectTaskRecordStore(store)
    with records.project_lock(project_id):
        for pending in pending_managed_publications(store, project_id):
            if pending["relative_path"] == canonical_path:
                raise ManagedPublicationError(
                    f"managed publication path already reserved: {canonical_path!r}"
                )
        records.create_if_absent(project_id, publication_id, record)
    return publication_id


def _load_marker(records: ProjectTaskRecordStore, project_id: str, path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ManagedPublicationError(f"publication marker is missing or unsafe: {path.name!r}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManagedPublicationError(f"publication marker is unreadable: {path.name!r}") from exc
    if not isinstance(raw, Mapping):
        raise ManagedPublicationError(f"publication marker must be an object: {path.name!r}")
    if raw.get("record_type") != PUBLICATION_RECORD_TYPE:
        raise ManagedPublicationError(f"unexpected publication record type: {path.name!r}")
    if raw.get("schema_version") != PUBLICATION_SCHEMA_VERSION:
        raise ManagedPublicationError(f"unsupported publication marker schema: {path.name!r}")
    if raw.get("project_id") != project_id or raw.get("publication_id") != path.stem:
        raise ManagedPublicationError(f"publication marker identity mismatch: {path.name!r}")
    relative_path = raw.get("relative_path")
    if not isinstance(relative_path, str):
        raise ManagedPublicationError(f"publication marker has no relative path: {path.name!r}")
    _canonical_output_path(relative_path)
    reference_id = raw.get("reference_id")
    if reference_id is not None:
        validate_identifier(reference_id, field_name="publication reference_id")
    purpose = raw.get("purpose")
    created_at = raw.get("created_at")
    if not isinstance(purpose, str) or not purpose.strip():
        raise ManagedPublicationError(f"publication marker has no purpose: {path.name!r}")
    if not isinstance(created_at, str) or not created_at:
        raise ManagedPublicationError(f"publication marker has no created_at: {path.name!r}")
    return dict(raw)


def pending_managed_publications(
    store: ProjectStore,
    project_id: str,
) -> tuple[dict[str, Any], ...]:
    """Return validated prepared markers. Caller should hold the shared project lock."""

    records = ProjectTaskRecordStore(store)
    tasks = store.project_directory(project_id) / "tasks"
    if tasks.is_symlink() or not tasks.is_dir():
        raise ManagedPublicationError("project tasks root is missing or unsafe")
    result: list[dict[str, Any]] = []
    for path in sorted(tasks.glob(f"{PUBLICATION_RECORD_PREFIX}*.json"), key=lambda item: item.name):
        result.append(_load_marker(records, project_id, path))
    return tuple(result)


def finish_managed_publication(
    store: ProjectStore,
    project_id: str,
    publication_id: str,
) -> None:
    """Remove one durable marker after completion or proven rollback."""

    publication_id = validate_identifier(publication_id, field_name="publication_id")
    records = ProjectTaskRecordStore(store)
    with records.project_lock(project_id):
        path = records.path(project_id, publication_id)
        _load_marker(records, project_id, path)
        try:
            path.unlink()
        except OSError as exc:
            raise ManagedPublicationError(
                f"could not remove completed publication marker: {publication_id!r}"
            ) from exc


def recover_managed_publications(
    store: ProjectStore,
    project_id: str,
) -> tuple[Path, ...]:
    """Reconcile crash-left arbitrary-path publication markers without data loss.

    A publication is already canonical only when its registered ProjectReference
    matches the marker's path and, when present, the marker's expected reference
    identity. A path owned by a different reference must not claim crash-left bytes.
    Unregistered/interrupted bytes are moved outside the project tree rather than
    deleted. A marker with no materialized path is simply cleared. No provider or
    renderer is replayed.
    """

    records = ProjectTaskRecordStore(store)
    quarantined: list[Path] = []
    with records.project_lock(project_id):
        project = store.load_project(project_id)
        registered_by_path: dict[str, set[str]] = {}
        for item in (*project.sources, *project.artifacts):
            registered_by_path.setdefault(item.path, set()).add(item.id)

        for marker in pending_managed_publications(store, project_id):
            publication_id = marker["publication_id"]
            relative_path = marker["relative_path"]
            expected_reference_id = marker.get("reference_id")
            registered_ids = registered_by_path.get(relative_path, set())
            publication_registered = bool(registered_ids) and (
                expected_reference_id is None or expected_reference_id in registered_ids
            )
            root = PurePosixPath(relative_path).parts[0]
            output = store.resolve_project_file(
                project_id,
                relative_path,
                allowed_roots=(root,),
            )
            if not publication_registered and (output.exists() or output.is_symlink()):
                if output.is_symlink() or not output.is_file():
                    raise ManagedPublicationError(
                        f"interrupted publication path is not a regular file: {relative_path!r}"
                    )
                destination = store.root / (
                    f".uv-recovered-publication-{project_id}-{publication_id}-{output.name}"
                )
                if destination.exists() or destination.is_symlink():
                    raise ManagedPublicationError(
                        f"publication quarantine path unexpectedly exists: {destination.name!r}"
                    )
                try:
                    os.replace(output, destination)
                except OSError as exc:
                    raise ManagedPublicationError(
                        f"could not quarantine interrupted publication: {relative_path!r}"
                    ) from exc
                quarantined.append(destination)
            finish_managed_publication(store, project_id, publication_id)
    return tuple(quarantined)
