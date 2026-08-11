"""Read-only MCP profile/discovery management API.

Profiles are machine configuration. This API deliberately does not expose a
create/update command surface and does not invoke MCP tools.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.capabilities import CapabilityRegistry
from uv_studio.config import configuration_root
from uv_studio.mcp.client import (
    MCPDiscoveryError,
    MCPDiscoveryTimeout,
    MCPMissingEnvironment,
)
from uv_studio.mcp.manager import (
    MCPManager,
    MCPManagerError,
    MCPProfileDisabled,
    MCPProfileNotFound,
    MCPProfileNotReady,
)
from uv_studio.mcp.models import MCPConfigurationError
from uv_studio.mcp.store import MCPConfigStore, MCPConfigStoreError

router = APIRouter(prefix="/api/uv/mcp", tags=["UV Studio MCP"])


@lru_cache(maxsize=1)
def get_mcp_config_store() -> MCPConfigStore:
    return MCPConfigStore(configuration_root())


@lru_cache(maxsize=1)
def _default_mcp_manager() -> MCPManager:
    return MCPManager(get_mcp_config_store(), get_capability_registry())


def get_mcp_manager(
    registry: CapabilityRegistry = Depends(get_capability_registry),
) -> MCPManager:
    default = _default_mcp_manager()
    if default.registry is registry:
        return default
    # Primarily supports dependency-overridden registries in tests without
    # mutating the process-wide manager singleton.
    return MCPManager(get_mcp_config_store(), registry)


def _profile_not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP profile not found")


@router.get("/profiles")
def list_mcp_profiles(
    manager: MCPManager = Depends(get_mcp_manager),
) -> list[dict[str, Any]]:
    try:
        return [manager.profile_payload(profile) for profile in manager.profiles()]
    except MCPConfigStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MCP machine configuration is invalid",
        ) from exc


@router.get("/bindings")
def list_mcp_bindings(
    manager: MCPManager = Depends(get_mcp_manager),
) -> list[dict[str, Any]]:
    try:
        return [binding.to_dict() for binding in manager.bindings()]
    except MCPConfigStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MCP machine configuration is invalid",
        ) from exc


@router.get("/profiles/{profile_id}/status")
def get_mcp_profile_status(
    profile_id: str,
    manager: MCPManager = Depends(get_mcp_manager),
) -> dict[str, Any]:
    try:
        return manager.status(profile_id).to_dict()
    except MCPProfileNotFound as exc:
        raise _profile_not_found(exc) from exc


@router.get("/profiles/{profile_id}/tools")
def list_mcp_profile_tools(
    profile_id: str,
    manager: MCPManager = Depends(get_mcp_manager),
) -> list[dict[str, Any]]:
    try:
        return [tool.to_dict() for tool in manager.tools(profile_id)]
    except MCPProfileNotFound as exc:
        raise _profile_not_found(exc) from exc
    except MCPProfileNotReady as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/profiles/{profile_id}/connect")
async def connect_mcp_profile(
    profile_id: str,
    manager: MCPManager = Depends(get_mcp_manager),
) -> dict[str, Any]:
    try:
        return (await manager.connect(profile_id)).to_dict()
    except MCPProfileNotFound as exc:
        raise _profile_not_found(exc) from exc
    except MCPProfileDisabled as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MCP profile is disabled") from exc
    except (MCPMissingEnvironment, MCPConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MCPDiscoveryTimeout as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except (MCPDiscoveryError, MCPManagerError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/profiles/{profile_id}/disconnect")
async def disconnect_mcp_profile(
    profile_id: str,
    manager: MCPManager = Depends(get_mcp_manager),
) -> dict[str, Any]:
    try:
        return (await manager.disconnect(profile_id)).to_dict()
    except MCPProfileNotFound as exc:
        raise _profile_not_found(exc) from exc
