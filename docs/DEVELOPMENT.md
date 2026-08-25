# UV Studio Development

Development commands run from the repository root. This document describes the current UV-owned runtime.

## Continuously verified toolchain

Permanent CI verifies Python 3.11, Node.js 20/npm, FFmpeg/FFprobe, MLT `melt`, Windows and Ubuntu. Newer versions are not support claims until added to CI.

## Local setup

Windows:

```powershell
.\scripts\setup-dev.ps1
.\scripts\run-backend.ps1
# another terminal
.\scripts\run-frontend.ps1
```

Cross-platform helper:

```text
python tools/uv_dev.py paths
python tools/uv_dev.py backend
python tools/uv_dev.py frontend --mode dev
python tools/uv_dev.py health-smoke
```

## Runtime boundary

The backend entrypoint is `uv_studio.server`, a UV-owned FastAPI application. The complete VideoClaw FastAPI application is not mounted as product root. Exact compatibility adapters and selected legacy UV routes remain while supported historical projects/tests need them.

Current health endpoint: `GET http://127.0.0.1:8000/api/health`.

## Current frontend/product boundary

Modern product entry points are:

```text
/projects
 -> choose Production Direction
 -> /projects/{projectId}/studio
```

`/projects/{projectId}` remains a compatibility workspace for old recipe/Product-Orchestrator projects. Do not add new Production Direction UI there.

Canonical projects default to `data/projects/` and can be moved with `UV_STUDIO_PROJECTS_DIR`. Machine-only runtime configuration is separate from portable project state.

## Architecture reading order

Before implementation read `AGENTS.md`, `project-context/ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, `docs/architecture/CURRENT_ARCHITECTURE.md` and the relevant accepted decisions. D-064 is current product composition; historical Stage/Recipe/Product-Orchestrator documents are subordinate compatibility/evidence.

## Vendored upstream

Do not edit `vendor/videoclaw-app` during ordinary feature work. Reconstruct it from `upstream/video-claw.lock.json` with `tools/vendor_videoclaw.py` only when deliberately updating the pin.

## Cross-chat continuation

Repository lifecycle is defined by `AGENTS.md`, `DEVELOPMENT_PROTOCOL.md` and D-038. Run `python tools/validate_development_context.py` before implementation. A new slice starts only from idle `main`.
