"""Final Stage-16 planning validation and committed-effect recovery.

This layer stays above the Stage-15 AgentHarness and existing UV mutation authorities.
It closes two review gaps without replaying work:

* durable plans reject missing required inputs for every Stage-15 catalog action;
* a foreground task that crashes after a canonical transaction/Job commit but before
  the Stage-15 success trace can reconstruct that trace from authoritative durable
  evidence rather than being marked failed or replayed.

Production/Timeline correlation is written into the existing ProjectUnitOfWork
prepared journal before canonical bytes change. Generation submission is already
idempotent and durable through GenerationJobManager, so recovery validates the exact
persisted Job request bound to the planned idempotency key.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

from uv_studio.generation.models import GenerationContract, GenerationValidationError
from uv_studio.projects.models import ProjectValidationError, validate_identifier
from uv_studio.projects.transactions import (
    HISTORY_TRANSACTIONS_ROOT,
    ProjectTransactionError,
    ProjectUnitOfWork,
)

from .models import AgentTraceRecord, AgentTraceStatus, portable_json, stable_digest
from .orchestration import (
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_runtime import (
    AgentPlanner as _RuntimeAgentPlanner,
    AgentSkillCatalog,
    AgentTaskCoordinator as _RuntimeAgentTaskCoordinator,
)

_CORRELATION_FIELD = "execution_correlation_id"
_EXECUTION_CORRELATION: ContextVar[str | None] = ContextVar(
    "uv_stage16_project_transaction_correlation",
    default=None,
)

_REQUIRED_ACTION_INPUTS: dict[str, tuple[str, ...]] = {
    "generation.submit": (
        "shot_id",
        "model_id",
        "inputs",
        "contract",
        "idempotency_key",
    ),
    "production.accept_take": ("take_id", "timeline_start_us", "duration_us"),
    "production.create_scene": ("scene_id", "title"),
    "production.create_shot": ("shot_id", "scene_id", "intent"),
    "production.register_take": ("take_id", "shot_id", "reference_id"),
    "timeline.add_clip": (
        "track_id",
        "reference_id",
        "timeline_start_us",
        "duration_us",
    ),
    "timeline.create_track": ("kind",),
    "timeline.move_clip": ("clip_id", "timeline_start_us"),
    "timeline.remove_clip": ("clip_id",),
    "timeline.trim_clip": ("clip_id", "source_start_us", "duration_us"),
}


def _typed_correlation_reference(
    plan_id: str,
    task_id: str,
    skill_id: str | None,
) -> str:
    digest = stable_digest(
        {
            "record_type": "agent_task_correlation",
            "plan_id": plan_id,
            "task_id": task_id,
            "skill_id": skill_id,
        }
    )
    return f"agent_corr_{digest[:32]}"


@contextmanager
def _execution_correlation(correlation_id: str) -> Iterator[None]:
    try:
        normalized = validate_identifier(
            correlation_id,
            field_name="execution correlation_id",
        )
    except ProjectValidationError as exc:
        raise AgentTaskStateError(str(exc)) from exc
    token = _EXECUTION_CORRELATION.set(normalized)
    try:
        yield
    finally:
        _EXECUTION_CORRELATION.reset(token)


@dataclass(frozen=True)
class _CommittedTransactionEvidence:
    transaction_id: str
    command: str
    created_at: str


class _CorrelatedProjectUnitOfWork(ProjectUnitOfWork):
    """ProjectUnitOfWork that binds one execution correlation before its commit point."""

    def _execute_prepared(
        self,
        project_id: str,
        record_path: Any,
        record: dict[str, Any],
        changes: list[dict[str, Any]],
        history_before: Any,
        history_after: Any,
    ) -> None:
        correlation_id = _EXECUTION_CORRELATION.get()
        prepared = dict(record)
        if correlation_id is not None:
            prepared[_CORRELATION_FIELD] = correlation_id
        super()._execute_prepared(
            project_id,
            record_path,
            prepared,
            changes,
            history_before,
            history_after,
        )

    def committed_by_correlation(
        self,
        project_id: str,
        correlation_id: str,
    ) -> _CommittedTransactionEvidence | None:
        """Return the unique committed transaction carrying this opaque correlation."""

        try:
            normalized = validate_identifier(
                correlation_id,
                field_name="execution correlation_id",
            )
        except ProjectValidationError as exc:
            raise ProjectTransactionError(str(exc)) from exc

        with self.project_store._lock:
            self._ensure_history_layout(project_id)
            # A prepared operation is not proof of a mutation. The canonical transaction
            # authority first rolls every interrupted prepared record back, then this
            # lookup considers committed records only.
            self._recover_prepared_operations(project_id)
            self.project_store.load_project(project_id)

            matches: list[_CommittedTransactionEvidence] = []
            transaction_root = self._history_dir(
                project_id,
                HISTORY_TRANSACTIONS_ROOT,
            )
            for path in sorted(transaction_root.glob("*.json"), key=lambda item: item.name):
                record = self._load_record(path)
                if record.get("phase") != "committed":
                    continue
                if record.get(_CORRELATION_FIELD) != normalized:
                    continue
                raw_transaction_id = record.get("transaction_id")
                try:
                    transaction_id = validate_identifier(
                        raw_transaction_id,
                        field_name="transaction_id",
                    )
                except ProjectValidationError as exc:
                    raise ProjectTransactionError(
                        f"correlated transaction {path.name!r} has invalid identity"
                    ) from exc
                if transaction_id != path.stem or record.get("record_id") != transaction_id:
                    raise ProjectTransactionError(
                        "correlated transaction record identity mismatch"
                    )
                command = record.get("command")
                created_at = record.get("created_at")
                if not isinstance(command, str) or not command.strip():
                    raise ProjectTransactionError(
                        "correlated transaction command is invalid"
                    )
                if not isinstance(created_at, str) or not created_at:
                    raise ProjectTransactionError(
                        "correlated transaction created_at is invalid"
                    )
                matches.append(
                    _CommittedTransactionEvidence(
                        transaction_id=transaction_id,
                        command=command.strip(),
                        created_at=created_at,
                    )
                )

            if len(matches) > 1:
                raise ProjectTransactionError(
                    f"execution correlation {normalized!r} matched multiple committed transactions"
                )
            return matches[0] if matches else None


class AgentPlanner(_RuntimeAgentPlanner):
    """Stage-16 Planner with explicit required-input validation before persistence."""

    def build(
        self,
        *,
        project_id: str,
        goal: str,
        proposals: Sequence[AgentPlanStepProposal],
        target_shot_id: str | None = None,
        canonical_references: Sequence[str] = (),
        plan_id: str | None = None,
    ) -> AgentPlanRecord:
        plan = super().build(
            project_id=project_id,
            goal=goal,
            proposals=proposals,
            target_shot_id=target_shot_id,
            canonical_references=canonical_references,
            plan_id=plan_id,
        )
        for spec in plan.tasks:
            required = _REQUIRED_ACTION_INPUTS.get(spec.action_id)
            if required is None:
                raise AgentPlanningError(
                    f"required-input contract is not defined for action {spec.action_id!r}"
                )
            missing = [
                field_name
                for field_name in required
                if field_name not in spec.inputs or spec.inputs[field_name] is None
            ]
            if missing:
                raise AgentPlanningError(
                    f"action {spec.action_id!r} is missing required inputs: {missing!r}"
                )
            if spec.action_id == "generation.submit":
                if not isinstance(spec.inputs["inputs"], Mapping):
                    raise AgentPlanningError(
                        "generation.submit inputs must be a JSON object"
                    )
                contract = spec.inputs["contract"]
                if not isinstance(contract, Mapping):
                    raise AgentPlanningError(
                        "generation.submit contract must be a JSON object"
                    )
                try:
                    GenerationContract.from_dict(contract)
                    validate_identifier(
                        spec.inputs["idempotency_key"],
                        field_name="idempotency_key",
                    )
                except (GenerationValidationError, ProjectValidationError) as exc:
                    raise AgentPlanningError(
                        f"generation.submit required inputs are invalid: {exc}"
                    ) from exc
        return plan


class AgentTaskCoordinator(_RuntimeAgentTaskCoordinator):
    """Recover post-commit/pre-trace crashes from canonical transaction or Job evidence."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        if planner is None:
            planner = AgentPlanner(
                harness,
                skills=AgentSkillCatalog(harness.catalog),
            )
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )
        self._transaction_evidence = _CorrelatedProjectUnitOfWork(
            self.project_store
        )
        # The same canonical Production/Timeline services remain authoritative; only
        # their existing UoW instance is replaced by a subclass that enriches the
        # prepared journal with execution correlation before any canonical write.
        self.harness.production.uow = self._transaction_evidence
        self.harness.timeline.unit_of_work = self._transaction_evidence

    @staticmethod
    def _known_input_references(spec: Any) -> tuple[str, ...]:
        values: list[str] = []
        for field_name in (
            "scene_id",
            "shot_id",
            "take_id",
            "reference_id",
            "track_id",
            "clip_id",
        ):
            value = spec.inputs.get(field_name)
            if isinstance(value, str) and value:
                values.append(value)
        return tuple(dict.fromkeys(values))

    def _recovered_success_trace(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
        *,
        created_at: str,
        result_references: Mapping[str, str],
        extra_references: Sequence[str] = (),
    ) -> AgentTraceRecord:
        spec = plan.task(record.task_id)
        typed_reference = _typed_correlation_reference(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        )
        references = tuple(
            dict.fromkeys(
                (
                    record.project_id,
                    *(self._known_input_references(spec)),
                    *extra_references,
                    *result_references.values(),
                    typed_reference,
                )
            )
        )
        return AgentTraceRecord(
            trace_id=f"agent_trace_{uuid.uuid4().hex}",
            project_id=record.project_id,
            created_at=created_at,
            context_digest=plan.context_digest,
            action_id=spec.action_id,
            input_digest=self._expected_input_digest(spec),
            canonical_references=references,
            policy=spec.policy,
            status=AgentTraceStatus.SUCCEEDED,
            result_references=dict(result_references),
        )

    def _transaction_recovery_trace(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTraceRecord | None:
        spec = plan.task(record.task_id)
        if spec.action_id == "generation.submit":
            return None
        correlation_id = _typed_correlation_reference(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        )
        try:
            evidence = self._transaction_evidence.committed_by_correlation(
                record.project_id,
                correlation_id,
            )
        except ProjectTransactionError as exc:
            raise AgentTaskStateError(
                f"could not inspect correlated project transaction: {exc}"
            ) from exc
        if evidence is None:
            return None
        if evidence.command != spec.action_id:
            raise AgentTaskStateError(
                "correlated committed transaction action does not match durable Agent Task"
            )
        created_at = evidence.created_at
        if record.started_at is not None and created_at < record.started_at:
            created_at = record.started_at
        return self._recovered_success_trace(
            plan,
            record,
            created_at=created_at,
            result_references={"transaction_id": evidence.transaction_id},
        )

    def _generation_recovery_trace(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTraceRecord | None:
        spec = plan.task(record.task_id)
        if spec.action_id != "generation.submit":
            return None
        idempotency_key = spec.inputs.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise AgentTaskStateError(
                "durable generation task lost its required idempotency key"
            )
        matches = [
            job
            for job in self.harness.jobs.list(record.project_id)
            if job.idempotency_key == idempotency_key
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise AgentTaskStateError(
                "generation idempotency key matched multiple durable Jobs"
            )
        job = matches[0]

        contract_raw = spec.inputs.get("contract")
        request_inputs = spec.inputs.get("inputs")
        if not isinstance(contract_raw, Mapping) or not isinstance(request_inputs, Mapping):
            raise AgentTaskStateError(
                "durable generation task lost normalized request semantics"
            )
        try:
            expected_contract = GenerationContract.from_dict(contract_raw).to_dict()
        except GenerationValidationError as exc:
            raise AgentTaskStateError(
                f"durable generation contract is invalid: {exc}"
            ) from exc
        expected_inputs = portable_json(
            dict(request_inputs),
            field_name="Agent generation recovery inputs",
        )
        request = job.request
        exact_request = (
            request.get("project_id") == record.project_id
            and request.get("shot_id") == spec.inputs.get("shot_id")
            and request.get("model_id") == spec.inputs.get("model_id")
            and request.get("inputs") == expected_inputs
            and request.get("generation_contract") == expected_contract
        )
        if not exact_request:
            raise AgentTaskStateError(
                "generation idempotency key is bound to request semantics that do not match the Agent Task"
            )

        created_at = record.started_at or job.created_at
        result_references = {"job_id": job.job_id}
        attempt = job.current_attempt
        if attempt is not None:
            result_references["attempt_id"] = attempt.attempt_id
            if attempt.output_reference_id is not None:
                result_references["output_reference_id"] = attempt.output_reference_id
            if attempt.take_id is not None:
                result_references["take_id"] = attempt.take_id
        return self._recovered_success_trace(
            plan,
            record,
            created_at=created_at,
            result_references=result_references,
            extra_references=(
                spec.inputs["shot_id"],
                job.job_id,
            ),
        )

    def _reconcile_running(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTaskRecord:
        trace = self._correlated_trace_for(plan, record)
        if trace is not None:
            return super()._reconcile_running(plan, record)

        recovered = self._transaction_recovery_trace(plan, record)
        if recovered is None:
            recovered = self._generation_recovery_trace(plan, record)
        if recovered is not None:
            # Append evidence first. If the process stops after this append but before
            # the task transition, the next reopen consumes this exact correlated trace.
            self.harness.traces.append(recovered)
            return self.tasks.transition(
                record,
                AgentTaskStatus.SUCCEEDED,
                trace=recovered,
            )
        return super()._reconcile_running(plan, record)

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        plan = self.plans.get(project_id, plan_id)
        spec = plan.task(task_id)
        correlation_id = _typed_correlation_reference(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        )
        with _execution_correlation(correlation_id):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan.plan_id,
                task_id=spec.task_id,
                runtime_inputs=runtime_inputs,
            )
