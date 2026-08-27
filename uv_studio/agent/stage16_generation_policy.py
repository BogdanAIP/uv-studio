"""Bind Stage-16 frozen Agent policy to the exact Generation preparation.

The review-consistency layer already freezes AgentHarness policy lookup for one
foreground dispatch. This refinement also freezes GenerationService.prepare()
for generation.submit so Capability Registry changes cannot make the queued Job
use different locality/cost/effects/authorization facts than durable evidence.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Mapping

from uv_studio.capabilities.models import OfferAvailability
from uv_studio.generation.jobs import generation_request_digest
from uv_studio.generation.models import GenerationContract
from uv_studio.generation.service import GenerationService, GenerationSubmissionPreparation

from .models import AgentPolicyProjection
from .orchestration import AgentTaskStateError
from .stage16_review_consistency import (
    AgentPlanner,
    AgentTaskCoordinator as _ReviewConsistencyAgentTaskCoordinator,
    _ExecutionPolicyCatalog,
)


class _GenerationPolicyBoundService(GenerationService):
    """Use one verified preparation while a frozen Agent policy is bound."""

    def __init__(
        self,
        base: GenerationService,
        policy_catalog: _ExecutionPolicyCatalog,
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
        self._bound_preparation: ContextVar[
            GenerationSubmissionPreparation | None
        ] = ContextVar(
            f"uv_agent_generation_preparation_{id(self)}",
            default=None,
        )

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
        current = harness.generation
        if not isinstance(current, _GenerationPolicyBoundService):
            harness.generation = _GenerationPolicyBoundService(
                current,
                self._execution_policy_catalog,
            )


__all__ = ["AgentPlanner", "AgentTaskCoordinator"]
