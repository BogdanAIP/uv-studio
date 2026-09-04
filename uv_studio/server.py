"""UV Studio-owned FastAPI application boundary.

The pinned VideoClaw tree remains available to exact compatibility adapters, but
the complete upstream FastAPI route table is not mounted by default.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_BACKEND = ROOT / "vendor" / "videoclaw-app" / "backend"

if str(UPSTREAM_BACKEND) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_BACKEND))

import uvicorn  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from uv_studio.api.artifact_files import router as artifact_files_router  # noqa: E402
from uv_studio.api.capabilities import router as capabilities_router  # noqa: E402
from uv_studio.api.capability_execution import router as capability_execution_router  # noqa: E402
from uv_studio.api.configuration import router as configuration_router  # noqa: E402
from uv_studio.api.continuity_brief import router as continuity_brief_router  # noqa: E402
from uv_studio.api.dubbing_review_current import router as dubbing_review_current_router  # noqa: E402
from uv_studio.api.edit_state import router as edit_state_router  # noqa: E402
from uv_studio.api.editor_commands import router as editor_commands_router  # noqa: E402
from uv_studio.api.generation import router as generation_router  # noqa: E402
from uv_studio.api.mcp import router as mcp_router  # noqa: E402
from uv_studio.api.music_analysis_assist import router as music_analysis_assist_router  # noqa: E402
from uv_studio.api.music_assembly import router as music_assembly_router  # noqa: E402
from uv_studio.api.music_direction import router as music_direction_router  # noqa: E402
from uv_studio.api.music_map import router as music_map_router  # noqa: E402
from uv_studio.api.music_video_review import router as music_video_review_router  # noqa: E402
from uv_studio.api.prepared_audio import router as prepared_audio_router  # noqa: E402
from uv_studio.api.prepared_audio_promotion import router as prepared_audio_promotion_router  # noqa: E402
from uv_studio.api.production_semantics import router as production_semantics_router  # noqa: E402
from uv_studio.api.project_common import get_project_store  # noqa: E402
from uv_studio.api.project_media import router as project_media_router  # noqa: E402
from uv_studio.api.project_transactions import router as project_transactions_router  # noqa: E402
from uv_studio.api.project_workflow import router as project_workflow_router  # noqa: E402
from uv_studio.api.projects import router as projects_router  # noqa: E402
from uv_studio.api.qwen_mm import router as qwen_mm_router  # noqa: E402
from uv_studio.api.replacement_plan import router as replacement_plan_router  # noqa: E402
from uv_studio.api.replacement_preparation import router as replacement_preparation_router  # noqa: E402
from uv_studio.api.replacement_review import router as replacement_review_router  # noqa: E402
from uv_studio.api.sequence_continuity import router as sequence_continuity_router  # noqa: E402
from uv_studio.api.sequence_review_assist import router as sequence_review_assist_router  # noqa: E402
from uv_studio.api.stage8_workspace import router as stage8_workspace_router  # noqa: E402
from uv_studio.api.studio_timeline import router as studio_timeline_router  # noqa: E402
from uv_studio.config import allowed_frontend_origins  # noqa: E402
from uv_studio.generation.recovery import recover_interrupted_generation_jobs  # noqa: E402
from uv_studio.projects.root_staging import recover_stale_root_staging  # noqa: E402
from uv_studio.runtime_config import RuntimeConfigStore  # noqa: E402

TRUSTED_FRONTEND_ORIGINS = frozenset(allowed_frontend_origins())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Root-level staging is outside every project directory and has its own
    # cross-runtime lease. Reclaim only staging whose OS lock proves its publisher
    # is no longer alive before project-scoped publication/job reconciliation.
    store = get_project_store()
    recover_stale_root_staging(store.root)
    # FastAPI BackgroundTasks are process-local rather than durable workers.
    # Reconcile abandoned queued/running generation records before accepting
    # requests, but never auto-replay provider work after a restart.
    recover_interrupted_generation_jobs(store)
    yield


app = FastAPI(title="UV Studio", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(TRUSTED_FRONTEND_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def enforce_trusted_browser_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin is not None and origin not in TRUSTED_FRONTEND_ORIGINS:
        return JSONResponse(
            status_code=403,
            content={"detail": "browser origin is not allowed by UV Studio"},
        )
    return await call_next(request)


app.include_router(configuration_router)
app.include_router(capabilities_router)
app.include_router(capability_execution_router)
app.include_router(generation_router)
app.include_router(mcp_router)
app.include_router(qwen_mm_router)
app.include_router(projects_router)
app.include_router(project_workflow_router)
app.include_router(project_media_router)
app.include_router(studio_timeline_router)
app.include_router(production_semantics_router)
app.include_router(project_transactions_router)
app.include_router(stage8_workspace_router)
app.include_router(prepared_audio_router)
app.include_router(prepared_audio_promotion_router)
app.include_router(artifact_files_router)
app.include_router(editor_commands_router)
app.include_router(dubbing_review_current_router)
app.include_router(edit_state_router)
app.include_router(continuity_brief_router)
app.include_router(replacement_plan_router)
app.include_router(replacement_preparation_router)
app.include_router(replacement_review_router)
app.include_router(sequence_continuity_router)
app.include_router(sequence_review_assist_router)
app.include_router(music_map_router)
app.include_router(music_direction_router)
app.include_router(music_assembly_router)
app.include_router(music_analysis_assist_router)
app.include_router(music_video_review_router)


@app.get("/api/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "uv-studio"}


@app.get("/api/stages", tags=["Compatibility metadata"])
def legacy_stage_catalog() -> dict[str, list[dict[str, object]]]:
    return {
        "stages": [
            {"id": "script_generation", "name": "剧本生成", "order": 1, "description": "将灵感转化为结构化剧本"},
            {"id": "character_design", "name": "角色/场景设计", "order": 2, "description": "生成角色设计图和场景背景"},
            {"id": "storyboard", "name": "分镜设计", "order": 3, "description": "设计镜头语言和分镜脚本"},
            {"id": "reference_generation", "name": "参考图生成", "order": 4, "description": "生成高精度参考图"},
            {"id": "video_generation", "name": "视频生成", "order": 5, "description": "将参考图/分镜图生成视频"},
            {"id": "post_production", "name": "后期剪辑", "order": 6, "description": "拼接视频片段为最终成片"},
        ]
    }


@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    return {
        "service": "UV Studio",
        "version": "0.1.0",
        "health": "/api/health",
        "projects": "/api/uv/projects",
    }


def main() -> None:
    server = RuntimeConfigStore().public_config()["server"]
    uvicorn.run(
        app,
        host=server["host"],
        port=server["port"],
        access_log=server["access_log"],
        log_level=str(server["log_level"]).lower(),
    )


if __name__ == "__main__":
    main()
