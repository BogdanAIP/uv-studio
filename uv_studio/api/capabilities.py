"""Read-only semantic capability catalog and adapter-offer metadata."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, status

from uv_studio.capabilities import (
    CapabilityRegistry,
    UnknownCapability,
    build_builtin_capability_registry,
)
from uv_studio.capabilities.models import OfferAvailability
from uv_studio.config import release_root
from uv_studio.toolchain import ToolchainResolutionError, packaged_tool_paths

router = APIRouter(prefix="/api/uv/capabilities", tags=["UV Studio Capabilities"])


def _project_packaged_local_media_offers(registry: CapabilityRegistry) -> None:
    """Replace development PATH readiness with verified packaged-tool readiness."""

    if release_root() is None:
        return
    try:
        tools = packaged_tool_paths()
        ready = all(tools.get(name) for name in ("ffmpeg", "ffprobe"))
        problem = None
    except ToolchainResolutionError as exc:
        ready = False
        problem = str(exc)

    for capability in registry.list_capabilities():
        for offer in registry.offers_for(capability.capability_id):
            if offer.adapter_id != "local_ffmpeg":
                continue
            registry.upsert_offer(
                replace(
                    offer,
                    availability=(
                        OfferAvailability.AVAILABLE
                        if ready
                        else OfferAvailability.UNAVAILABLE
                    ),
                    reason=(
                        "Verified UV Studio release FFmpeg/FFprobe components are available; "
                        "local deterministic media execution is enabled."
                        if ready
                        else "Packaged local media toolchain is not executable: "
                        + (problem or "required release components are unavailable")
                    ),
                )
            )


@lru_cache(maxsize=1)
def get_capability_registry() -> CapabilityRegistry:
    registry = build_builtin_capability_registry()
    _project_packaged_local_media_offers(registry)
    return registry


def _capability_payload(registry: CapabilityRegistry, capability_id: str) -> dict[str, Any]:
    capability = registry.get_capability(capability_id)
    payload = capability.to_dict()
    payload["offer_summary"] = registry.offer_summary(capability_id)
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
