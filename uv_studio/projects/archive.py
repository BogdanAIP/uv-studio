"""Portable, validated UV Studio project archives.

Archive imports are staged and fully validated before a project directory is
committed into the canonical Project Store. The format is intentionally owned by
UV Studio rather than by the pinned VideoClaw runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from uv_studio.production.semantics import (
    PRODUCTION_SEMANTICS_PATH,
    ProductionSemanticError,
    ProductionSemanticsDocument,
)

from .migrations import migrate_project_data
from .models import (
    PROJECT_SCHEMA_VERSION,
    ProjectDocument,
    ProjectValidationError,
    utc_now_iso,
    validate_identifier,
)
from .publication import ManagedPublicationError, pending_managed_publications
from .store import PROJECT_DIRECTORIES, PROJECT_FILENAME, ProjectAlreadyExists, ProjectStore
from .task_records import ProjectTaskRecordStore
from .transactions import ProjectTransactionError, ProjectUnitOfWork, _snapshot_content

ARCHIVE_SCHEMA_VERSION = 1
ARCHIVE_MANIFEST = ".uv-project-archive.json"
PROJECT_PREFIX = "project"
_MANAGED_MEDIA_ROOTS = frozenset({"sources", "assets", "artifacts", "exports"})
_MANAGED_PUBLICATION_NAME = re.compile(
    r"^(?:(?:src|art|aud|sub)_[0-9a-f]{32}|generated_attempt_[0-9a-f]{32})(?:[._-]|$)"
)


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


def _raw_project_schema_version(path: Path) -> int:
    """Return the schema declared by the exact project.json bytes at ``path``."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectArchiveError(f"Cannot read archived project schema: {path}") from exc
    if not isinstance(data, dict):
        raise ProjectArchiveError("Archived project.json must be a JSON object")
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProjectArchiveError("Archived project.json has invalid schema_version")
    return version


def _safe_archive_output(project_dir: Path, archive_path: Path) -> Path:
    resolved = archive_path.expanduser().resolve()
    if resolved == project_dir or project_dir in resolved.parents:
        raise ProjectArchiveError("Archive output cannot be inside the project being archived")
    return resolved


def _is_archive_transient(project_dir: Path, path: Path) -> bool:
    return path == project_dir / "tasks" / ProjectTaskRecordStore.LOCK_FILE_NAME


def _iter_project_entries(project_dir: Path) -> tuple[list[Path], list[Path]]:
    directories: list[Path] = []
    files: list[Path] = []
    for path in sorted(project_dir.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ProjectArchiveError(f"Project archive does not allow symlinks: {path}")
        if _is_archive_transient(project_dir, path):
            continue
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


def _registered_media_paths(document: ProjectDocument) -> set[str]:
    return {reference.path for reference in (*document.sources, *document.artifacts)}


def _snapshot_project(snapshot: Any) -> ProjectDocument | None:
    """Read one historical project.json snapshot through the current schema boundary."""

    try:
        content = _snapshot_content(snapshot)
        if content is None:
            return None
        raw = json.loads(content.decode("utf-8"))
        return ProjectDocument.from_dict(migrate_project_data(raw))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ProjectTransactionError,
        ProjectValidationError,
    ) as exc:
        raise ProjectArchiveError("Project redo history contains invalid Project snapshot") from exc


