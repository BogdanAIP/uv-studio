"""File-first project transactions and durable product-level undo/redo.

The transaction authority coordinates canonical JSON documents that belong to
one project.  A prepared journal is written before any target changes.  The
journal's final atomic ``committed`` marker is the commit point; an interrupted
prepared operation is rolled back to its exact byte snapshots on the next use.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from uv_studio.projects.generation_authority import (
    GenerationReferenceAuthorityError,
    validate_generation_reference_bytes,
)
from uv_studio.projects.identity import assert_project_identity_transition
from uv_studio.projects.migrations import migrate_project_data
from uv_studio.projects.models import (
    PROJECT_SCHEMA_VERSION,
    ProjectDocument,
    ProjectValidationError,
    utc_now_iso,
    validate_identifier,
    validate_project_relative_path,
)
from uv_studio.projects.production_state import ProductionStateError, validate_production_document
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore, ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore
from uv_studio.projects.timeline import MAIN_TIMELINE_PATH, TimelineDocument, TimelineError, TimelineStore

TRANSACTION_SCHEMA_VERSION = 1
HISTORY_SCHEMA_VERSION = 1
HISTORY_ROOT = "history"
HISTORY_INDEX_PATH = "history/index.json"
HISTORY_TRANSACTIONS_ROOT = "history/transactions"
HISTORY_OPERATIONS_ROOT = "history/operations"

_CANONICAL_JSON_ROOTS = frozenset({"production", "timeline", "tasks", "reviews"})
_MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024


class ProjectTransactionError(ProjectValidationError):
    """A project transaction or its durable history is invalid."""


class ProjectTransactionConflict(ProjectTransactionError):
    """Canonical bytes no longer match the transaction history."""


class NothingToUndo(ProjectTransactionError):
    pass


class NothingToRedo(ProjectTransactionError):
    pass


class ProjectTransactionRecoveryError(ProjectStoreError):
    """An interrupted transaction could not be restored safely."""


@dataclass(frozen=True)
class ProjectTransactionEntry:
    transaction_id: str
    command: str
    created_at: str
    changed_paths: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectTransactionEntry":
        if not isinstance(data, Mapping):
            raise ProjectTransactionError("history entry must be a JSON object")
        try:
            transaction_id = validate_identifier(
                data["transaction_id"], field_name="transaction_id"
            )
            command = data["command"]
            created_at = data["created_at"]
            changed_paths = data["changed_paths"]
        except (KeyError, ProjectValidationError) as exc:
            raise ProjectTransactionError(f"invalid history entry: {exc}") from exc
        if not isinstance(command, str) or not command.strip() or len(command.strip()) > 200:
            raise ProjectTransactionError("history command must be 1..200 characters")
        if not isinstance(created_at, str) or not created_at:
            raise ProjectTransactionError("history created_at must be non-empty text")
        if not isinstance(changed_paths, list) or not changed_paths:
            raise ProjectTransactionError("history changed_paths must be a non-empty list")
        normalized_paths = tuple(_canonical_document_path(item) for item in changed_paths)
        if len(normalized_paths) != len(set(normalized_paths)):
            raise ProjectTransactionError("history changed_paths must be unique")
        return cls(
            transaction_id=transaction_id,
            command=command.strip(),
            created_at=created_at,
            changed_paths=normalized_paths,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "command": self.command,
            "created_at": self.created_at,
            "changed_paths": list(self.changed_paths),
        }


@dataclass(frozen=True)
class ProjectHistoryState:
    entries: tuple[ProjectTransactionEntry, ...]
    cursor: int

    @property
    def can_undo(self) -> bool:
        return self.cursor > 0

    @property
    def can_redo(self) -> bool:
        return self.cursor < len(self.entries)

    @property
    def current_transaction_id(self) -> str | None:
        if self.cursor == 0:
            return None
        return self.entries[self.cursor - 1].transaction_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": HISTORY_SCHEMA_VERSION,
            "cursor": self.cursor,
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "current_transaction_id": self.current_transaction_id,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class ProjectTransactionResult:
    operation_id: str
    operation: str
    transaction_id: str
    history: ProjectHistoryState

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation": self.operation,
            "transaction_id": self.transaction_id,
            "history": self.history.to_dict(),
        }


def _canonical_document_path(value: Any) -> str:
    if not isinstance(value, str):
        raise ProjectTransactionError("transaction document path must be text")
    try:
        canonical = validate_project_relative_path(value)
    except ProjectValidationError as exc:
        raise ProjectTransactionError(str(exc)) from exc
    if canonical == PROJECT_FILENAME:
        return canonical
    parts = PurePosixPath(canonical).parts
    if not parts or parts[0] not in _CANONICAL_JSON_ROOTS:
        raise ProjectTransactionError(
            "transactions may change project.json or canonical JSON under "
            f"{sorted(_CANONICAL_JSON_ROOTS)!r}"
        )
    if PurePosixPath(canonical).suffix.lower() != ".json":
        raise ProjectTransactionError("transaction documents must be JSON files")
    return canonical


def _strict_json_bytes(
    data: Mapping[str, Any],
    *,
    relative_path: str | None = None,
) -> bytes:
    if not isinstance(data, Mapping):
        raise ProjectTransactionError("transaction document must be a JSON object")
    if relative_path == PROJECT_FILENAME and data.get("schema_version") != PROJECT_SCHEMA_VERSION:
        raise ProjectTransactionError(
            f"new transaction project.json must use schema v{PROJECT_SCHEMA_VERSION}; "
            "legacy schema bytes are valid only as historical undo/redo snapshots"
        )
    try:
        text = json.dumps(
            dict(data),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
    except (TypeError, ValueError) as exc:
        raise ProjectTransactionError("transaction document must contain strict portable JSON") from exc
    encoded = text.encode("utf-8")
    if len(encoded) > _MAX_SNAPSHOT_BYTES:
        raise ProjectTransactionError(
            f"transaction document exceeds {_MAX_SNAPSHOT_BYTES} byte history bound"
        )
    return encoded


def _snapshot(relative_path: str, content: bytes | None) -> dict[str, Any]:
    if content is None:
        return {
            "path": relative_path,
            "exists": False,
            "size": 0,
            "sha256": None,
            "content_base64": None,
        }
    if len(content) > _MAX_SNAPSHOT_BYTES:
        raise ProjectTransactionError(
            f"transaction document exceeds {_MAX_SNAPSHOT_BYTES} byte history bound"
        )
    return {
        "path": relative_path,
        "exists": True,
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


def _snapshot_content(snapshot: Mapping[str, Any]) -> bytes | None:
    if not isinstance(snapshot, Mapping):
        raise ProjectTransactionError("transaction snapshot must be a JSON object")
    relative_path = _canonical_document_path(snapshot.get("path"))
    exists = snapshot.get("exists")
    if not isinstance(exists, bool):
        raise ProjectTransactionError(f"snapshot exists flag is invalid for {relative_path!r}")
    if not exists:
        if snapshot.get("size") != 0 or snapshot.get("sha256") is not None:
            raise ProjectTransactionError(f"missing snapshot metadata is invalid for {relative_path!r}")
        return None
    encoded = snapshot.get("content_base64")
    expected_size = snapshot.get("size")
    expected_sha = snapshot.get("sha256")
    if (
        not isinstance(encoded, str)
        or isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
    ):
        raise ProjectTransactionError(f"snapshot content is invalid for {relative_path!r}")
    try:
        content = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise ProjectTransactionError(f"snapshot base64 is invalid for {relative_path!r}") from exc
    if len(content) != expected_size or len(content) > _MAX_SNAPSHOT_BYTES:
        raise ProjectTransactionError(f"snapshot size is invalid for {relative_path!r}")
    if not isinstance(expected_sha, str) or hashlib.sha256(content).hexdigest() != expected_sha:
        raise ProjectTransactionError(f"snapshot digest is invalid for {relative_path!r}")
    return content


def _project_document_from_bytes(project_id: str, content: bytes) -> ProjectDocument:
    try:
        raw = json.loads(content.decode("utf-8"))
        project = ProjectDocument.from_dict(migrate_project_data(raw))
    except (UnicodeDecodeError, json.JSONDecodeError, ProjectValidationError) as exc:
        raise ProjectTransactionError(f"invalid historical project.json: {exc}") from exc
    if project.project_id != project_id:
        raise ProjectTransactionError("historical project.json project_id does not match project")
    return project


class ProjectUnitOfWork:
    """One project-scoped transaction and undo/redo authority."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def history(self, project_id: str) -> ProjectHistoryState:
        with self.records.project_lock(project_id):
            self._ensure_history_layout(project_id)
            self._recover_prepared_operations(project_id)
            self.project_store.load_project(project_id)
            return self._load_history(project_id)

    def redo_project_documents(self, project_id: str) -> tuple[ProjectDocument, ...]:
        """Return validated project.json states reachable through the current Redo suffix.

        The method is recovery-capable like ``history()`` and validates each committed
        transaction against the durable history index.  Historical schema-v1 bytes
        are migrated only in memory for validation; the recorded snapshot bytes are
        never rewritten.
        """

        with self.records.project_lock(project_id):
            self._ensure_history_layout(project_id)
            self._recover_prepared_operations(project_id)
            previous_project = self.project_store.load_project(project_id)
            history = self._load_history(project_id)
            documents: list[ProjectDocument] = []
            for entry in history.entries[history.cursor :]:
                record = self._load_record(
                    self._record_path(project_id, entry.transaction_id, transaction=True)
                )
                if (
                    record.get("phase") != "committed"
                    or record.get("operation") != "commit"
                    or record.get("transaction_id") != entry.transaction_id
                    or record.get("command") != entry.command
                    or record.get("created_at") != entry.created_at
                ):
                    raise ProjectTransactionError(
                        "redo transaction disagrees with durable history index"
                    )
                changes = record.get("changes")
                if not isinstance(changes, list) or not changes:
                    raise ProjectTransactionError("redo transaction has invalid changes")
                changed_paths: list[str] = []
                for change in changes:
                    relative_path, _before, after = self._validated_change(change)
                    changed_paths.append(relative_path)
                    if relative_path != PROJECT_FILENAME:
                        continue
                    content = _snapshot_content(after)
                    if content is None:
                        raise ProjectTransactionError(
                            "redo transaction cannot remove project.json"
                        )
                    project = _project_document_from_bytes(project_id, content)
                    assert_project_identity_transition(previous_project, project)
                    documents.append(project)
                    previous_project = project
                if tuple(changed_paths) != entry.changed_paths:
                    raise ProjectTransactionError(
                        "redo transaction changed paths disagree with history index"
                    )
            return tuple(documents)

    def commit(
        self,
        project_id: str,
        *,
        command: str,
        documents: Mapping[str, Mapping[str, Any]],
    ) -> ProjectTransactionResult:
        if not isinstance(command, str) or not command.strip() or len(command.strip()) > 200:
            raise ProjectTransactionError("transaction command must be 1..200 characters")
        if not isinstance(documents, Mapping) or not documents:
            raise ProjectTransactionError("transaction must contain at least one document")

        with self.records.project_lock(project_id):
            self._ensure_history_layout(project_id)
            self._recover_prepared_operations(project_id)
            current_project = self.project_store.load_project(project_id)

            encoded: dict[str, bytes] = {}
            for raw_path, data in documents.items():
                relative_path = _canonical_document_path(raw_path)
                if relative_path in encoded:
                    raise ProjectTransactionError(f"duplicate transaction path: {relative_path!r}")
                encoded[relative_path] = _strict_json_bytes(
                    data,
                    relative_path=relative_path,
                )
            self._validate_documents(project_id, current_project, encoded)

            changes: list[dict[str, Any]] = []
            for relative_path in sorted(encoded):
                target = self._document_path(project_id, relative_path)
                before = self._read_document_snapshot(relative_path, target)
                after = _snapshot(relative_path, encoded[relative_path])
                if before["sha256"] == after["sha256"] and before["exists"] == after["exists"]:
                    continue
                changes.append({"path": relative_path, "before": before, "after": after})
            if not changes:
                raise ProjectTransactionError("transaction does not change canonical project state")

            history_before = self._load_history(project_id)
            transaction_id = f"tx_{uuid.uuid4().hex}"
            entry = ProjectTransactionEntry(
                transaction_id=transaction_id,
                command=command.strip(),
                created_at=utc_now_iso(),
                changed_paths=tuple(change["path"] for change in changes),
            )
            retained = history_before.entries[: history_before.cursor]
            history_after = ProjectHistoryState(
                entries=(*retained, entry),
                cursor=len(retained) + 1,
            )
            record = {
                "schema_version": TRANSACTION_SCHEMA_VERSION,
                "record_id": transaction_id,
                "operation": "commit",
                "transaction_id": transaction_id,
                "command": entry.command,
                "created_at": entry.created_at,
                "phase": "prepared",
                "changes": changes,
                "history_before": history_before.to_dict(),
                "history_after": history_after.to_dict(),
            }
            record_path = self._record_path(project_id, transaction_id, transaction=True)
            self._execute_prepared(
                project_id,
                record_path,
                record,
                changes,
                history_before,
                history_after,
            )
            return ProjectTransactionResult(
                operation_id=transaction_id,
                operation="commit",
                transaction_id=transaction_id,
                history=history_after,
            )

    def undo(self, project_id: str) -> ProjectTransactionResult:
        return self._move_cursor(project_id, operation="undo")

    def redo(self, project_id: str) -> ProjectTransactionResult:
        return self._move_cursor(project_id, operation="redo")

    def _move_cursor(self, project_id: str, *, operation: str) -> ProjectTransactionResult:
        with self.records.project_lock(project_id):
            self._ensure_history_layout(project_id)
            self._recover_prepared_operations(project_id)
            current_project = self.project_store.load_project(project_id)
            history_before = self._load_history(project_id)

            if operation == "undo":
                if not history_before.can_undo:
                    raise NothingToUndo("project history has nothing to undo")
                entry = history_before.entries[history_before.cursor - 1]
                cursor_after = history_before.cursor - 1
                source_key, target_key = "after", "before"
            elif operation == "redo":
                if not history_before.can_redo:
                    raise NothingToRedo("project history has nothing to redo")
                entry = history_before.entries[history_before.cursor]
                cursor_after = history_before.cursor + 1
                source_key, target_key = "before", "after"
            else:  # pragma: no cover - private invariant
                raise ProjectTransactionError(f"unsupported history operation: {operation!r}")

            transaction = self._load_record(
                self._record_path(project_id, entry.transaction_id, transaction=True)
            )
            if transaction.get("phase") != "committed":
                raise ProjectTransactionError(
                    f"transaction is not committed: {entry.transaction_id!r}"
                )
            raw_changes = transaction.get("changes")
            if not isinstance(raw_changes, list) or not raw_changes:
                raise ProjectTransactionError("transaction record has no changes")

            operation_changes: list[dict[str, Any]] = []
            for change in raw_changes:
                relative_path, before, after = self._validated_change(change)
                expected = after if source_key == "after" else before
                replacement = before if target_key == "before" else after
                target = self._document_path(project_id, relative_path)
                current = self._read_document_snapshot(relative_path, target)
                self._assert_snapshot_matches(current, expected, relative_path)
                operation_changes.append(
                    {"path": relative_path, "before": current, "after": dict(replacement)}
                )

            validation_documents: dict[str, bytes | None] = {}
            for change in operation_changes:
                content = _snapshot_content(change["after"])
                if content is None:
                    if change["path"] == PROJECT_FILENAME:
                        raise ProjectTransactionError("project.json cannot be removed by undo/redo")
                validation_documents[change["path"]] = content
            self._validate_documents(project_id, current_project, validation_documents)
            if operation == "redo":
                project_bytes = validation_documents.get(PROJECT_FILENAME)
                if project_bytes is not None:
                    redo_project = _project_document_from_bytes(project_id, project_bytes)
                    for artifact in redo_project.artifacts:
                        if not isinstance(artifact.metadata.get("generation"), dict):
                            continue
                        try:
                            validate_generation_reference_bytes(
                                self.project_store,
                                project_id,
                                artifact,
                            )
                        except GenerationReferenceAuthorityError as exc:
                            raise ProjectTransactionError(
                                f"Redo Generation authority is invalid: {exc}"
                            ) from exc

            history_after = ProjectHistoryState(
                entries=history_before.entries,
                cursor=cursor_after,
            )
            operation_id = f"op_{uuid.uuid4().hex}"
            record = {
                "schema_version": TRANSACTION_SCHEMA_VERSION,
                "record_id": operation_id,
                "operation": operation,
                "transaction_id": entry.transaction_id,
                "command": entry.command,
                "created_at": utc_now_iso(),
                "phase": "prepared",
                "changes": operation_changes,
                "history_before": history_before.to_dict(),
                "history_after": history_after.to_dict(),
            }
            record_path = self._record_path(project_id, operation_id, transaction=False)
            self._execute_prepared(
                project_id,
                record_path,
                record,
                operation_changes,
                history_before,
                history_after,
            )
            return ProjectTransactionResult(
                operation_id=operation_id,
                operation=operation,
                transaction_id=entry.transaction_id,
                history=history_after,
            )

    def _validate_documents(
        self,
        project_id: str,
        current_project: ProjectDocument,
        documents: Mapping[str, bytes | None],
    ) -> None:
        proposed_project = current_project
        project_bytes = documents.get(PROJECT_FILENAME)
        if PROJECT_FILENAME in documents and project_bytes is None:
            raise ProjectTransactionError("project.json cannot be removed by a transaction")
        if project_bytes is not None:
            proposed_project = _project_document_from_bytes(project_id, project_bytes)
            assert_project_identity_transition(current_project, proposed_project)

        timeline_is_staged = MAIN_TIMELINE_PATH in documents
        timeline_bytes = documents.get(MAIN_TIMELINE_PATH)
        if not timeline_is_staged and project_bytes is not None:
            timeline_path = self._document_path(project_id, MAIN_TIMELINE_PATH)
            if timeline_path.exists():
                if not timeline_path.is_file() or timeline_path.is_symlink():
                    raise ProjectTransactionError("canonical timeline must be a regular file")
                try:
                    timeline_bytes = timeline_path.read_bytes()
                except OSError as exc:
                    raise ProjectTransactionError("canonical timeline could not be read") from exc

        for relative_path, content in documents.items():
            if content is None:
                continue
            if relative_path.startswith("production/"):
                try:
                    validate_production_document(json.loads(content.decode("utf-8")))
                except (UnicodeDecodeError, json.JSONDecodeError, ProductionStateError) as exc:
                    raise ProjectTransactionError(
                        f"invalid staged production document {relative_path!r}: {exc}"
                    ) from exc
        if timeline_bytes is not None:
            try:
                timeline = TimelineDocument.from_dict(json.loads(timeline_bytes.decode("utf-8")))
                TimelineStore(self.project_store).validate(
                    project_id,
                    timeline,
                    project=proposed_project,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, TimelineError) as exc:
                raise ProjectTransactionError(f"invalid staged timeline: {exc}") from exc

    @staticmethod
    def _validated_change(
        change: Any,
    ) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
        if not isinstance(change, Mapping):
            raise ProjectTransactionError("transaction change must be a JSON object")
        relative_path = _canonical_document_path(change.get("path"))
        before = change.get("before")
        after = change.get("after")
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            raise ProjectTransactionError("transaction change snapshots are invalid")
        before_path = _canonical_document_path(before.get("path"))
        after_path = _canonical_document_path(after.get("path"))
        if before_path != relative_path or after_path != relative_path:
            raise ProjectTransactionError("transaction change snapshot paths do not match")
        _snapshot_content(before)
        _snapshot_content(after)
        return relative_path, before, after

    def _execute_prepared(
        self,
        project_id: str,
        record_path: Path,
        record: dict[str, Any],
        changes: list[dict[str, Any]],
        history_before: ProjectHistoryState,
        history_after: ProjectHistoryState,
    ) -> None:
        self.project_store._atomic_write_json(record_path, record)
        try:
            for change in changes:
                self._write_snapshot(project_id, change["after"])
            self._write_history(project_id, history_after)
            committed = dict(record)
            committed["phase"] = "committed"
            self.project_store._atomic_write_json(record_path, committed)
        except Exception as exc:
            try:
                for change in reversed(changes):
                    self._write_snapshot(project_id, change["before"])
                self._write_history(project_id, history_before)
                rolled_back = dict(record)
                rolled_back["phase"] = "rolled_back"
                self.project_store._atomic_write_json(record_path, rolled_back)
            except Exception as rollback_exc:
                raise ProjectTransactionRecoveryError(
                    "project transaction failed and exact rollback could not be completed"
                ) from rollback_exc
            raise ProjectTransactionError("project transaction failed and was rolled back") from exc

    def _recover_prepared_operations(self, project_id: str) -> None:
        paths = [
            *sorted(self._history_dir(project_id, HISTORY_TRANSACTIONS_ROOT).glob("*.json")),
            *sorted(self._history_dir(project_id, HISTORY_OPERATIONS_ROOT).glob("*.json")),
        ]
        for path in paths:
            record = self._load_record(path)
            phase = record.get("phase")
            if phase in {"committed", "rolled_back"}:
                continue
            if phase != "prepared":
                raise ProjectTransactionRecoveryError(
                    f"unsupported transaction journal phase in {path.name!r}: {phase!r}"
                )
            changes = record.get("changes")
            if not isinstance(changes, list):
                raise ProjectTransactionRecoveryError(
                    f"transaction journal has invalid changes: {path.name!r}"
                )
            history_before = self._history_from_dict(record.get("history_before"))
            try:
                for change in reversed(changes):
                    _relative_path, before, _after = self._validated_change(change)
                    self._write_snapshot(project_id, before)
                self._write_history(project_id, history_before)
                rolled_back = dict(record)
                rolled_back["phase"] = "rolled_back"
                self.project_store._atomic_write_json(path, rolled_back)
            except Exception as exc:
                raise ProjectTransactionRecoveryError(
                    f"could not recover prepared project transaction {path.name!r}"
                ) from exc

    def _ensure_history_layout(self, project_id: str) -> None:
        project_dir = self.project_store.project_directory(project_id)
        root = project_dir / HISTORY_ROOT
        if root.is_symlink():
            raise ProjectTransactionError("project history root must not be a symlink")
        try:
            root.mkdir(exist_ok=True)
        except OSError as exc:
            raise ProjectTransactionError("project history root could not be created") from exc
        for name in ("transactions", "operations"):
            path = root / name
            if path.is_symlink():
                raise ProjectTransactionError(f"project history {name} must not be a symlink")
            try:
                path.mkdir(exist_ok=True)
            except OSError as exc:
                raise ProjectTransactionError(
                    f"project history {name} directory could not be created"
                ) from exc

    def _history_dir(self, project_id: str, relative: str) -> Path:
        project_dir = self.project_store.project_directory(project_id)
        path = project_dir.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_dir():
            raise ProjectTransactionError(f"project history directory is invalid: {relative!r}")
        return path

    def _history_path(self, project_id: str) -> Path:
        return self.project_store.resolve_project_file(
            project_id,
            HISTORY_INDEX_PATH,
            allowed_roots=(HISTORY_ROOT,),
        )

    def _record_path(self, project_id: str, record_id: str, *, transaction: bool) -> Path:
        record_id = validate_identifier(record_id, field_name="transaction record_id")
        root = HISTORY_TRANSACTIONS_ROOT if transaction else HISTORY_OPERATIONS_ROOT
        return self.project_store.resolve_project_file(
            project_id,
            f"{root}/{record_id}.json",
            allowed_roots=(HISTORY_ROOT,),
        )

    def _document_path(self, project_id: str, relative_path: str) -> Path:
        if relative_path == PROJECT_FILENAME:
            return self.project_store.project_path(project_id)
        root = PurePosixPath(relative_path).parts[0]
        return self.project_store.resolve_project_file(
            project_id,
            relative_path,
            allowed_roots=(root,),
        )

    def _read_document_snapshot(self, relative_path: str, path: Path) -> dict[str, Any]:
        if not path.exists():
            return _snapshot(relative_path, None)
        if not path.is_file() or path.is_symlink():
            raise ProjectTransactionError(
                f"transaction target must be a regular project file: {relative_path!r}"
            )
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ProjectTransactionError(
                f"transaction target could not be read: {relative_path!r}"
            ) from exc
        return _snapshot(relative_path, content)

    def _write_snapshot(self, project_id: str, snapshot: Mapping[str, Any]) -> None:
        relative_path = _canonical_document_path(snapshot.get("path"))
        target = self._document_path(project_id, relative_path)
        content = _snapshot_content(snapshot)
        if content is None:
            if target.is_symlink():
                raise ProjectTransactionError(
                    f"transaction target must not be a symlink: {relative_path!r}"
                )
            target.unlink(missing_ok=True)
            return
        self.project_store._atomic_write_bytes(target, content)

    @staticmethod
    def _assert_snapshot_matches(
        current: Mapping[str, Any],
        expected: Mapping[str, Any],
        relative_path: str,
    ) -> None:
        expected_content = _snapshot_content(expected)
        current_content = _snapshot_content(current)
        if current_content != expected_content:
            raise ProjectTransactionConflict(
                f"canonical document changed outside transaction history: {relative_path!r}"
            )

    def _load_history(self, project_id: str) -> ProjectHistoryState:
        path = self._history_path(project_id)
        if not path.exists():
            return ProjectHistoryState(entries=(), cursor=0)
        if not path.is_file() or path.is_symlink():
            raise ProjectTransactionError("project history index must be a regular file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectTransactionError("project history index is malformed") from exc
        return self._history_from_dict(data)

    def _history_from_dict(self, data: Any) -> ProjectHistoryState:
        if not isinstance(data, Mapping):
            raise ProjectTransactionError("project history must be a JSON object")
        if data.get("schema_version") != HISTORY_SCHEMA_VERSION:
            raise ProjectTransactionError("unsupported project history schema")
        raw_entries = data.get("entries")
        cursor = data.get("cursor")
        if not isinstance(raw_entries, list):
            raise ProjectTransactionError("project history entries must be a list")
        entries = tuple(ProjectTransactionEntry.from_dict(item) for item in raw_entries)
        ids = [entry.transaction_id for entry in entries]
        if len(ids) != len(set(ids)):
            raise ProjectTransactionError("project history transaction IDs must be unique")
        if isinstance(cursor, bool) or not isinstance(cursor, int) or not 0 <= cursor <= len(entries):
            raise ProjectTransactionError("project history cursor is out of bounds")
        return ProjectHistoryState(entries=entries, cursor=cursor)

    def _write_history(self, project_id: str, history: ProjectHistoryState) -> None:
        self.project_store._atomic_write_json(self._history_path(project_id), history.to_dict())

    @staticmethod
    def _load_record(path: Path) -> dict[str, Any]:
        if not path.is_file() or path.is_symlink():
            raise ProjectTransactionError(f"transaction record is missing or unsafe: {path.name!r}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectTransactionError(f"transaction record is malformed: {path.name!r}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != TRANSACTION_SCHEMA_VERSION:
            raise ProjectTransactionError(f"unsupported transaction record: {path.name!r}")
        return data
