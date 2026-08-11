"""Explicit offer selection policies for capability execution.

Registry ordering is descriptive metadata. This module is the permission boundary
that decides whether an offer may actually be selected for execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import CapabilityOffer, CostClass, LocalityClass, OfferAvailability
from .registry import CapabilityRegistry, UnknownCapability, UnknownOffer


class SelectionPolicy(str, Enum):
    MANUAL = "manual"
    PINNED_OFFER = "pinned_offer"
    LOCAL_FREE_FIRST = "local_free_first"


class OfferSelectionError(RuntimeError):
    pass


class OfferSelectionRequired(OfferSelectionError):
    pass


class NoEligibleOffer(OfferSelectionError):
    pass


class PinnedOfferRejected(OfferSelectionError):
    pass


@dataclass(frozen=True)
class OfferSelectionDecision:
    capability_id: str
    policy: SelectionPolicy
    offer: CapabilityOffer | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "policy": self.policy.value,
            "offer": None if self.offer is None else self.offer.to_dict(),
            "reason": self.reason,
        }


def _normalize_policy(value: SelectionPolicy | str) -> SelectionPolicy:
    if isinstance(value, SelectionPolicy):
        return value
    try:
        return SelectionPolicy(value)
    except (TypeError, ValueError) as exc:
        raise OfferSelectionError(f"unknown selection policy: {value!r}") from exc


def select_offer(
    registry: CapabilityRegistry,
    capability_id: str,
    *,
    policy: SelectionPolicy | str,
    pinned_offer_id: str | None = None,
) -> OfferSelectionDecision:
    """Select an offer without ever turning metadata preference into paid fallback.

    `local_free_first` is intentionally strict: only AVAILABLE + FREE + LOCAL
    offers qualify. It never widens to hybrid/remote or potentially-paid/paid.
    """

    normalized_policy = _normalize_policy(policy)
    registry.get_capability(capability_id)

    if normalized_policy is SelectionPolicy.MANUAL:
        raise OfferSelectionRequired(
            "manual selection does not choose an offer automatically; choose an exact offer first"
        )

    if normalized_policy is SelectionPolicy.PINNED_OFFER:
        if not pinned_offer_id:
            raise PinnedOfferRejected("pinned_offer policy requires pinned_offer_id")
        try:
            offer = registry.get_offer(pinned_offer_id)
        except UnknownOffer as exc:
            raise PinnedOfferRejected(f"unknown pinned offer: {pinned_offer_id}") from exc
        if offer.capability_id != capability_id:
            raise PinnedOfferRejected(
                f"offer {offer.offer_id!r} provides {offer.capability_id!r}, not {capability_id!r}"
            )
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise PinnedOfferRejected(
                f"offer {offer.offer_id!r} is not available: {offer.availability.value}"
            )
        return OfferSelectionDecision(
            capability_id=capability_id,
            policy=normalized_policy,
            offer=offer,
            reason="exact user-pinned available offer selected",
        )

    safe_offers = [
        offer
        for offer in registry.offers_for(capability_id, include_unavailable=False)
        if offer.cost_class is CostClass.FREE and offer.locality is LocalityClass.LOCAL
    ]
    if not safe_offers:
        summary = registry.offer_summary(capability_id)
        raise NoEligibleOffer(
            "no available local/free offer exists; local_free_first will not fall through "
            f"to remote or paid-capable offers (summary={summary})"
        )
    offer = safe_offers[0]
    return OfferSelectionDecision(
        capability_id=capability_id,
        policy=normalized_policy,
        offer=offer,
        reason="selected first available local/free offer",
    )
