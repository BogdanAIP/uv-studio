"""External capability execution intent, cost snapshot and one-shot authorization.

This module is provider-neutral. A registered/discovered offer is not permission
to invoke it. Grants are ephemeral machine-runtime state and are never portable
project data.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .models import CapabilityOffer, CostClass, LocalityClass

AUTHORIZATION_TTL_SECONDS = 300
_MAX_INTENT_JSON_BYTES = 512 * 1024


class ExternalExecutionError(RuntimeError):
    pass


class ExecutionConsentRequired(ExternalExecutionError):
    pass


class ExecutionAuthorizationRejected(ExternalExecutionError):
    pass


class ExecutionAuthorizationExpired(ExecutionAuthorizationRejected):
    pass


class ExecutionAuthorizationUsed(ExecutionAuthorizationRejected):
    pass


class CostEstimateState(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    KNOWN = "known"
    BOUNDED = "bounded"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ExecutionCostEstimate:
    state: CostEstimateState
    currency: str | None = None
    amount: float | None = None
    upper_bound: float | None = None
    source: str = "offer_metadata"

    def __post_init__(self) -> None:
        if self.state is CostEstimateState.NOT_APPLICABLE:
            if self.currency is not None or self.amount is not None or self.upper_bound is not None:
                raise ValueError("not_applicable cost estimate cannot contain monetary values")
        if self.state is CostEstimateState.UNKNOWN:
            if self.amount is not None or self.upper_bound is not None:
                raise ValueError("unknown cost estimate cannot contain monetary values")
        if self.state is CostEstimateState.KNOWN:
            if not self.currency or self.amount is None or self.amount < 0:
                raise ValueError("known cost estimate requires non-negative amount and currency")
        if self.state is CostEstimateState.BOUNDED:
            if not self.currency or self.upper_bound is None or self.upper_bound < 0:
                raise ValueError("bounded cost estimate requires non-negative upper_bound and currency")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "currency": self.currency,
            "amount": self.amount,
            "upper_bound": self.upper_bound,
            "source": self.source,
        }


@dataclass(frozen=True)
class ExecutionIntent:
    project_id: str
    capability_id: str
    offer_id: str
    input_digest: str
    locality: LocalityClass
    cost_class: CostClass
    cost_estimate: ExecutionCostEstimate

    @property
    def intent_digest(self) -> str:
        return _sha256_json({
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "input_digest": self.input_digest,
            "locality": self.locality.value,
            "cost_class": self.cost_class.value,
            "cost_estimate": self.cost_estimate.to_dict(),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "input_digest": self.input_digest,
            "intent_digest": self.intent_digest,
            "locality": self.locality.value,
            "cost_class": self.cost_class.value,
            "cost_estimate": self.cost_estimate.to_dict(),
        }


@dataclass(frozen=True)
class PreparedExternalExecution:
    intent: ExecutionIntent
    remote_consent_required: bool
    cost_consent_required: bool
    unknown_cost_ack_required: bool

    @property
    def authorization_required(self) -> bool:
        return self.remote_consent_required or self.cost_consent_required

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "authorization_required": self.authorization_required,
            "remote_consent_required": self.remote_consent_required,
            "cost_consent_required": self.cost_consent_required,
            "unknown_cost_ack_required": self.unknown_cost_ack_required,
        }


@dataclass(frozen=True)
class ExecutionAuthorizationGrant:
    grant_id: str
    token: str
    intent_digest: str
    project_id: str
    capability_id: str
    offer_id: str
    expires_at_epoch: float

    def public_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "authorization_token": self.token,
            "intent_digest": self.intent_digest,
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "expires_at_epoch": self.expires_at_epoch,
            "one_shot": True,
        }


@dataclass
class _StoredGrant:
    grant: ExecutionAuthorizationGrant
    used: bool = False


def _sha256_json(value: Any) -> str:
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ExternalExecutionError("execution input must be JSON serializable") from exc
    if len(encoded) > _MAX_INTENT_JSON_BYTES:
        raise ExternalExecutionError(f"execution intent input exceeds {_MAX_INTENT_JSON_BYTES} bytes")
    return hashlib.sha256(encoded).hexdigest()


def input_digest(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        raise ExternalExecutionError("execution input must be an object")
    return _sha256_json(dict(payload))


def cost_estimate_for_offer(offer: CapabilityOffer) -> ExecutionCostEstimate:
    if offer.cost_class is CostClass.FREE:
        return ExecutionCostEstimate(CostEstimateState.NOT_APPLICABLE)
    return ExecutionCostEstimate(CostEstimateState.UNKNOWN)


def prepare_external_execution(
    *, project_id: str, offer: CapabilityOffer, payload: Mapping[str, Any],
    cost_estimate: ExecutionCostEstimate | None = None,
) -> PreparedExternalExecution:
    estimate = cost_estimate or cost_estimate_for_offer(offer)
    intent = ExecutionIntent(
        project_id=project_id,
        capability_id=offer.capability_id,
        offer_id=offer.offer_id,
        input_digest=input_digest(payload),
        locality=offer.locality,
        cost_class=offer.cost_class,
        cost_estimate=estimate,
    )
    remote_required = offer.locality is not LocalityClass.LOCAL
    cost_required = offer.cost_class is not CostClass.FREE
    return PreparedExternalExecution(
        intent=intent,
        remote_consent_required=remote_required,
        cost_consent_required=cost_required,
        unknown_cost_ack_required=(cost_required and estimate.state is CostEstimateState.UNKNOWN),
    )


class ExecutionAuthorizationStore:
    """Thread-safe in-memory one-shot grant store."""

    def __init__(self, *, ttl_seconds: int = AUTHORIZATION_TTL_SECONDS) -> None:
        if ttl_seconds < 1 or ttl_seconds > 3600:
            raise ValueError("authorization TTL must be between 1 and 3600 seconds")
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._grants: dict[str, _StoredGrant] = {}

    def authorize(
        self, prepared: PreparedExternalExecution, *, confirm_remote: bool,
        confirm_cost: bool, acknowledge_unknown_cost: bool, now: float | None = None,
    ) -> ExecutionAuthorizationGrant:
        if prepared.remote_consent_required and not confirm_remote:
            raise ExecutionConsentRequired("remote execution confirmation is required")
        if prepared.cost_consent_required and not confirm_cost:
            raise ExecutionConsentRequired("paid-capable execution confirmation is required")
        if prepared.unknown_cost_ack_required and not acknowledge_unknown_cost:
            raise ExecutionConsentRequired("unknown execution cost must be acknowledged explicitly")
        current = time.time() if now is None else float(now)
        grant = ExecutionAuthorizationGrant(
            grant_id=f"grant_{secrets.token_hex(16)}",
            token=secrets.token_urlsafe(32),
            intent_digest=prepared.intent.intent_digest,
            project_id=prepared.intent.project_id,
            capability_id=prepared.intent.capability_id,
            offer_id=prepared.intent.offer_id,
            expires_at_epoch=current + self.ttl_seconds,
        )
        with self._lock:
            self._grants[grant.token] = _StoredGrant(grant=grant)
        return grant

    def consume(
        self, token: str, *, expected_intent_digest: str, now: float | None = None,
    ) -> ExecutionAuthorizationGrant:
        if not isinstance(token, str) or not token:
            raise ExecutionAuthorizationRejected("authorization token is required")
        current = time.time() if now is None else float(now)
        with self._lock:
            stored = self._grants.get(token)
            if stored is None:
                raise ExecutionAuthorizationRejected("authorization token is unknown")
            grant = stored.grant
            if stored.used:
                raise ExecutionAuthorizationUsed("authorization token has already been used")
            if current > grant.expires_at_epoch:
                stored.used = True
                raise ExecutionAuthorizationExpired("authorization token has expired")
            if not secrets.compare_digest(grant.intent_digest, expected_intent_digest):
                raise ExecutionAuthorizationRejected(
                    "authorization token does not match the current execution intent"
                )
            stored.used = True
            return grant
