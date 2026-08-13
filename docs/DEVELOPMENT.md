# UV Studio Development

Development commands run from the repository root. This document describes the current UV-owned runtime.

## Continuously verified toolchain

Permanent CI currently verifies Python 3.11, Node.js 20, npm, FFmpeg/FFprobe, MLT `melt`, Windows and Ubuntu. Newer Python versions may work, but they are not a support claim until added to CI.

## Windows setup

```powershell
.\scripts\setup-dev.ps1
```

The script creates `.venv`, installs `requirements-uv-dev.txt` on top of `requirements-uv.txt`, and runs `npm ci` in top-level `frontend/`.

Start backend:

```powershell
.\scripts\run-backend.ps1
```

Start frontend in another terminal:

```powershell
.\scripts\run-frontend.ps1
```

Cross-platform launcher:

```text
python tools/uv_dev.py paths
python tools/uv_dev.py backend
python tools/uv_dev.py frontend --mode dev
python tools/uv_dev.py health-smoke
```

## Runtime boundary

The backend entrypoint is `uv_studio.server`. It is a UV Studio-owned FastAPI application. The complete VideoClaw FastAPI route table is not mounted by default; the pinned vendor tree remains available only to exact compatibility adapters and provenance/comparison tooling.

Current health endpoint:

```text
GET http://127.0.0.1:8000/api/health
```

`health-smoke` proves the UV-owned server starts and responds over real HTTP without provider configuration. It does not prove legacy VideoClaw routes are live.

## Project data

Canonical projects default to `data/projects/` and can be moved with `UV_STUDIO_PROJECTS_DIR`. Machine-only runtime configuration is separate from canonical project data.

## Frontend

Top-level `frontend/` is UV Studio-owned product source derived from the pinned VideoClaw frontend. `vendor/videoclaw-app/frontend/` is comparison/provenance only.

Supported canonical product surfaces are under `/projects` and `/projects/[projectId]`. The historical VideoClaw workflow UI still exists in source, but its legacy API surface is not mounted by the UV-owned backend; do not treat it as a supported working product path. The next Stage 5 hardening slice will remove or explicitly isolate that mismatch.

## Vendored upstream

Do not edit `vendor/videoclaw-app` during ordinary feature work. Reconstruct it from `upstream/video-claw.lock.json` with `tools/vendor_videoclaw.py` only when deliberately updating the pin.

## Cross-chat continuation

Repository memory lifecycle is defined by `AGENTS.md`, `DEVELOPMENT_PROTOCOL.md` and D-038. Always run `python tools/validate_development_context.py` before implementation. A new slice starts only from idle `main`.
