"""Durable non-secret provenance for authorized external capability execution."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from typing import Any, Mapping

from uv_studio.mcp.manager import MCPExecutionTarget
from uv_studio.projects.models import utc_now_iso
from uv_studio.projects.task_records import ProjectTaskRecordStore

from .authorization import ExecutionPreparation
from .models import CapabilityOffer

# Version 1 records used MCP-specific top-level profile_id/tool_name fields.
# Version 2 keeps executor identity transport-neutral. Existing v1 files are
# immutable project history and require no migration.
EXTERNAL_RUN_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class ExternalExecutorIdentity:
    kind: str
    identity: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("external executor kind must be non-empty")
        normalized: dict[str, str] = {}
        for key, value in self.identity.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("external executor identity keys must be non-empty strings")
            if not isinstance(value, str) or not value.strip():
                raise ValueError("external executor identity values must be non-empty strings")
            normalized[key] = value
        if not normalized:
            raise ValueError("external executor identity must not be empty")
        object.__setattr__(self, "kind", self.kind.strip())
        object.__setattr__(self, "identity", normalized)

    @classmethod
    def for_mcp(cls, target: MCPExecutionTarget) -> "ExternalExecutorIdentity":
        return cls(
            kind="mcp",
            identity={
                "profile_id": target.profile.profile_id,
                "tool_name": target.binding.tool_name,
            },
        )

    @classmethod
    def for_native_videoclaw(cls, operation: str) -> "ExternalExecutorIdentity":
        return cls(kind="native_videoclaw", identity={"operation": operation})

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "identity": dict(self.identity)}


@dataclass(frozen=True)
class ExternalRunRecord:
    run_id: str
    project_id: str
    capability_id: str
    offer_id: str
    adapter_id: str
    executor: ExternalExecutorIdentity
    started_at: str
    ended_at: str | None
    authorization_required: bool
    consent_scopes: tuple[str, ...]
    cost_class: str
    cost_estimate: dict[str, Any]
    input_digest: str
    status: str
    result_summary: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    schema_version: int = EXTERNAL_RUN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "adapter_id": self.adapter_id,
            "executor": self.executor.to_dict(),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "authorization": {
                "required": self.authorization_required,
                "consent_scopes": list(self.consent_scopes),
            },
            "cost": {
                "class": self.cost_class,
                "estimate": dict(self.cost_estimate),
            },
            "input_digest": self.input_digest,
            "status": self.status,
            "result_summary": None if self.result_summary is None else dict(self.result_summary),
            "error": None if self.error is None else dict(self.error),
        }


class ExternalRunProvenance:
    def __init__(self, records: ProjectTaskRecordStore) -> None:
        self.records = records

    def start(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        preparation: ExecutionPreparation,
        executor: ExternalExecutorIdentity,
    ) -> ExternalRunRecord:
        if preparation.intent.project_id != project_id:
            raise ValueError("execution preparation project does not match provenance project")
        if preparation.intent.capability_id != offer.capability_id:
            raise ValueError("execution preparation capability does not match selected offer")
        if preparation.intent.offer_id != offer.offer_id:
            raise ValueError("execution preparation offer does not match selected offer")
        run_id = f"run_{uuid.uuid4().hex}"
        record = ExternalRunRecord(
            run_id=run_id,
            project_id=project_id,
            capability_id=offer.capability_id,
            offer_id=offer.offer_id,
            adapter_id=offer.adapter_id,
            executor=executor,
            started_at=utc_now_iso(),
            ended_at=None,
            authorization_required=preparation.authorization_required,
            consent_scopes=tuple(item.value for item in preparation.consent_required),
            cost_class=offer.cost_class.value,
            cost_estimate=preparation.cost_estimate.to_dict(),
            input_digest=preparation.intent.input_digest,
            status="running",
        )
        self._persist(record)
        return record

    def succeed(
        self,
        record: ExternalRunRecord,
        result: Mapping[str, Any],
        *,
        references: Mapping[str, str] | None = None,
    ) -> ExternalRunRecord:
        summary = self._result_summary(dict(result))
        if references:
            summary["references"] = dict(references)
        updated = replace(
            record,
            ended_at=utc_now_iso(),
            status="succeeded",
            result_summary=summary,
            error=None,
        )
        self._persist(updated)
        return updated

    def fail(self, record: ExternalRunRecord, exc: Exception) -> ExternalRunRecord:
        code = getattr(exc, "code", "external_execution_failed")
        updated = replace(
            record,
            ended_at=utc_now_iso(),
            status="failed",
            result_summary=None,
            error={
                "class": type(exc).__name__,
                "code": str(code),
            },
        )
        self._persist(updated)
        return updated

    def _persist(self, record: ExternalRunRecord) -> None:
        self.records.write(record.project_id, record.run_id, record.to_dict())

    @staticmethod
    def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return {
            "json_bytes": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
