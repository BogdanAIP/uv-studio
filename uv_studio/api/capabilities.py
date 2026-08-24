"""Read-only semantic capability catalog and adapter-offer metadata."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, status

from uv_studio.capabilities import (
    CapabilityRegistry,
    UnknownCapability,
    build_builtin_capability_registry,
)
from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability

router = APIRouter(prefix="/api/uv/capabilities", tags=["UV Studio Capabilities"])


@lru_cache(maxsize=1)
def get_capability_registry() -> CapabilityRegistry:
    return build_builtin_capability_registry()


def _execution_summary(registry: CapabilityRegistry, capability_id: str) -> dict[str, int]:
    offers = registry.offers_for(capability_id)
    available = [offer for offer in offers if offer.availability is OfferAvailability.AVAILABLE]
    configuration_required = [
        offer
        for offer in offers
        if offer.availability is OfferAvailability.CONFIGURATION_REQUIRED
    ]
    return {
        "local_free_available": sum(
            offer.locality is LocalityClass.LOCAL and offer.cost_class is CostClass.FREE
            for offer in available
        ),
        "external_available": sum(
            offer.locality is not LocalityClass.LOCAL
            for offer in available
        ),
        "paid_capable_available": sum(
            offer.cost_class is not CostClass.FREE
            for offer in available
        ),
        "local_configuration_required": sum(
            offer.locality is LocalityClass.LOCAL
            for offer in configuration_required
        ),
        "external_configuration_required": sum(
            offer.locality is not LocalityClass.LOCAL
            for offer in configuration_required
        ),
    }


def _capability_payload(registry: CapabilityRegistry, capability_id: str) -> dict[str, Any]:
    capability = registry.get_capability(capability_id)
    payload = capability.to_dict()
    payload["offer_summary"] = registry.offer_summary(capability_id)
    payload["execution_summary"] = _execution_summary(registry, capability_id)
    return payload


@router.get("")
def list_capabilities() -> list[dict[str, Any]]:
    registry = get_capability_registry()
    return [
        _capability_payload(registry, capability.capability_id)
        for capability in registry.list_capabilities()
    ]


@router.get("/{capability_id}")
def get_capability(capability_id: str) -> dict[str, Any]:
    registry = get_capability_registry()
    try:
        return _capability_payload(registry, capability_id)
    except UnknownCapability as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability not found",
        ) from exc


@router.get("/{capability_id}/offers")
def list_capability_offers(capability_id: str) -> list[dict[str, Any]]:
    registry = get_capability_registry()
    try:
        offers = registry.offers_for(capability_id)
    except UnknownCapability as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability not found",
        ) from exc
    return [
        {
            **offer.to_dict(),
            "adapter": registry.get_adapter(offer.adapter_id).to_dict(),
        }
        for offer in offers
    ]