def _redoable_media_paths(store: ProjectStore, project_id: str) -> set[str]:
    """Return media paths owned by the current durable UOW redo suffix.

    ProjectUnitOfWork snapshots canonical JSON, not binary media. After a reference
    transaction is undone, its already-published bytes intentionally remain in the
    project so Redo can restore the exact reference. Archives must preserve those
    bytes while the transaction is still reachable through
    ``history.entries[history.cursor:]``. A later canonical commit truncates that
    suffix and removes this authority automatically.
    """

    uow = ProjectUnitOfWork(store)
    try:
        history = uow.history(project_id)
    except ProjectTransactionError as exc:
        raise ProjectArchiveError("Project redo history is invalid") from exc

    protected: set[str] = set()
    for entry in history.entries[history.cursor :]:
        try:
            record = uow._load_record(
                uow._record_path(project_id, entry.transaction_id, transaction=True)
            )
        except ProjectTransactionError as exc:
            raise ProjectArchiveError("Project redo transaction history is invalid") from exc
        if (
            record.get("phase") != "committed"
            or record.get("operation") != "commit"
            or record.get("transaction_id") != entry.transaction_id
        ):
            raise ProjectArchiveError("Project redo transaction disagrees with history index")
        changes = record.get("changes")
        if not isinstance(changes, list) or not changes:
            raise ProjectArchiveError("Project redo transaction has invalid changes")
        for change in changes:
            try:
                relative, _before, after = uow._validated_change(change)
            except ProjectTransactionError as exc:
                raise ProjectArchiveError("Project redo transaction change is invalid") from exc
            if relative != PROJECT_FILENAME:
                continue
            project = _snapshot_project(after)
            if project is None:
                raise ProjectArchiveError("Project redo transaction cannot remove project.json")
            protected.update(_registered_media_paths(project))
    return protected


def _looks_like_managed_publication(project_dir: Path, path: Path) -> bool:
    relative = path.relative_to(project_dir)
    if len(relative.parts) < 2 or relative.parts[0] not in _MANAGED_MEDIA_ROOTS:
        return False
    name = relative.name[1:] if relative.name.startswith(".") else relative.name
    return _MANAGED_PUBLICATION_NAME.match(name) is not None


def _reject_interrupted_publications(store: ProjectStore, project_id: str) -> None:
    """Fail closed on a crash-left arbitrary-path publication marker."""

    try:
        pending = pending_managed_publications(store, project_id)
    except ManagedPublicationError as exc:
        raise ProjectArchiveError(f"Managed publication recovery state is invalid: {exc}") from exc
    if pending:
        paths = sorted(str(item["relative_path"]) for item in pending)
        raise ProjectArchiveError(
            "Project has interrupted managed publication state; restart UV Studio "
            f"to reconcile before export: {paths!r}"
        )


def _reject_unpublished_managed_media(
    store: ProjectStore,
    project_id: str,
    document: ProjectDocument,
    project_dir: Path,
    files: list[Path],
) -> None:
    """Fail closed when a self-identifying UV publication lacks durable ownership.

    Historical source/artifact/audio names plus current WebVTT ``sub_<uuid>`` and
    Generation ``generated_attempt_<uuid>`` names are unambiguous UV-owned
    publications. Ordinary unregistered files remain portable. A path is also
    durably owned while its ProjectReference is reachable through the current UOW
    Redo suffix, because the binary bytes are required to make that Redo exact.
    Arbitrary-path ``timeline.assemble`` is covered by its durable publication marker
    instead of a filename guess.
    """

    owned = _registered_media_paths(document) | _redoable_media_paths(store, project_id)
    for path in files:
        relative = path.relative_to(project_dir).as_posix()
        if _looks_like_managed_publication(project_dir, path) and relative not in owned:
            raise ProjectArchiveError(
                "Project contains an unpublished managed media file; restart UV Studio "
                f"to reconcile publication before export: {relative}"
            )


def _load_production_semantics(project_dir: Path) -> ProductionSemanticsDocument:
    path = project_dir.joinpath(*PurePosixPath(PRODUCTION_SEMANTICS_PATH).parts)
    if path.is_symlink() or not path.is_file():
        raise ProjectArchiveError("Generation archive authority requires safe Production Semantics")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return ProductionSemanticsDocument.from_dict(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ProductionSemanticError) as exc:
        raise ProjectArchiveError("Production Semantics is invalid for Generation archive authority") from exc


def _snapshot_production(snapshot: Any) -> ProductionSemanticsDocument | None:
    try:
        content = _snapshot_content(snapshot)
        if content is None:
            return None
        raw = json.loads(content.decode("utf-8"))
        return ProductionSemanticsDocument.from_dict(raw)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ProductionSemanticError,
        ProjectTransactionError,
    ) as exc:
        raise ProjectArchiveError("Generation Take history contains invalid Production snapshot") from exc


