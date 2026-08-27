"""Bind Stage-16 frozen Agent policy to the exact Generation preparation.

The review-consistency layer already freezes AgentHarness policy lookup for one
foreground dispatch. This refinement also freezes GenerationService.prepare()
for generation.submit so Capability Registry changes cannot make the queued Job
use different locality/cost/effects/authorization facts than durable evidence.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from uv_studio.capabilities.models import OfferAvailability
from uv_studio.generation.jobs import generation_request_digest
from uv_studio.generation.models import GenerationContract
from uv_studio.generation.service import GenerationService, GenerationSubmissionPreparation
from uv_studio.projects.task_records import ProjectTaskRecordConflict, ProjectTaskRecordStore

from .models import AgentPolicyProjection, portable_json, stable_digest
from .orchestration import AgentTaskStateError
from .stage16_review_consistency import (
    AgentPlanner,
    AgentTaskCoordinator as _ReviewConsistencyAgentTaskCoordinator,
    _ExecutionPolicyCatalog,
)


_GENERATION_PREPARATION_EVIDENCE_RECORD_TYPE = "agent_generation_preparation_evidence"
_GENERATION_PREPARATION_EVIDENCE_SCHEMA_VERSION = 1


def _generation_preparation_evidence_id(plan_id: str, task_id: str) -> str:
    digest = stable_digest(
        {
            "record_type": _GENERATION_PREPARATION_EVIDENCE_RECORD_TYPE,
            "plan_id": plan_id,
            "task_id": task_id,
        }
    )
    return f"agent_genprep_{digest[:32]}"


def _generation_execution_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise AgentTaskStateError("generation preparation lost execution mapping")
    expected = ("capability_id", "offer_id", "adapter_id")
    if set(value) != set(expected):
        raise AgentTaskStateError("generation execution mapping fields are invalid")
    mapping: dict[str, str] = {}
    for field_name in expected:
        field_value = value.get(field_name)
        if not isinstance(field_value, str) or not field_value:
            raise AgentTaskStateError(
                f"generation execution mapping {field_name} is invalid"
            )
        mapping[field_name] = field_value
    return mapping


def _generation_request_digest_value(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AgentTaskStateError("generation preparation request_digest is invalid")
    return value


@dataclass(frozen=True)
class _GenerationPreparationEvidence:
    record_id: str
    project_id: str
    plan_id: str
    task_id: str
    model_id: str
    request_digest: str
    execution_mapping: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": _GENERATION_PREPARATION_EVIDENCE_RECORD_TYPE,
            "schema_version": _GENERATION_PREPARATION_EVIDENCE_SCHEMA_VERSION,
            "record_id": self.record_id,
            "project_id": self.project_id,
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "model_id": self.model_id,
            "request_digest": self.request_digest,
            "execution_mapping": dict(self.execution_mapping),
        }


class _GenerationPreparationEvidenceStore:
    """Append-only proof of the exact Generation preparation used by one Agent Task."""

    def __init__(self, project_store: Any) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def append(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        preparation: GenerationSubmissionPreparation,
    ) -> _GenerationPreparationEvidence:
        record_id = _generation_preparation_evidence_id(plan_id, task_id)
        evidence = _GenerationPreparationEvidence(
            record_id=record_id,
            project_id=project_id,
            plan_id=plan_id,
            task_id=task_id,
            model_id=preparation.model.model_id,
            request_digest=_generation_request_digest_value(preparation.request_digest),
            execution_mapping=_generation_execution_mapping(
                preparation.request.get("execution_mapping")
            ),
        )
        payload = portable_json(
            evidence.to_dict(),
            field_name="Agent generation preparation evidence",
        )
        try:
            self.records.create_if_absent(project_id, record_id, payload)
        except ProjectTaskRecordConflict as exc:
            raise AgentTaskStateError(
                f"generation preparation evidence already exists for Agent Task {task_id!r}"
            ) from exc
        return evidence

    def get(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
    ) -> _GenerationPreparationEvidence | None:
        record_id = _generation_preparation_evidence_id(plan_id, task_id)
        with self.project_store._lock, self.records.project_lock(project_id):
            path = self.records.path(project_id, record_id)
            if not path.exists():
                return None
            if path.is_symlink() or not path.is_file():
                raise AgentTaskStateError(
                    "generation preparation evidence path is not a regular file"
                )
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise AgentTaskStateError(
                    f"could not read generation preparation evidence for {task_id!r}: {exc}"
                ) from exc
            if not isinstance(raw, Mapping):
                raise AgentTaskStateError(
                    "generation preparation evidence must be a JSON object"
                )
            if (
                raw.get("record_type") != _GENERATION_PREPARATION_EVIDENCE_RECORD_TYPE
                or raw.get("schema_version") != _GENERATION_PREPARATION_EVIDENCE_SCHEMA_VERSION
                or raw.get("record_id") != record_id
                or raw.get("project_id") != project_id
                or raw.get("plan_id") != plan_id
                or raw.get("task_id") != task_id
            ):
                raise AgentTaskStateError(
                    "generation preparation evidence identity mismatch"
                )
            model_id = raw.get("model_id")
            if not isinstance(model_id, str) or not model_id:
                raise AgentTaskStateError(
                    "generation preparation evidence model_id is invalid"
                )
            return _GenerationPreparationEvidence(
                record_id=record_id,
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                model_id=model_id,
                request_digest=_generation_request_digest_value(
                    raw.get("request_digest")
                ),
                execution_mapping=_generation_execution_mapping(
                    raw.get("execution_mapping")
                ),
            )


class _GenerationPolicyBoundService(GenerationService):
    """Use one verified preparation while a frozen Agent policy is bound."""

    def __init__(
        self,
        base: GenerationService,
        policy_catalog: _ExecutionPolicyCatalog,
        preparation_evidence: _GenerationPreparationEvidenceStore,
    ) -> None:
        # Preserve the exact existing GenerationService authorities instead of
        # constructing a second Job/Production/transaction stack.
        self.project_store = base.project_store
        self.model_registry = base.model_registry
        self.authorizations = base.authorizations
        self.executor = base.executor
        self.jobs = base.jobs
        self.production = base.production
        self.transactions = base.transactions
        self._policy_catalog = policy_catalog
        self._preparation_evidence = preparation_evidence
        self._bound_preparation: ContextVar[
            GenerationSubmissionPreparation | None
        ] = ContextVar(
            f"uv_agent_generation_preparation_{id(self)}",
            default=None,
        )
        self._bound_agent_task: ContextVar[tuple[str, str, str] | None] = ContextVar(
            f"uv_agent_generation_task_{id(self)}",
            default=None,
        )

    @contextmanager
    def bind_agent_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
    ) -> Iterator[None]:
        token = self._bound_agent_task.set((project_id, plan_id, task_id))
        try:
            yield
        finally:
            self._bound_agent_task.reset(token)

    def _frozen_policy(
        self,
        *,
        project_id: str,
        model_id: str,
    ) -> AgentPolicyProjection | None:
        bound = self._policy_catalog._bound.get()
        if bound is None:
            return None
        bound_project, bound_action, bound_model, policy = bound
        if (
            bound_project == project_id
            and bound_action == "generation.submit"
            and bound_model == model_id
        ):
            return policy
        return None

    def _validate_preparation(
        self,
        *,
        project_id: str,
        policy: AgentPolicyProjection,
        preparation: GenerationSubmissionPreparation,
    ) -> None:
        try:
            effects = self.model_registry.capability_registry.effects_for_offer(
                preparation.offer.offer_id
            )
        except Exception as exc:
            raise AgentTaskStateError(
                f"could not verify generation preparation against frozen policy: {exc}"
            ) from exc

        execution = preparation.execution
        consent = tuple(item.value for item in execution.consent_required)
        matches = (
            policy.action_id == "generation.submit"
            and policy.model_id == preparation.model.model_id
            and policy.capability_id == preparation.model.capability_id
            and policy.offer_id == preparation.offer.offer_id
            and policy.available
            == (preparation.offer.availability is OfferAvailability.AVAILABLE)
            and policy.reason == preparation.offer.reason
            and policy.locality == execution.locality.value
            and policy.cost_class == execution.cost_class.value
            and policy.authorization_required == execution.authorization_required
            and policy.consent_required == consent
            and policy.effects == effects
            and execution.intent.project_id == project_id
            and execution.intent.capability_id == preparation.offer.capability_id
            and execution.intent.offer_id == preparation.offer.offer_id
        )
        if not matches:
            raise AgentTaskStateError(
                "generation preparation no longer matches the frozen Agent execution policy"
            )

    @staticmethod
    def _matches_bound_request(
        preparation: GenerationSubmissionPreparation,
        *,
        project_id: str,
        shot_id: str,
        model_id: str,
        inputs: Mapping[str, Any],
        contract: GenerationContract,
    ) -> bool:
        try:
            digest, _ = generation_request_digest(
                project_id=project_id,
                shot_id=shot_id,
                model_id=model_id,
                capability_id=preparation.model.capability_id,
                offer_id=preparation.offer.offer_id,
                adapter_id=preparation.offer.adapter_id,
                inputs=inputs,
                contract=contract,
            )
        except Exception:
            return False
        return digest == preparation.request_digest

    def prepare(
        self,
        *,
        project_id: str,
        shot_id: str,
        model_id: str,
        inputs: Mapping[str, Any],
        contract: GenerationContract,
    ) -> GenerationSubmissionPreparation:
        bound = self._bound_preparation.get()
        if bound is not None:
            if not self._matches_bound_request(
                bound,
                project_id=project_id,
                shot_id=shot_id,
                model_id=model_id,
                inputs=inputs,
                contract=contract,
            ):
                raise AgentTaskStateError(
                    "bound generation preparation does not match the dispatch request"
                )
            return bound
        return GenerationService.prepare(
            self,
            project_id=project_id,
            shot_id=shot_id,
            model_id=model_id,
            inputs=inputs,
            contract=contract,
        )

    def submit(
        self,
        *,
        project_id: str,
        shot_id: str,
        model_id: str,
        inputs: Mapping[str, Any],
        contract: GenerationContract,
        idempotency_key: str,
        authorization_token: str | None,
    ):
        policy = self._frozen_policy(project_id=project_id, model_id=model_id)
        if policy is None:
            return GenerationService.submit(
                self,
                project_id=project_id,
                shot_id=shot_id,
                model_id=model_id,
                inputs=inputs,
                contract=contract,
                idempotency_key=idempotency_key,
                authorization_token=authorization_token,
            )

        # Resolve the real Generation preparation exactly once after the Agent
        # policy snapshot was captured. If the registry changed in between, fail
        # before D-017 consumption or durable Job creation.
        preparation = GenerationService.prepare(
            self,
            project_id=project_id,
            shot_id=shot_id,
            model_id=model_id,
            inputs=inputs,
            contract=contract,
        )
        self._validate_preparation(
            project_id=project_id,
            policy=policy,
            preparation=preparation,
        )

        bound_task = self._bound_agent_task.get()
        if bound_task is None:
            raise AgentTaskStateError(
                "frozen generation dispatch lost its Agent Task binding"
            )
        bound_project, plan_id, task_id = bound_task
        if bound_project != project_id:
            raise AgentTaskStateError(
                "generation preparation Agent Task project binding mismatch"
            )
        # Persist the exact mapping/digest before D-017 consumption and before Job
        # idempotency lookup/commit. Recovery may only reuse a Job if this proof exists.
        self._preparation_evidence.append(
            project_id=project_id,
            plan_id=plan_id,
            task_id=task_id,
            preparation=preparation,
        )

        token = self._bound_preparation.set(preparation)
        try:
            # GenerationService.submit() calls self.prepare(); the override above
            # returns this exact verified object rather than re-reading registry.
            return GenerationService.submit(
                self,
                project_id=project_id,
                shot_id=shot_id,
                model_id=model_id,
                inputs=inputs,
                contract=contract,
                idempotency_key=idempotency_key,
                authorization_token=authorization_token,
            )
        finally:
            self._bound_preparation.reset(token)


class AgentTaskCoordinator(_ReviewConsistencyAgentTaskCoordinator):
    """Final Stage-16 coordinator with generation preparation/policy consistency."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )
        self._generation_preparation_evidence = _GenerationPreparationEvidenceStore(
            self.project_store
        )
        current = harness.generation
        if isinstance(current, _GenerationPolicyBoundService):
            self._generation_service = current
            self._generation_preparation_evidence = current._preparation_evidence
        else:
            self._generation_service = _GenerationPolicyBoundService(
                current,
                self._execution_policy_catalog,
                self._generation_preparation_evidence,
            )
            harness.generation = self._generation_service

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        with self._generation_service.bind_agent_task(
            project_id=project_id,
            plan_id=plan_id,
            task_id=task_id,
        ):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                runtime_inputs=runtime_inputs,
            )

    def _generation_recovery_trace(self, plan: Any, record: Any):
        spec = plan.task(record.task_id)
        if spec.action_id != "generation.submit":
            return super()._generation_recovery_trace(plan, record)

        preparation_evidence = self._generation_preparation_evidence.get(
            project_id=record.project_id,
            plan_id=plan.plan_id,
            task_id=record.task_id,
        )
        # A Job cannot belong to this Agent Task unless the exact preparation was
        # persisted before the existing GenerationService idempotency/commit path.
        if preparation_evidence is None:
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
        mapping = job.request.get("execution_mapping")
        exact_preparation = (
            job.request_digest == preparation_evidence.request_digest
            and job.request.get("model_id") == preparation_evidence.model_id
            and isinstance(mapping, Mapping)
            and dict(mapping) == preparation_evidence.execution_mapping
        )
        if not exact_preparation:
            # This is the same idempotency conflict GenerationService.submit would
            # reject. Do not attribute an older Job to a newly captured execution.
            return None

        return super()._generation_recovery_trace(plan, record)


__all__ = ["AgentPlanner", "AgentTaskCoordinator"]
