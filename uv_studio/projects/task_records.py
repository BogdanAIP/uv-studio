"""Atomic versioned task/run records inside canonical UV Studio projects."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Mapping

from .models import validate_identifier
from .store import ProjectStore


class ProjectTaskRecordStore:
    """Write canonical JSON run records under the project's existing tasks/ root."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self._lock = threading.RLock()

    def path(self, project_id: str, run_id: str) -> Path:
        validate_identifier(run_id, field_name="run_id")
        return self.project_store.resolve_project_file(
            project_id,
            f"tasks/{run_id}.json",
            allowed_roots=("tasks",),
        )

    def write(self, project_id: str, run_id: str, data: Mapping[str, Any]) -> Path:
        if not isinstance(data, Mapping):
            raise TypeError("task record must be a mapping")
        path = self.path(project_id, run_id)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with self._lock:
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
        return path