def _matching_take(document: ProductionSemanticsDocument | None, take_id: str):
    if document is None:
        return None
    for take in document.takes:
        if take.take_id == take_id:
            return take
    return None


def _history_proves_undone_generation_take(
    store: ProjectStore,
    project_id: str,
    *,
    take_id: str,
    shot_id: str,
    reference_id: str,
) -> bool:
    """Prove that a missing Generation Take was removed by explicit durable Undo.

    Generation Job records are intentionally outside user Undo/Redo history. A
    succeeded attempt therefore retains immutable historical ``take_id`` provenance
    even when the Production Take is later undone. Archive may accept that absence
    only when the existing UOW transaction/operation journals prove the exact Take
    was created and the last committed operation for that transaction is ``undo``.
    Out-of-band deletion or a later redo remains fail-closed.
    """

    uow = ProjectUnitOfWork(store)
    try:
        uow.history(project_id)
    except ProjectTransactionError as exc:
        raise ProjectArchiveError("Generation Take history is invalid") from exc

    project_dir = store.project_directory(project_id)
    transactions_dir = project_dir / "history" / "transactions"
    operations_dir = project_dir / "history" / "operations"
    if transactions_dir.is_symlink() or not transactions_dir.is_dir():
        raise ProjectArchiveError("Generation Take transaction history is unsafe")
    if operations_dir.is_symlink() or not operations_dir.is_dir():
        raise ProjectArchiveError("Generation Take operation history is unsafe")

    creation_ids: list[str] = []
    for path in sorted(transactions_dir.glob("*.json"), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file():
            raise ProjectArchiveError("Generation Take transaction history is unsafe")
        try:
            record = uow._load_record(path)
        except ProjectTransactionError as exc:
            raise ProjectArchiveError("Generation Take transaction history is invalid") from exc
        if (
            record.get("phase") != "committed"
            or record.get("operation") != "commit"
            or record.get("command") != "production.register_take"
        ):
            continue
        changes = record.get("changes")
        if not isinstance(changes, list):
            raise ProjectArchiveError("Generation Take transaction has invalid changes")
        for change in changes:
            try:
                relative, before, after = uow._validated_change(change)
            except ProjectTransactionError as exc:
                raise ProjectArchiveError("Generation Take transaction change is invalid") from exc
            if relative != PRODUCTION_SEMANTICS_PATH:
                continue
            before_doc = _snapshot_production(before)
            after_doc = _snapshot_production(after)
            before_take = _matching_take(before_doc, take_id)
            after_take = _matching_take(after_doc, take_id)
            if after_take is None:
                continue
            if before_take is not None:
                continue
            if after_take.shot_id == shot_id and after_take.reference_id == reference_id:
                transaction_id = record.get("transaction_id")
                if not isinstance(transaction_id, str) or not transaction_id:
                    raise ProjectArchiveError("Generation Take transaction lost identity")
                creation_ids.append(transaction_id)

    creation_ids = sorted(set(creation_ids))
    if not creation_ids:
        return False
    if len(creation_ids) != 1:
        raise ProjectArchiveError("Generation Take history is ambiguous")
    transaction_id = creation_ids[0]

    operations: list[tuple[str, str, str]] = []
    for path in sorted(operations_dir.glob("*.json"), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file():
            raise ProjectArchiveError("Generation Take operation history is unsafe")
        try:
            record = uow._load_record(path)
        except ProjectTransactionError as exc:
            raise ProjectArchiveError("Generation Take operation history is invalid") from exc
        if record.get("phase") != "committed" or record.get("transaction_id") != transaction_id:
            continue
        operation = record.get("operation")
        created_at = record.get("created_at")
        record_id = record.get("record_id")
        if operation not in {"undo", "redo"}:
            continue
        if not isinstance(created_at, str) or not created_at:
            raise ProjectArchiveError("Generation Take operation lost created_at")
        if not isinstance(record_id, str) or not record_id:
            raise ProjectArchiveError("Generation Take operation lost identity")
        operations.append((created_at, record_id, operation))

    if not operations:
        return False
    operations.sort()
    if len(operations) >= 2 and operations[-1][0] == operations[-2][0]:
        raise ProjectArchiveError("Generation Take operation ordering is ambiguous")
    return operations[-1][2] == "undo"


def _generation_digest_authority(
    store: ProjectStore,
    project_id: str,
    document: ProjectDocument,
    project_dir: Path,
) -> dict[str, tuple[int, str]]:
    """Validate Generation authority and return expected digest for exact ZIP capture."""

    expected_digests: dict[str, tuple[int, str]] = {}
    production: ProductionSemanticsDocument | None = None
    for artifact in document.artifacts:
        generation = artifact.metadata.get("generation")
        if not isinstance(generation, dict):
            continue
        job_id = generation.get("job_id")
        attempt_id = generation.get("attempt_id")
        if not isinstance(job_id, str) or not isinstance(attempt_id, str):
            raise ProjectArchiveError(
                f"Generation artifact has incomplete durable provenance: {artifact.id}"
            )
        job_path = project_dir / "tasks" / f"{job_id}.json"
        if job_path.is_symlink() or not job_path.is_file():
            raise ProjectArchiveError(
                f"Generation artifact has no safe durable Job record: {artifact.id}"
            )
        try:
            raw = json.loads(job_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProjectArchiveError(
                f"Generation Job record is unreadable for artifact: {artifact.id}"
            ) from exc
        if not isinstance(raw, dict) or raw.get("record_type") != "generation_job":
            raise ProjectArchiveError(
                f"Generation artifact points to a non-generation task record: {artifact.id}"
            )
        attempts = raw.get("attempts")
        if not isinstance(attempts, list):
            raise ProjectArchiveError(
                f"Generation Job has invalid attempt history for artifact: {artifact.id}"
            )
        matching_attempts = [
            attempt
            for attempt in attempts
            if isinstance(attempt, dict) and attempt.get("attempt_id") == attempt_id
        ]
        if len(matching_attempts) != 1:
            raise ProjectArchiveError(
                f"Generation artifact does not resolve to one durable attempt: {artifact.id}"
            )
        attempt = matching_attempts[0]
        take_id = attempt.get("take_id")
        if (
            attempt.get("status") != "succeeded"
            or attempt.get("output_reference_id") != artifact.id
            or not isinstance(take_id, str)
            or not take_id
        ):
            raise ProjectArchiveError(
                "Generation materialization is not durably complete; restart UV Studio "
                f"to reconcile before export: {artifact.id}"
            )

        request = raw.get("request")
        mapping = request.get("execution_mapping") if isinstance(request, dict) else None
        contract = request.get("generation_contract") if isinstance(request, dict) else None
        shot_id = request.get("shot_id") if isinstance(request, dict) else None
        if not isinstance(shot_id, str) or not shot_id:
            raise ProjectArchiveError(
                f"Generation Job lost shot authority for artifact: {artifact.id}"
            )
        authority = {
            "job_id": raw.get("job_id"),
            "attempt_id": attempt_id,
            "model_id": request.get("model_id") if isinstance(request, dict) else None,
            "capability_id": mapping.get("capability_id") if isinstance(mapping, dict) else None,
            "offer_id": mapping.get("offer_id") if isinstance(mapping, dict) else None,
            "adapter_id": mapping.get("adapter_id") if isinstance(mapping, dict) else None,
            "request_digest": raw.get("request_digest"),
        }
        for field_name, expected_value in authority.items():
            if not isinstance(expected_value, str) or not expected_value:
                raise ProjectArchiveError(
                    f"Generation Job lost {field_name} authority for artifact: {artifact.id}"
                )
            if generation.get(field_name) != expected_value:
                raise ProjectArchiveError(
                    f"Generation artifact {field_name} disagrees with durable Job: {artifact.id}"
                )
        if not isinstance(contract, dict) or generation.get("contract") != contract:
            raise ProjectArchiveError(
                f"Generation artifact contract disagrees with durable Job: {artifact.id}"
            )

        if production is None:
            production = _load_production_semantics(project_dir)
        take = _matching_take(production, take_id)
        if take is not None:
            if take.shot_id != shot_id or take.reference_id != artifact.id:
                raise ProjectArchiveError(
                    f"Generation Take disagrees with current Production authority: {artifact.id}"
                )
        elif not _history_proves_undone_generation_take(
            store,
            project_id,
            take_id=take_id,
            shot_id=shot_id,
            reference_id=artifact.id,
        ):
            raise ProjectArchiveError(
                f"Generation Take is missing without durable Undo authority: {artifact.id}"
            )

        expected_name = f"generated_{attempt_id}"
        artifact_name = PurePosixPath(artifact.path).name
        if not (artifact_name == expected_name or artifact_name.startswith(expected_name + ".")):
            raise ProjectArchiveError(
                f"Generation artifact path disagrees with durable attempt: {artifact.id}"
            )
        size_bytes = artifact.metadata.get("size_bytes")
        sha256 = artifact.metadata.get("sha256")
        if (
            isinstance(size_bytes, bool)
            or not isinstance(size_bytes, int)
            or size_bytes <= 0
            or not isinstance(sha256, str)
            or len(sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in sha256)
        ):
            raise ProjectArchiveError(
                f"Generation artifact has invalid size/digest authority: {artifact.id}"
            )
        if artifact.path in expected_digests:
            raise ProjectArchiveError(
                f"Multiple Generation artifacts claim one output path: {artifact.path}"
            )
        expected_digests[artifact.path] = (size_bytes, sha256)
    return expected_digests


def _write_zip_file_and_record(
    archive: zipfile.ZipFile,
    project_dir: Path,
    path: Path,
    *,
    chunk_size: int = 1024 * 1024,
) -> dict[str, Any]:
    """Write one live file once and describe the exact bytes written to the ZIP."""

    if path.is_symlink() or not path.is_file():
        raise ProjectArchiveError(f"Project file changed type during export: {path}")
    name = _archive_relative_name(project_dir, path)
    info = zipfile.ZipInfo.from_file(path, arcname=name)
    info.compress_type = archive.compression
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as output:
            while chunk := source.read(chunk_size):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ProjectArchiveError(f"Could not capture project file during export: {path}") from exc
    return {"path": name, "size": size, "sha256": digest.hexdigest()}


def export_project(
    store: ProjectStore,
    project_id: str,
    archive_path: Path | str,
) -> Path:
    """Export one stable canonical project snapshot to a validated ZIP format."""
    project_dir = store.project_path(project_id).parent
    lexical_lock_path = project_dir / "tasks" / ProjectTaskRecordStore.LOCK_FILE_NAME
    if lexical_lock_path.is_symlink():
        raise ProjectArchiveError(f"Project archive does not allow symlinks: {lexical_lock_path}")

    task_records = ProjectTaskRecordStore(store)
    with task_records.project_lock(project_id):
        document = store.load_project(project_id)
        project_path = store.project_path(project_id)
        project_dir = project_path.parent
        stored_schema_version = _raw_project_schema_version(project_path)
        destination = _safe_archive_output(project_dir, Path(archive_path))
        destination.parent.mkdir(parents=True, exist_ok=True)

        directories, files = _iter_project_entries(project_dir)
        _reject_interrupted_publications(store, project_id)
        _reject_unpublished_managed_media(store, project_id, document, project_dir, files)
        generation_digests = _generation_digest_authority(
            store,
            project_id,
            document,
            project_dir,
        )
        created_at = utc_now_iso()

        temp_path = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(
                temp_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            ) as archive:
                _write_zip_directory(archive, PROJECT_PREFIX)
                for directory in directories:
                    _write_zip_directory(archive, _archive_relative_name(project_dir, directory))
                file_records: list[dict[str, Any]] = []
                for path in files:
                    record = _write_zip_file_and_record(archive, project_dir, path)
                    relative = path.relative_to(project_dir).as_posix()
                    expected = generation_digests.get(relative)
                    if expected is not None and (
                        record["size"] != expected[0] or record["sha256"] != expected[1]
                    ):
                        raise ProjectArchiveError(
                            "Generation output bytes do not match persisted size/digest: "
                            f"{relative}"
                        )
                    file_records.append(record)
                manifest = {
                    "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
                    "project_id": document.project_id,
                    "project_schema_version": stored_schema_version,
                    "created_at": created_at,
                    "files": file_records,
                }
                archive.writestr(
                    ARCHIVE_MANIFEST,
                    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                )
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

        if (
            name != ARCHIVE_MANIFEST
            and name != PROJECT_PREFIX
            and not name.startswith(f"{PROJECT_PREFIX}/")
        ):
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
    staging_root = staging_project.resolve()

    # Create declared project directories first, including empty ones.
    for name, info in sorted(members.items()):
        if not info.is_dir() or name == PROJECT_PREFIX:
            continue
        if not name.startswith(f"{PROJECT_PREFIX}/"):
            continue
        relative = PurePosixPath(name).relative_to(PROJECT_PREFIX)
        target = staging_project.joinpath(*relative.parts).resolve()
        if staging_root not in target.parents and target != staging_root:
            raise ProjectArchiveError(f"Archive directory escaped staging: {name}")
        target.mkdir(parents=True, exist_ok=True)

    for name, record in sorted(records.items()):
        info = members[name]
        relative = PurePosixPath(name).relative_to(PROJECT_PREFIX)
        target = staging_project.joinpath(*relative.parts).resolve()
        if staging_root not in target.parents:
            raise ProjectArchiveError(f"Archive file escaped staging: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            with archive.open(info, "r") as source, target.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise ProjectArchiveError(f"Could not extract archive member: {name}") from exc
        if size != record["size"]:
            raise ProjectArchiveError(
                f"Size mismatch for {name}: expected={record['size']} actual={size}"
            )
        if digest.hexdigest() != record["sha256"]:
            raise ProjectArchiveError(f"SHA-256 mismatch for {name}")


def _validated_project_id(manifest: dict[str, Any]) -> str:
    project_id = manifest.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise ProjectArchiveError("Archive manifest has no project_id")
    try:
        validate_identifier(project_id, field_name="project_id")
    except ProjectValidationError as exc:
        raise ProjectArchiveError(f"Invalid archive project_id: {project_id!r}") from exc
    return project_id


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

        # Validate identity before it is ever used as a filesystem component.
        project_id = _validated_project_id(manifest)
        if store.project_path(project_id).parent.exists():
            raise ProjectAlreadyExists(project_id)

        with tempfile.TemporaryDirectory(prefix=".uv-import-", dir=store.root) as temp:
            temp_root = Path(temp)
            staging_project = temp_root / project_id
            _extract_project(archive, members, records, staging_project)

            # Ensure standard directories exist even when they were empty and an
            # archive producer omitted explicit directory entries.
            for name in PROJECT_DIRECTORIES:
                (staging_project / name).mkdir(parents=True, exist_ok=True)

            raw_schema_version = _raw_project_schema_version(staging_project / "project.json")
            if manifest.get("project_schema_version") != raw_schema_version:
                raise ProjectArchiveError(
                    "Manifest project_schema_version does not match project.json"
                )

            staged_store = ProjectStore(temp_root)
            document = staged_store.load_project(project_id)
            if document.project_id != project_id:
                raise ProjectArchiveError("Manifest project_id does not match project.json")
            if document.schema_version != PROJECT_SCHEMA_VERSION:
                raise ProjectArchiveError(
                    f"Unsupported imported project schema: {document.schema_version}"
                )

            store.commit_staged_project(staging_project, project_id)
            return store.load_project(project_id)
