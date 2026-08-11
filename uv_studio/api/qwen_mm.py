"""Trusted static Qwen-MM profile/binding pack API.

Unlike the generic MCP API this endpoint never accepts an arbitrary command.
It can only persist one of the pinned profile templates defined in UV Studio.
"""

from __future__ import annotations

import sys
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.mcp import get_mcp_config_store
from uv_studio.integrations.qwen_mm import (
    QwenMMPlatformUnsupported,
    UnknownQwenMMPack,
    configure_qwen_mm_pack,
    get_qwen_mm_pack,
    list_qwen_mm_packs,
)
from uv_studio.mcp.store import MCPConfigStore, MCPConfigStoreError

router = APIRouter(prefix="/api/uv/integrations/qwen-mm", tags=["UV Studio Qwen-MM"])


def get_qwen_platform() -> str:
    return sys.platform


@router.get("")
def list_qwen_packs() -> list[dict[str, Any]]:
    return [pack.to_dict() for pack in list_qwen_mm_packs()]


@router.get("/{pack_id}")
def get_qwen_pack(pack_id: str) -> dict[str, Any]:
    try:
        return get_qwen_mm_pack(pack_id).to_dict()
    except UnknownQwenMMPack as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Qwen-MM pack not found") from exc


@router.post("/{pack_id}/configure", status_code=status.HTTP_201_CREATED)
def configure_qwen_pack(
    pack_id: str,
    store: MCPConfigStore = Depends(get_mcp_config_store),
    platform: str = Depends(get_qwen_platform),
) -> dict[str, Any]:
    try:
        pack = get_qwen_mm_pack(pack_id)
        config = configure_qwen_mm_pack(store, pack_id, platform=platform)
    except UnknownQwenMMPack as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Qwen-MM pack not found") from exc
    except QwenMMPlatformUnsupported as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MCPConfigStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update MCP machine configuration",
        ) from exc

    return {
        "pack": pack.to_dict(),
        "configured_profile_id": pack.profile.profile_id,
        "binding_count": len(pack.bindings),
        "configuration": {
            "profile_count": len(config.profiles),
            "binding_count": len(config.bindings),
        },
        "next_action": (
            f"Run MCP discovery for profile {pack.profile.profile_id!r}. "
            "Only exact READY bindings can execute; UV Studio execution authorization "
            "is still enforced whenever locality or cost requires it."
        ),
    }
