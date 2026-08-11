# UV Studio Development

Development commands should be run from the UV Studio repository root. Contributors should not need to remember internal paths inside `vendor/videoclaw-app`.

## Windows

Requirements for development:

- Python 3.11+;
- Node.js 20+ and npm;
- Git;
- FFmpeg for media operations that need it.

Prepare the local environment once:

```powershell
.\scripts\setup-dev.ps1
```

This creates `.venv`, installs the pinned backend requirements, and runs `npm ci` in the UV Studio-owned top-level `frontend/`.

Start the backend:

```powershell
.\scripts\run-backend.ps1
```

Start the frontend in another PowerShell window:

```powershell
.\scripts\run-frontend.ps1
```

The backend command starts **UV Studio's own server entrypoint** (`uv_studio.server`). That server mounts UV Studio-owned APIs on top of the pinned VideoClaw FastAPI application, so existing upstream routes remain available without editing vendored router files.

The frontend command runs the product-owned derived frontend from:

```text
frontend/
```

The untouched pinned frontend snapshot remains at `vendor/videoclaw-app/frontend/` only for provenance/comparison. See `docs/FRONTEND.md` before using the destructive frontend reset tool.

Default development URLs:

- backend health: `http://127.0.0.1:8000/api/health`
- UV Studio projects API: `http://127.0.0.1:8000/api/uv/projects`
- frontend: `http://localhost:3000`
- canonical projects screen: `http://localhost:3000/projects`

## Project data location

By default, UV Studio project metadata is stored under:

```text
data/projects/
```

from the repository root during development.

Override the location with:

```text
UV_STUDIO_PROJECTS_DIR
```

PowerShell example:

```powershell
$env:UV_STUDIO_PROJECTS_DIR = "D:\UVStudioProjects"
.\scripts\run-backend.ps1
```

Tests always override the Project Store dependency to a temporary directory and do not write into the normal project root.

## Cross-platform launcher

The stable UV Studio-owned development entrypoint is:

```text
python tools/uv_dev.py <command>
```

Commands:

```text
paths
backend
frontend --mode dev|start|build
health-smoke
```

Examples:

```powershell
.\.venv\Scripts\python.exe tools\uv_dev.py paths
.\.venv\Scripts\python.exe tools\uv_dev.py health-smoke
```

On Linux/macOS with a prepared virtual environment:

```bash
.venv/bin/python tools/uv_dev.py backend
python tools/uv_dev.py frontend --mode dev
```

## Health smoke

`health-smoke` starts the UV Studio FastAPI server as a subprocess, repeatedly probes the existing `/api/health` HTTP route until it returns `{"status":"ok", ...}`, then terminates the server.

It requires backend dependencies to be installed but does **not** require model/API credentials.

The smoke test proves two compatibility properties at once:

1. the pinned upstream FastAPI routes still function;
2. UV Studio can own the backend entrypoint without modifying the vendored application.

## Vendored upstream

Do not manually edit files under `vendor/videoclaw-app` during ordinary UV Studio feature work.

The directory is reconstructed from:

```text
upstream/video-claw.lock.json
```

using:

```text
python tools/vendor_videoclaw.py
```

If upstream code must change, first decide whether the change belongs in an UV Studio wrapper/adapter. Direct changes to vendored code need an explicit decision because they complicate future upstream comparisons.

## Product frontend provenance

The top-level `frontend/` started as a reproducible derived copy of the pinned upstream frontend but is now normal UV Studio product source.

Safe provenance check:

```text
python tools/promote_frontend.py --check
```

Do **not** run a forced frontend reset during normal development. `python tools/promote_frontend.py --force` deliberately deletes product frontend changes and recreates the original pinned baseline.

## Cross-chat continuation

The repository and GitHub are the project memory; old chat history is not required to continue development. Every coding agent or new development chat must begin with `AGENTS.md`, which owns the mandatory reading order and coordination rules. `DEVELOPMENT_PROTOCOL.md` defines the full slice, PR and handoff lifecycle.

Before implementation, validate the checked-in development state from the repository root:

```text
python tools/validate_development_context.py
```

The validator checks the machine-readable active slice and its links to the human context. GitHub CI additionally checks the live PR identity, draft phase, body markers and required sections.
