"""Secret-safe UV Studio machine configuration API.

Provider credentials are write-only through this API. Reads expose only public
runtime settings and per-secret presence flags, never stored values.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.runtime_config import RuntimeConfigError, RuntimeConfigStore

router = APIRouter(tags=["UV Studio Configuration"])
PUBLIC_CONFIG_PATH = "data/config/runtime.json"


class RuntimeConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(default_factory=dict)
    secret_updates: dict[str, str | None] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def get_runtime_config_store() -> RuntimeConfigStore:
    return RuntimeConfigStore()


def _response(store: RuntimeConfigStore) -> dict[str, Any]:
    return {
        "config": store.public_config(),
        "secrets": store.secret_status(),
        "path": PUBLIC_CONFIG_PATH,
    }


def _translate_error(exc: RuntimeConfigError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


@router.get("/api/config")
def get_runtime_config(
    store: RuntimeConfigStore = Depends(get_runtime_config_store),
) -> dict[str, Any]:
    try:
        return _response(store)
    except RuntimeConfigError as exc:
        raise _translate_error(exc) from exc


@router.put("/api/config")
def update_runtime_config(
    request: RuntimeConfigUpdateRequest,
    store: RuntimeConfigStore = Depends(get_runtime_config_store),
) -> dict[str, Any]:
    try:
        config, secrets = store.update(
            values=request.values,
            secret_updates=request.secret_updates,
        )
        return {
            "config": config,
            "secrets": secrets,
            "path": PUBLIC_CONFIG_PATH,
        }
    except RuntimeConfigError as exc:
        raise _translate_error(exc) from exc
