"""UV Studio FastAPI entrypoint.

The pinned VideoClaw application remains available, while UV Studio-owned
routers are mounted from outside the vendored tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_BACKEND = ROOT / "vendor" / "videoclaw-app" / "backend"

if str(UPSTREAM_BACKEND) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_BACKEND))

import uvicorn  # noqa: E402
from api.app import app as upstream_app  # type: ignore  # noqa: E402
from config import settings as upstream_settings  # type: ignore  # noqa: E402

from uv_studio.api.capabilities import router as capabilities_router  # noqa: E402
from uv_studio.api.capability_execution import router as capability_execution_router  # noqa: E402
from uv_studio.api.execution import router as execution_router  # noqa: E402
from uv_studio.api.mcp import router as mcp_router  # noqa: E402
from uv_studio.api.projects import router as projects_router  # noqa: E402
from uv_studio.api.qwen_mm import router as qwen_mm_router  # noqa: E402
from uv_studio.api.recipes import router as recipes_router  # noqa: E402

app = upstream_app
app.include_router(capabilities_router)
app.include_router(capability_execution_router)
app.include_router(mcp_router)
app.include_router(qwen_mm_router)
app.include_router(recipes_router)
app.include_router(execution_router)
app.include_router(projects_router)


def main() -> None:
    uvicorn.run(
        app,
        host=upstream_settings.HOST,
        port=upstream_settings.PORT,
        access_log=upstream_settings.ACCESS_LOG,
    )


if __name__ == "__main__":
    main()
