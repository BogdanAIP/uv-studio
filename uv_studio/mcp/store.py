"""Atomic machine-global MCP configuration store.

This store is intentionally separate from Project Store. Portable `.uvproj.zip`
archives must not capture machine commands or credential references.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Mapping

from .models import MCPConfiguration, MCPConfigurationError


class MCPConfigStoreError(RuntimeError):
    pass


class MCPConfigStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "mcp.json"
        self.logs_dir = self.root / "mcp-logs"
        self._lock = threading.RLock()

    def load(self) -> MCPConfiguration:
        if not self.path.exists():
            return MCPConfiguration.empty()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPConfigStoreError(f"Malformed MCP configuration: {self.path}") from exc
        except OSError as exc:
            raise MCPConfigStoreError(f"Could not read MCP configuration: {self.path}") from exc
        try:
            return MCPConfiguration.from_dict(raw)
        except (MCPConfigurationError, TypeError, ValueError) as exc:
            raise MCPConfigStoreError(f"Invalid MCP configuration: {exc}") from exc

    def save(self, config: MCPConfiguration) -> MCPConfiguration:
        if not isinstance(config, MCPConfiguration):
            raise MCPConfigStoreError("save accepts only MCPConfiguration")
        with self._lock:
            self._atomic_write_json(config.to_dict())
        return config

    def _atomic_write_json(self, data: Mapping[str, Any]) -> None:
        temp = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            serialized = json.dumps(
                dict(data), ensure_ascii=False, indent=2, sort_keys=True
            ) + "\n"
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    def stderr_log_path(self, profile_id: str) -> Path:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        return self.logs_dir / f"{profile_id}.stderr.log"
