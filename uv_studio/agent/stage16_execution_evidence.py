"""Final Stage-16 foreground execution evidence and recovery semantics.

This refinement stays above the existing Stage-15 AgentHarness and Stage-16
Planner/Task/Skill contracts. It keeps already-committed work recoverable when
success-trace persistence fails, records the exact execution-time policy used for
dispatch, and restores Timeline identities created by production.accept_take.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from uv_studio.projects.models import ProjectValidationError, utc_now_iso, validate_identifier
from uv_studio.projects.task_records import ProjectTaskRecordConflict, ProjectTaskRecordStore
from uv_studio.projects.timeline import MAIN_TIMELINE_PATH
from uv_studio.projects.transactions import ProjectTransactionError

from .models import (
    AgentPolicyProjection,
    AgentTraceRecord,
    portable_json,
    stable_digest,
)
from .orchestration import (
    AgentTaskBlocked,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_recovery import (
    AgentPlanner,
    AgentTaskCoordinator as _RecoveryAgentTaskCoordinator,
    _CorrelatedProjectUnitOfWork,
    _RecoveryAgentTaskStore,
    _execution_context,
    _execution_correlation,
    _typed_correlation_reference,
    _validate_context_digest,
)

_EXECUTION_EVIDENCE_RECORD_TYPE = "agent_execution_evidence"
_EXECUTION_EVIDENCE_SCHEMA_VERSION = 1


def _validate_digest(value: Any, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AgentTaskStateError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _execution_evidence_id(plan_id: str, task_id: str, skill_id: str | None) -> str:
    digest = stable_digest(
        {
            "record_type": _EXECUTION_EVIDENCE_RECORD_TYPE,
            "plan_id": plan_id,
            "task_id": task_id,
            "skill_id": skill_id,
        }
    )
    return f"agent_exec_{digest[:32]}"


@dataclass(frozen=True)
class _ExecutionEvidence:
    record_id: str
    project_id: str
    plan_id: str
    task_id: str
    action_id: str
    skill_id: str | None
    created_at: str
    context_digest: str
    input_digest: str
    policy: AgentPolicyProjection

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": _EXECUTION_EVIDENCE_RECORD_TYPE,
            "schema_version": _EXECUTION_EVIDENCE_SCHEMA_VERSION,
            "record_id": self.record_id,
            "project_id": self.project_id,
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "action_id": self.action_id,
            "skill_id": self.skill_id,
            "created_at": self.created_at,
            "context_digest": self.context_digest,
            "input_digest": self.input_digest,
            "policy": self.policy.to_dict(),
        }


class _ExecutionEvidenceStore:
    """Append-only execution metadata under the existing project tasks authority."""

    def __init__(self, project_store: Any) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def append(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        action_id: str,
        skill_id: str | None,
        context_digest: str,
        input_digest: str,
        policy: AgentPolicyProjection,
    ) -> _ExecutionEvidence:
        record_id = _execution_evidence_id(plan_id, task_id, skill_id)
        evidence = _ExecutionEvidence(
            record_id=record_id,
            project_id=validate_identifier(project_id, field_name="project_id"),
            plan_id=validate_identifier(plan_id, field_name="plan_id"),
            task_id=validate_identifier(task_id, field_name="task_id"),
            action_id=policy.action_id,
            skill_id=(
                validate_identifier(skill_id, field_name="skill_id")
                if skill_id is not None
                else None
            ),
            created_at=utc_now_iso(),
            context_digest=_validate_context_digest(
                context_digest,
                field_name="execution evidence context digest",
            ),
            input_digest=_validate_digest(
                input_digest,
                field_name="execution evidence input digest",
            ),
            policy=policy,
        )
        if evidence.action_id != action_id:
            raise AgentTaskStateError("execution policy action does not match Agent Task")
        payload = portable_json(
            evidence.to_dict(),
            field_name="Agent execution evidence",
        )
        try:
            self.records.create_if_absent(project_id, record_id, payload)
        except ProjectTaskRecordConflict as exc:
            raise AgentTaskStateError(
                f"execution evidence already exists for Agent Task {task_id!r}"
            ) from exc
        return evidence

    def get(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        skill_id: str | None,
    ) -> _ExecutionEvidence | None:
        record_id = _execution_evidence_id(plan_id, task_id, skill_id)
        with self.project_store._lock, self.records.project_lock(project_id):
            path = self.records.path(project_id, record_id)
            if not path.exists():
                return None
            if path.is_symlink() or not path.is_file():
                raise AgentTaskStateError("execution evidence path is not a regular file")
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise AgentTaskStateError(
                    f"could not read execution evidence for {task_id!r}: {exc}"
                ) from exc
            if not isinstance(raw, Mapping):
                raise AgentTaskStateError("execution evidence must be a JSON object")
            if (
                raw.get("record_type") != _EXECUTION_EVIDENCE_RECORD_TYPE
                or raw.get("schema_version") != _EXECUTION_EVIDENCE_SCHEMA_VERSION
                or raw.get("record_id") != record_id
                or raw.get("project_id") != project_id
                or raw.get("plan_id") != plan_id
                or raw.get("task_id") != task_id
                or raw.get("skill_id") != skill_id
            ):
                raise AgentTaskStateError("execution evidence identity mismatch")
            created_at = raw.get("created_at")
            action_id = raw.get("action_id")
            if not isinstance(created_at, str) or not created_at:
                raise AgentTaskStateError("execution evidence created_at is invalid")
            if not isinstance(action_id, str) or not action_id:
                raise AgentTaskStateError("execution evidence action_id is invalid")
            try:
                policy = AgentPolicyProjection.from_dict(raw.get("policy"))
            except Exception as exc:
                raise AgentTaskStateError(
                    f"execution evidence policy is invalid: {exc}"
                ) from exc
            if policy.action_id != action_id:
                raise AgentTaskStateError("execution evidence policy action mismatch")
            return _ExecutionEvidence(
                record_id=record_id,
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                action_id=action_id,
                skill_id=skill_id,
                created_at=created_at,
                context_digest=_validate_context_digest(
                    raw.get("context_digest"),
                    field_name="execution evidence context digest",
                ),
                input_digest=_validate_digest(
                    raw.get("input_digest"),
                    field_name="execution evidence input digest",
                ),
                policy=policy,
            )


class _FinalCorrelatedProjectUnitOfWork(_CorrelatedProjectUnitOfWork):
    """Also recover Timeline identities emitted by production.accept_take."""

    @classmethod
    def _timeline_result_references(
        cls,
        record: Mapping[str, Any],
        command: str,
    ) -> dict[str, str]:
        if command != "production.accept_take":
            return super()._timeline_result_references(record, command)

        changes = record.get("changes")
        if not isinstance(changes, list):
            raise ProjectTransactionError(
                "correlated accept_take transaction changes are invalid"
            )
        timeline_changes = [
            change
            for change in changes
            if isinstance(change, Mapping)
            and change.get("path") == MAIN_TIMELINE_PATH
        ]
        if len(timeline_changes) != 1:
            raise ProjectTransactionError(
                "correlated accept_take transaction must contain one main timeline change"
            )
        change = timeline_changes[0]
        before = cls._timeline_from_snapshot(change.get("before"), label="before")
        after = cls._timeline_from_snapshot(change.get("after"), label="after")
        before_clips = {
            clip.clip_id: track.track_id
            for track in before.tracks
            for clip in track.clips
        }
        after_clips = {
            clip.clip_id: track.track_id
            for track in after.tracks
            for clip in track.clips
        }
        added = sorted(set(after_clips).difference(before_clips))
        if len(added) != 1:
            raise ProjectTransactionError(
                "correlated accept_take transaction does not identify one created clip"
            )
        clip_id = added[0]
        return {"track_id": after_clips[clip_id], "clip_id": clip_id}


class AgentTaskCoordinator(_RecoveryAgentTaskCoordinator):
    """Foreground Stage-16 executor with exact durable execution evidence."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        if task_store is None:
            task_store = _RecoveryAgentTaskStore(harness.project_store)
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )
        self._execution_evidence = _ExecutionEvidenceStore(self.project_store)
        self._transaction_evidence = _FinalCorrelatedProjectUnitOfWork(
            self.project_store
        )
        self.harness.production.uow = self._transaction_evidence
        self.harness.timeline.unit_of_work = self._transaction_evidence

    def _execution_policy(self, project_id: str, spec: Any, payload: Mapping[str, Any]) -> AgentPolicyProjection:
        model_id = payload.get("model_id")
        return self.harness.catalog.policy(
            project_id=project_id,
            action_id=spec.action_id,
            model_id=model_id if isinstance(model_id, str) else None,
        )

    def _recovered_success_trace(
        self,
        plan: Any,
        record: AgentTaskRecord,
        *,
        created_at: str,
        result_references: Mapping[str, str],
        extra_references: Sequence[str] = (),
        context_digest: str | None = None,
    ) -> AgentTraceRecord:
        trace = super()._recovered_success_trace(
            plan,
            record,
            created_at=created_at,
            result_references=result_references,
            extra_references=extra_references,
            context_digest=context_digest,
        )
        spec = plan.task(record.task_id)
        evidence = self._execution_evidence.get(
            project_id=record.project_id,
            plan_id=plan.plan_id,
            task_id=record.task_id,
            skill_id=spec.skill_id,
        )
        if evidence is None:
            return trace
        expected_input_digest = self._expected_input_digest(spec)
        if evidence.action_id != spec.action_id or evidence.input_digest != expected_input_digest:
            raise AgentTaskStateError(
                "durable execution evidence does not match the recovered Agent Task"
            )
        if evidence.context_digest != trace.context_digest:
            raise AgentTaskStateError(
                "durable execution policy/context evidence disagrees with recovered effect"
            )
        return replace(trace, policy=evidence.policy)

    def _committed_recovery_trace(
        self,
        plan: Any,
        record: AgentTaskRecord,
    ) -> AgentTraceRecord | None:
        recovered = self._transaction_recovery_trace(plan, record)
        if recovered is None:
            recovered = self._generation_recovery_trace(plan, record)
        return recovered

    def _execution_payload(
        self,
        spec: Any,
        runtime_inputs: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        payload = dict(spec.inputs)
        definition = self.harness.catalog.get(spec.action_id)
        if runtime_inputs is not None:
            if not isinstance(runtime_inputs, Mapping):
                raise AgentTaskStateError("runtime_inputs must be a mapping")
            unknown_runtime = set(runtime_inputs).difference({"authorization_token"})
            if unknown_runtime:
                raise AgentTaskStateError(
                    f"unsupported execution-only inputs: {sorted(unknown_runtime)!r}"
                )
            if runtime_inputs and "authorization_token" not in definition.input_fields:
                raise AgentTaskStateError(
                    f"action {spec.action_id!r} does not accept execution authorization"
                )
            if "authorization_token" in runtime_inputs:
                token = runtime_inputs["authorization_token"]
                if token is not None and not isinstance(token, str):
                    raise AgentTaskStateError("authorization_token must be text or null")
                payload["authorization_token"] = token
        if "authorization_token" in definition.input_fields and "authorization_token" not in payload:
            payload["authorization_token"] = None
        return payload

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        with self.project_store._lock, self.tasks.records.project_lock(project_id):
            plan = self.plans.get(project_id, plan_id)
            spec = plan.task(task_id)
            record = self.tasks.get(project_id, plan.plan_id, spec.task_id)
            if record.status is AgentTaskStatus.PLANNED:
                raise AgentTaskBlocked(
                    f"Agent Task {spec.task_id!r} is blocked by unsatisfied dependencies"
                )
            if record.status is not AgentTaskStatus.READY:
                raise AgentTaskStateError(
                    f"Agent Task {spec.task_id!r} is not runnable from {record.status.value!r}"
                )
            records = {
                item.task_id: item
                for item in self.tasks.list_by_plan(project_id, plan.plan_id)
            }
            unsatisfied = [
                dependency
                for dependency in spec.dependencies
                if records[dependency].status is not AgentTaskStatus.SUCCEEDED
            ]
            if unsatisfied:
                raise AgentTaskBlocked(
                    f"Agent Task {spec.task_id!r} has unsatisfied dependencies: {unsatisfied!r}"
                )

            payload = self._execution_payload(spec, runtime_inputs)
            correlation_id = _typed_correlation_reference(
                plan.plan_id,
                spec.task_id,
                spec.skill_id,
            )
            try:
                snapshot = self.harness.context.build(
                    project_id,
                    shot_id=spec.target_shot_id,
                )
            except Exception:
                with _execution_correlation(correlation_id):
                    return super().execute_task(
                        project_id=project_id,
                        plan_id=plan.plan_id,
                        task_id=spec.task_id,
                        runtime_inputs=runtime_inputs,
                    )

            expected_input_digest = self._expected_input_digest(spec)
            try:
                policy = self._execution_policy(project_id, spec, payload)
            except Exception:
                policy = None

            with (
                self._correlated_traces.correlate(
                    plan.plan_id,
                    spec.task_id,
                    spec.skill_id,
                    expected_input_digest=expected_input_digest,
                ),
                _execution_correlation(correlation_id),
                _execution_context(snapshot.digest),
            ):
                running = self.tasks.transition(record, AgentTaskStatus.RUNNING)
                if policy is not None:
                    try:
                        self._execution_evidence.append(
                            project_id=project_id,
                            plan_id=plan.plan_id,
                            task_id=spec.task_id,
                            action_id=spec.action_id,
                            skill_id=spec.skill_id,
                            context_digest=snapshot.digest,
                            input_digest=expected_input_digest,
                            policy=policy,
                        )
                    except Exception as exc:
                        self.tasks.transition(
                            running,
                            AgentTaskStatus.FAILED,
                            error=exc,
                        )
                        raise

                before_ids = {
                    trace.trace_id for trace in self.harness.traces.list(project_id)
                }
                try:
                    result = self.harness.execute(
                        project_id=project_id,
                        action_id=spec.action_id,
                        inputs=payload,
                        target_shot_id=spec.target_shot_id,
                    )
                except Exception as exc:
                    trace = self._trace_after(project_id, before_ids, spec.action_id)
                    if trace is not None:
                        self.tasks.transition(
                            running,
                            AgentTaskStatus.FAILED,
                            trace=trace,
                            error=exc,
                        )
                        raise
                    recovered = self._committed_recovery_trace(plan, running)
                    if recovered is not None:
                        # Canonical/cost-bearing work is already durable. Do not write a
                        # false FAILED terminal state merely because success-trace
                        # persistence failed. RUNNING remains the recoverable marker.
                        raise
                    self.tasks.transition(
                        running,
                        AgentTaskStatus.FAILED,
                        error=exc,
                    )
                    raise

                trace = self._trace_after(project_id, before_ids, spec.action_id)
                if trace is None:
                    error = AgentTaskStateError(
                        "AgentHarness execution completed without an inspectable Stage-15 trace"
                    )
                    recovered = self._committed_recovery_trace(plan, running)
                    if recovered is not None:
                        raise error
                    self.tasks.transition(
                        running,
                        AgentTaskStatus.FAILED,
                        error=error,
                    )
                    raise error

                self.tasks.transition(
                    running,
                    AgentTaskStatus.SUCCEEDED,
                    trace=trace,
                )
                self.tasks.promote_ready(plan)
                return result


__all__ = ["AgentPlanner", "AgentTaskCoordinator"]
