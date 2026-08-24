"""Recoverable file-first transaction journal for coordinated project JSON writes.

The journal is intentionally storage-level. It knows only canonical project-relative
JSON files, one pending operation and one history index. Application semantics such
as timeline commands and undo/redo live above this module.

Commit protocol:

1. atomically persist ``transactions/pending.json`` with exact before/after snapshots;
2. replace all coordinated canonical JSON files;
3. persist any immutable history record;
4. atomically replace ``transactions/index.json`` as the commit marker;
5. remove ``pending.json``.

Recovery is deterministic: if the durable index equals the pending operation's
``after_index`` the operation committed and recovery enforces the after snapshots.
Otherwise the index must still equal ``before_index`` and recovery restores the
before snapshots. An unrelated index state fails closed instead of guessing.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

TRANSACTION_SCHEMA_VERSION = 1
TRANSACTIONS_DIRNAME = "transactions"
TRANSACTION_HISTORY_DIRNAME = "history"
TRANSACTION_INDEX_PATH = "transactions/index.json"
TRANSACTION_PENDING_PATH = "transactions/pending.json"
MAX_TRANSACTION_HISTORY = 50
MAX_TRANSACTION_SNAPSHOT_BYTES = 4 * 1024 * 1024
_MANAGED_FILES = frozenset({"project.json", "timeline/main.json"})


class ProjectTransactionLogError(RuntimeError):
    """Malformed, unsafe or irreconcilable project transaction state."""


def empty_transaction_index() -> dict[str, Any]:
    return {
        "schema_version": TRANSACTION_SCHEMA_VERSION,
        "history": [],
        "cursor": 0,
    }


def canonical_json_bytes(data: Mapping[str, Any]) -> bytes:
    try:
        text = json.dumps(
            dict(data),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProjectTransactionLogError("transaction snapshot is not strict JSON") from exc
    return text.encode("utf-8")


def snapshot_sha256(data: Mapping[str, Any] | None) -> str:
    if data is None:
        return hashlib.sha256(b"<absent>").hexdigest()
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


def snapshot_size(data: Mapping[str, Any] | None) -> int:
    return len(canonical_json_bytes(data)) if data is not None else 0


def validate_transaction_index(data: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        raise ProjectTransactionLogError("transaction index must be a JSON object")
    allowed = {"schema_version", "history", "cursor"}
    unknown = set(data).difference(allowed)
    if unknown:
        raise ProjectTransactionLogError(f"unsupported transaction index fields: {sorted(unknown)!r}")
    if data.get("schema_version") != TRANSACTION_SCHEMA_VERSION:
        raise ProjectTransactionLogError("unsupported transaction index schema")
    history = data.get("history")
    cursor = data.get("cursor")
    if not isinstance(history, list) or not all(isinstance(item, str) and item for item in history):
        raise ProjectTransactionLogError("transaction index history must contain transaction IDs")
    if len(history) != len(set(history)):
        raise ProjectTransactionLogError("transaction index history IDs must be unique")
    if len(history) > MAX_TRANSACTION_HISTORY:
        raise ProjectTransactionLogError("transaction index exceeds bounded history")
    if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0 or cursor > len(history):
        raise ProjectTransactionLogError("transaction index cursor is invalid")
    return {
        "schema_version": TRANSACTION_SCHEMA_VERSION,
        "history": list(history),
        "cursor": cursor,
    }


def _strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value!r}")
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectTransactionLogError(f"cannot read transaction JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise ProjectTransactionLogError(f"transaction JSON must be an object: {path.name}")
    return value


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        serialized = json.dumps(
            dict(data),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def ensure_transaction_directories(project_dir: Path) -> Path:
    root = project_dir / TRANSACTIONS_DIRNAME
    if root.exists() and (not root.is_dir() or root.is_symlink()):
        raise ProjectTransactionLogError("transactions path must be a regular project directory")
    root.mkdir(exist_ok=True)
    history = root / TRANSACTION_HISTORY_DIRNAME
    if history.exists() and (not history.is_dir() or history.is_symlink()):
        raise ProjectTransactionLogError("transaction history path must be a regular directory")
    history.mkdir(exist_ok=True)
    return root


def load_transaction_index(project_dir: Path) -> dict[str, Any]:
    path = project_dir / TRANSACTION_INDEX_PATH
    if not path.exists():
        return empty_transaction_index()
    if not path.is_file() or path.is_symlink():
        raise ProjectTransactionLogError("transaction index must be a regular file")
    return validate_transaction_index(_strict_json(path))


def write_transaction_index(project_dir: Path, index: Mapping[str, Any]) -> None:
    normalized = validate_transaction_index(index)
    ensure_transaction_directories(project_dir)
    _atomic_write_json(project_dir / TRANSACTION_INDEX_PATH, normalized)


def history_record_path(project_dir: Path, transaction_id: str) -> Path:
    if not isinstance(transaction_id, str) or not transaction_id.startswith("txn_"):
        raise ProjectTransactionLogError("invalid transaction ID")
    if len(transaction_id) > 128 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for ch in transaction_id):
        raise ProjectTransactionLogError("invalid transaction ID")
    return project_dir / TRANSACTIONS_DIRNAME / TRANSACTION_HISTORY_DIRNAME / f"{transaction_id}.json"


def load_history_record(project_dir: Path, transaction_id: str) -> dict[str, Any]:
    path = history_record_path(project_dir, transaction_id)
    if not path.is_file() or path.is_symlink():
        raise ProjectTransactionLogError(f"transaction history record is missing: {transaction_id}")
    record = _strict_json(path)
    _validate_history_record(record, expected_id=transaction_id)
    return record


def write_history_record(project_dir: Path, record: Mapping[str, Any]) -> None:
    normalized = _validate_history_record(record)
    ensure_transaction_directories(project_dir)
    _atomic_write_json(history_record_path(project_dir, normalized["transaction_id"]), normalized)


def write_pending_operation(project_dir: Path, pending: Mapping[str, Any]) -> None:
    normalized = _validate_pending(pending)
    ensure_transaction_directories(project_dir)
    _atomic_write_json(project_dir / TRANSACTION_PENDING_PATH, normalized)


def clear_pending_operation(project_dir: Path) -> None:
    path = project_dir / TRANSACTION_PENDING_PATH
    if path.is_symlink():
        raise ProjectTransactionLogError("pending transaction path must not be a symlink")
    path.unlink(missing_ok=True)


def _validate_snapshot_map(value: Any, *, field_name: str) -> dict[str, dict[str, Any] | None]:
    if not isinstance(value, Mapping):
        raise ProjectTransactionLogError(f"{field_name} must be a JSON object")
    if set(value) != _MANAGED_FILES:
        raise ProjectTransactionLogError(
            f"{field_name} must contain exactly {sorted(_MANAGED_FILES)!r}"
        )
    result: dict[str, dict[str, Any] | None] = {}
    total = 0
    for relative_path in sorted(_MANAGED_FILES):
        snapshot = value[relative_path]
        if snapshot is not None and not isinstance(snapshot, Mapping):
            raise ProjectTransactionLogError(f"{field_name}.{relative_path} must be object or null")
        normalized = None if snapshot is None else dict(snapshot)
        total += snapshot_size(normalized)
        result[relative_path] = normalized
    if total > MAX_TRANSACTION_SNAPSHOT_BYTES:
        raise ProjectTransactionLogError("transaction snapshots exceed bounded JSON history size")
    return result


def _validate_hash_map(value: Any, *, field_name: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != _MANAGED_FILES:
        raise ProjectTransactionLogError(f"{field_name} must cover every managed file")
    result: dict[str, str] = {}
    for relative_path in sorted(_MANAGED_FILES):
        digest = value[relative_path]
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ProjectTransactionLogError(f"invalid SHA-256 in {field_name}.{relative_path}")
        result[relative_path] = digest
    return result


def _validate_history_record(
    value: Mapping[str, Any],
    *,
    expected_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectTransactionLogError("transaction history record must be an object")
    allowed = {
        "schema_version",
        "transaction_id",
        "label",
        "created_at",
        "before_files",
        "after_files",
        "before_hashes",
        "after_hashes",
    }
    unknown = set(value).difference(allowed)
    if unknown:
        raise ProjectTransactionLogError(f"unsupported history record fields: {sorted(unknown)!r}")
    if value.get("schema_version") != TRANSACTION_SCHEMA_VERSION:
        raise ProjectTransactionLogError("unsupported transaction history schema")
    transaction_id = value.get("transaction_id")
    history_record_path(Path("."), str(transaction_id))
    if expected_id is not None and transaction_id != expected_id:
        raise ProjectTransactionLogError("transaction history ID mismatch")
    label = value.get("label")
    created_at = value.get("created_at")
    if not isinstance(label, str) or not label.strip() or len(label) > 200:
        raise ProjectTransactionLogError("transaction label must be 1..200 characters")
    if not isinstance(created_at, str) or not created_at:
        raise ProjectTransactionLogError("transaction created_at is required")
    before_files = _validate_snapshot_map(value.get("before_files"), field_name="before_files")
    after_files = _validate_snapshot_map(value.get("after_files"), field_name="after_files")
    before_hashes = _validate_hash_map(value.get("before_hashes"), field_name="before_hashes")
    after_hashes = _validate_hash_map(value.get("after_hashes"), field_name="after_hashes")
    for relative_path in _MANAGED_FILES:
        if snapshot_sha256(before_files[relative_path]) != before_hashes[relative_path]:
            raise ProjectTransactionLogError("before snapshot hash mismatch")
        if snapshot_sha256(after_files[relative_path]) != after_hashes[relative_path]:
            raise ProjectTransactionLogError("after snapshot hash mismatch")
    return {
        "schema_version": TRANSACTION_SCHEMA_VERSION,
        "transaction_id": transaction_id,
        "label": label.strip(),
        "created_at": created_at,
        "before_files": before_files,
        "after_files": after_files,
        "before_hashes": before_hashes,
        "after_hashes": after_hashes,
    }


def _validate_pending(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectTransactionLogError("pending transaction must be an object")
    allowed = {
        "schema_version",
        "operation_id",
        "operation",
        "before_index",
        "after_index",
        "before_files",
        "after_files",
        "history_record",
    }
    unknown = set(value).difference(allowed)
    if unknown:
        raise ProjectTransactionLogError(f"unsupported pending transaction fields: {sorted(unknown)!r}")
    if value.get("schema_version") != TRANSACTION_SCHEMA_VERSION:
        raise ProjectTransactionLogError("unsupported pending transaction schema")
    operation_id = value.get("operation_id")
    if not isinstance(operation_id, str) or not operation_id.startswith("op_") or len(operation_id) > 128:
        raise ProjectTransactionLogError("pending operation_id is invalid")
    operation = value.get("operation")
    if operation not in {"commit", "undo", "redo"}:
        raise ProjectTransactionLogError("pending operation is invalid")
    before_index = validate_transaction_index(value.get("before_index"))
    after_index = validate_transaction_index(value.get("after_index"))
    before_files = _validate_snapshot_map(value.get("before_files"), field_name="before_files")
    after_files = _validate_snapshot_map(value.get("after_files"), field_name="after_files")
    history_record = value.get("history_record")
    normalized_record = None
    if history_record is not None:
        if operation != "commit":
            raise ProjectTransactionLogError("only commit may carry a new history record")
        normalized_record = _validate_history_record(history_record)
    return {
        "schema_version": TRANSACTION_SCHEMA_VERSION,
        "operation_id": operation_id,
        "operation": operation,
        "before_index": before_index,
        "after_index": after_index,
        "before_files": before_files,
        "after_files": after_files,
        "history_record": normalized_record,
    }


def _managed_path(project_dir: Path, relative_path: str) -> Path:
    if relative_path not in _MANAGED_FILES:
        raise ProjectTransactionLogError(f"transaction cannot manage path: {relative_path!r}")
    pure = PurePosixPath(relative_path)
    candidate = project_dir.joinpath(*pure.parts)
    resolved_parent = candidate.parent.resolve()
    resolved_project = project_dir.resolve()
    if resolved_parent != resolved_project and resolved_project not in resolved_parent.parents:
        raise ProjectTransactionLogError("transaction managed path escaped project directory")
    return candidate


def apply_snapshots(project_dir: Path, snapshots: Mapping[str, Mapping[str, Any] | None]) -> None:
    normalized = _validate_snapshot_map(snapshots, field_name="snapshots")
    # Project first, timeline second. Readers are serialized by ProjectStore's RLock;
    # crash recovery runs before ProjectStore returns canonical project state.
    for relative_path in ("project.json", "timeline/main.json"):
        path = _managed_path(project_dir, relative_path)
        snapshot = normalized[relative_path]
        if snapshot is None:
            if path.is_symlink():
                raise ProjectTransactionLogError("transaction target must not be a symlink")
            path.unlink(missing_ok=True)
        else:
            _atomic_write_json(path, snapshot)


def read_managed_snapshots(project_dir: Path) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for relative_path in ("project.json", "timeline/main.json"):
        path = _managed_path(project_dir, relative_path)
        if not path.exists():
            result[relative_path] = None
            continue
        if not path.is_file() or path.is_symlink():
            raise ProjectTransactionLogError(f"managed transaction path is not a regular file: {relative_path}")
        result[relative_path] = _strict_json(path)
    return _validate_snapshot_map(result, field_name="managed snapshots")


def managed_snapshot_hashes(
    snapshots: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, str]:
    normalized = _validate_snapshot_map(snapshots, field_name="snapshots")
    return {path: snapshot_sha256(snapshot) for path, snapshot in normalized.items()}


def recover_project_transaction_state(project_dir: Path) -> None:
    """Finish or roll back one interrupted coordinated JSON operation."""

    pending_path = project_dir / TRANSACTION_PENDING_PATH
    if not pending_path.exists():
        return
    if not pending_path.is_file() or pending_path.is_symlink():
        raise ProjectTransactionLogError("pending transaction must be a regular file")
    pending = _validate_pending(_strict_json(pending_path))
    current_index = load_transaction_index(project_dir)
    before_index = pending["before_index"]
    after_index = pending["after_index"]

    if current_index == after_index:
        # Index is the commit marker. Enforce the committed snapshots and record.
        apply_snapshots(project_dir, pending["after_files"])
        record = pending["history_record"]
        if record is not None:
            write_history_record(project_dir, record)
    elif current_index == before_index:
        # No commit marker: no coordinated changes may leak out.
        apply_snapshots(project_dir, pending["before_files"])
        record = pending["history_record"]
        if record is not None:
            record_path = history_record_path(project_dir, record["transaction_id"])
            if record_path.is_symlink():
                raise ProjectTransactionLogError("history record path must not be a symlink")
            record_path.unlink(missing_ok=True)
    else:
        raise ProjectTransactionLogError(
            "pending transaction index does not match before or after state; refusing recovery"
        )
    clear_pending_operation(project_dir)


def cleanup_unreferenced_history(project_dir: Path, index: Mapping[str, Any]) -> None:
    normalized = validate_transaction_index(index)
    history_dir = ensure_transaction_directories(project_dir) / TRANSACTION_HISTORY_DIRNAME
    keep = {f"{transaction_id}.json" for transaction_id in normalized["history"]}
    for path in history_dir.iterdir():
        if path.name in keep:
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix == ".json" and path.name.startswith("txn_"):
            path.unlink(missing_ok=True)
