"""Execution authorization and cost-awareness contracts.

Selection answers *which* offer would run. This module separately answers
whether that selected offer may run for this exact project/input. Grants are
intentionally in-memory, short-lived and one-shot so portable projects never
contain reusable permission to contact or spend money with an external service.
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
from .selection import SelectionPolicy

EXECUTION_AUTHORIZATION_SCHEMA_VERSION = 1
DEFAULT_AUTHORIZATION_TTL_SECONDS = 300.0


class ExecutionAuthorizationError(RuntimeError):
    """Base class for authorization failures."""


class ExecutionConsentRequired(ExecutionAuthorizationError):
    """The selected offer requires explicit acknowledgement before execution."""


class ExecutionAuthorizationInvalid(ExecutionAuthorizationError):
    """A one-shot grant is missing, expired, consumed, or bound to another intent."""


class InvalidExecutionInput(ExecutionAuthorizationError):
    """Input cannot be normalized into the authorization digest."""


class CostEstimateState(str, Enum):
    KNOWN = "known"
    BOUNDED = "bounded"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ConsentScope(str, Enum):
    REMOTE_EXECUTION = "remote_execution"
    EXTERNAL_COST = "external_cost"
    UNKNOWN_COST = "unknown_cost"


@dataclass(frozen=True)
class ExecutionCostEstimate:
    state: CostEstimateState
    amount: float | None = None
    upper_bound: float | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, CostEstimateState):
            object.__setattr__(self, "state", CostEstimateState(self.state))
        if self.state in {CostEstimateState.UNKNOWN, CostEstimateState.NOT_APPLICABLE}:
            if self.amount is not None or self.upper_bound is not None or self.currency is not None:
                raise ValueError(f"{self.state.value} cost estimates cannot contain price values")
            return
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise ValueError("known or bounded cost estimates require a currency")
        object.__setattr__(self, "currency", self.currency.strip().upper())
        if self.state is CostEstimateState.KNOWN:
            if self.amount is None or self.upper_bound is not None:
                raise ValueError("known cost estimates require amount and forbid upper_bound")
            if self.amount < 0:
                raise ValueError("cost amount cannot be negative")
        elif self.state is CostEstimateState.BOUNDED:
            if self.upper_bound is None or self.amount is not None:
                raise ValueError("bounded cost estimates require upper_bound and forbid amount")
            if self.upper_bound < 0:
                raise ValueError("cost upper_bound cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "amount": self.amount,
            "upper_bound": self.upper_bound,
            "currency": self.currency,
        }


def cost_estimate_for_offer(offer: CapabilityOffer) -> ExecutionCostEstimate:
    """Return only product-known cost facts; never invent provider prices."""
    if offer.cost_class is CostClass.FREE:
        return ExecutionCostEstimate(CostEstimateState.NOT_APPLICABLE)
    return ExecutionCostEstimate(CostEstimateState.UNKNOWN)


def normalized_input_digest(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        raise InvalidExecutionInput("execution input must be a JSON object")
    try:
        encoded = json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidExecutionInput("execution input must be finite JSON data") from exc
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ExecutionIntent:
    project_id: str
    capability_id: str
    offer_id: str
    selection_policy: SelectionPolicy
    input_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "selection_policy": self.selection_policy.value,
            "input_digest": self.input_digest,
        }


@dataclass(frozen=True)
class ExecutionPreparation:
    intent: ExecutionIntent
    locality: LocalityClass
    cost_class: CostClass
    cost_estimate: ExecutionCostEstimate
    consent_required: tuple[ConsentScope, ...]
    schema_version: int = EXECUTION_AUTHORIZATION_SCHEMA_VERSION

    @property
    def authorization_required(self) -> bool:
        return bool(self.consent_required)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "intent": self.intent.to_dict(),
            "locality": self.locality.value,
            "cost_class": self.cost_class.value,
            "cost_estimate": self.cost_estimate.to_dict(),
            "consent_required": [item.value for item in self.consent_required],
            "authorization_required": self.authorization_required,
        }


def prepare_execution(
    *,
    project_id: str,
    offer: CapabilityOffer,
    selection_policy: SelectionPolicy,
    payload: Mapping[str, Any],
    cost_estimate: ExecutionCostEstimate | None = None,
) -> ExecutionPreparation:
    estimate = cost_estimate or cost_estimate_for_offer(offer)
    consent: list[ConsentScope] = []
    if offer.locality is not LocalityClass.LOCAL:
        consent.append(ConsentScope.REMOTE_EXECUTION)
    if offer.cost_class is not CostClass.FREE:
        consent.append(ConsentScope.EXTERNAL_COST)
    if estimate.state is CostEstimateState.UNKNOWN:
        consent.append(ConsentScope.UNKNOWN_COST)
    return ExecutionPreparation(
        intent=ExecutionIntent(
            project_id=project_id,
            capability_id=offer.capability_id,
            offer_id=offer.offer_id,
            selection_policy=selection_policy,
            input_digest=normalized_input_digest(payload),
        ),
        locality=offer.locality,
        cost_class=offer.cost_class,
        cost_estimate=estimate,
        consent_required=tuple(consent),
    )


@dataclass(frozen=True)
class _AuthorizationGrant:
    token: str
    intent: ExecutionIntent
    consent: tuple[ConsentScope, ...]
    expires_at: float


class OneShotAuthorizationStore:
    """Process-local one-shot execution grants bound to an exact input digest."""

    def __init__(self, *, ttl_seconds: float = DEFAULT_AUTHORIZATION_TTL_SECONDS) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = float(ttl_seconds)
        self._grants: dict[str, _AuthorizationGrant] = {}
        self._lock = threading.RLock()

    def issue(
        self,
        preparation: ExecutionPreparation,
        *,
        acknowledgements: set[ConsentScope],
    ) -> tuple[str | None, float | None]:
        required = set(preparation.consent_required)
        if not required:
            return None, None
        missing = required.difference(acknowledgements)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ExecutionConsentRequired(f"missing required execution acknowledgements: {names}")
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + self.ttl_seconds
        grant = _AuthorizationGrant(
            token=token,
            intent=preparation.intent,
            consent=tuple(sorted(required, key=lambda item: item.value)),
            expires_at=expires_at,
        )
        with self._lock:
            self._purge_expired_locked()
            self._grants[token] = grant
        return token, expires_at

    def consume(self, token: str | None, preparation: ExecutionPreparation) -> None:
        if not preparation.authorization_required:
            if token is not None:
                raise ExecutionAuthorizationInvalid(
                    "authorization token was supplied for an execution that does not require consent"
                )
            return
        if not isinstance(token, str) or not token:
            raise ExecutionConsentRequired("one-shot execution authorization is required")
        with self._lock:
            grant = self._grants.pop(token, None)
            self._purge_expired_locked()
        if grant is None:
            raise ExecutionAuthorizationInvalid("execution authorization is invalid or already consumed")
        if grant.expires_at <= time.time():
            raise ExecutionAuthorizationInvalid("execution authorization has expired")
        if grant.intent != preparation.intent:
            raise ExecutionAuthorizationInvalid(
                "execution authorization does not match the selected offer or normalized input"
            )
        if set(grant.consent) != set(preparation.consent_required):
            raise ExecutionAuthorizationInvalid("execution authorization consent scope no longer matches")

    def _purge_expired_locked(self) -> None:
        now = time.time()
        expired = [token for token, grant in self._grants.items() if grant.expires_at <= now]
        for token in expired:
            self._grants.pop(token, None)
