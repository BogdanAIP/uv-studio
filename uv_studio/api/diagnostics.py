"""Secret-safe release and machine diagnostics API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from uv_studio.diagnostics import build_diagnostics

router = APIRouter(prefix="/api/uv/diagnostics", tags=["UV Studio Diagnostics"])


@router.get("")
def get_diagnostics(
    verify_release: bool = Query(
        False,
        description="Hash every packaged release payload file in addition to structural checks.",
    ),
) -> dict[str, Any]:
    return build_diagnostics(verify_release=verify_release)
