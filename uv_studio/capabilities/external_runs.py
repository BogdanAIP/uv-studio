"""Durable secret-free provenance for external capability runs."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from uv_studio.projects.models import utc_now_iso, validate_identifier
from uv_studio.projects.store import ProjectStore

from .consent import CostEstimateState, ExecutionCostEstimate

EXTERNAL_RUN_SCHEMA_VERSION = 1
_MAX_ERROR_LENGTH = 2000


class ExternalRunStoreError(RuntimeError):
    pass


class ExternalRunStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ExternalRunRecord:
    run_id: str
    project_id: str
    capability_id: str
    offer_id: str
    adapter_id: str
    tool_identity: str
    input_digest: str
    authorization_mode: str
    authorization_grant_id: str | None
    cost_estimate: ExecutionCostEstimate
    status: ExternalRunStatus
    started_at: str
    completed_at: str | None = None
    result_summary: Mapping[str, Any] | None = None
    error_class: str | None = None
    error_message: str | None = None
    schema_version: int = EXTERNAL_RUN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_identifier(self.run_id, field_name="run_id")
        validate_identifier(self.project_id, field_name="project_id")
        if self.authorization_grant_id is not None:
            validate_identifier(self.authorization_grant_id, field_name="authorization_grant_id")
        if self.schema_version != EXTERNAL_RUN_SCHEMA_VERSION:
            raise ExternalRunStoreError(
                f"ExternalRunRecord only supports schema v{EXTERNAL_RUN_SCHEMA_VERSION}"
            )
        if self.error_message is not None and len(self.error_message) > _MAX_ERROR_LENGTH:
            object.__setattr__(self, "error_message", self.error_message[:_MAX_ERROR_LENGTH])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "adapter_id": self.adapter_id,
            "tool_identity": self.tool_identity,
            "input_digest": self.input_digest,
            "authorization_mode": self.authorization_mode,
            "authorization_grant_id": self.authorization_grant_id,
            "cost_estimate": self.cost_estimate.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_summary": None if self.result_summary is None else dict(self.result_summary),
            "error_class": self.error_class,
            "error_message": self.error_message,
        }


class ExternalRunStore:
    def __init__(self, projects: ProjectStore) -> None:
        self.projects = projects

    def start(
        self,
        *,
        project_id: str,
        capability_id: str,
        offer_id: str,
        adapter_id: str,
        tool_identity: str,
        input_digest: str,
        authorization_mode: str,
        authorization_grant_id: str | None,
        cost_estimate: ExecutionCostEstimate,
    ) -> ExternalRunRecord:
        run = ExternalRunRecord(
            run_id=f"run_{uuid.uuid4().hex}",
            project_id=project_id,
            capability_id=capability_id,
            offer_id=offer_id,
            adapter_id=adapter_id,
            tool_identity=tool_identity,
            input_digest=input_digest,
            authorization_mode=authorization_mode,
            authorization_grant_id=authorization_grant_id,
            cost_estimate=cost_estimate,
            status=ExternalRunStatus.RUNNING,
            started_at=utc_now_iso(),
        )
        self._write(run)
        return run

    def succeed(
        self,
        run: ExternalRunRecord,
        *,
        result_summary: Mapping[str, Any] | None = None,
    ) -> ExternalRunRecord:
        updated = replace(
            run,
            status=ExternalRunStatus.SUCCEEDED,
            completed_at=utc_now_iso(),
            result_summary=None if result_summary is None else dict(result_summary),
        )
        self._write(updated)
        return updated

    def fail(self, run: ExternalRunRecord, exc: Exception) -> ExternalRunRecord:
        updated = replace(
            run,
            status=ExternalRunStatus.FAILED,
            completed_at=utc_now_iso(),
            error_class=type(exc).__name__,
            error_message=str(exc)[:_MAX_ERROR_LENGTH],
        )
        self._write(updated)
        return updated

    def load(self, project_id: str, run_id: str) -> ExternalRunRecord:
        validate_identifier(run_id, field_name="run_id")
        path = self._path(project_id, run_id)
        if not path.is_file():
            raise ExternalRunStoreError(f"external run not found: {run_id}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExternalRunStoreError(f"could not load external run: {run_id}") from exc
        try:
            return self._from_dict(data)
        except (KeyError, TypeError, ValueError, ExternalRunStoreError) as exc:
            raise ExternalRunStoreError(f"invalid external run record: {run_id}") from exc

    def _path(self, project_id: str, run_id: str) -> Path:
        project_dir = self.projects.project_directory(project_id)
        return project_dir / "tasks" / f"{run_id}.external.json"

    def _write(self, run: ExternalRunRecord) -> None:
        path = self._path(run.project_id, run.run_id)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            payload = json.dumps(
                run.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
            ) + "\n"
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    @staticmethod
    def _from_dict(data: Mapping[str, Any]) -> ExternalRunRecord:
        estimate_data = data["cost_estimate"]
        estimate = ExecutionCostEstimate(
            state=CostEstimateState(estimate_data["state"]),
            currency=estimate_data.get("currency"),
            amount=estimate_data.get("amount"),
            upper_bound=estimate_data.get("upper_bound"),
            source=estimate_data.get("source", "offer_metadata"),
        )
        return ExternalRunRecord(
            schema_version=int(data.get("schema_version", EXTERNAL_RUN_SCHEMA_VERSION)),
            run_id=data["run_id"],
            project_id=data["project_id"],
            capability_id=data["capability_id"],
            offer_id=data["offer_id"],
            adapter_id=data["adapter_id"],
            tool_identity=data["tool_identity"],
            input_digest=data["input_digest"],
            authorization_mode=data["authorization_mode"],
            authorization_grant_id=data.get("authorization_grant_id"),
            cost_estimate=estimate,
            status=ExternalRunStatus(data["status"]),
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            result_summary=data.get("result_summary"),
            error_class=data.get("error_class"),
            error_message=data.get("error_message"),
        )
