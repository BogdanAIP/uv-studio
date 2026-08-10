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

This creates `.venv`, installs the pinned backend requirements, and runs `npm ci` for the pinned frontend.

Start the backend:

```powershell
.\scripts\run-backend.ps1
```

Start the frontend in another PowerShell window:

```powershell
.\scripts\run-frontend.ps1
```

Default development URLs inherited from the pinned baseline:

- backend health: `http://127.0.0.1:8000/api/health`
- frontend: `http://localhost:3000`

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

`health-smoke` starts the pinned FastAPI backend as a subprocess, repeatedly probes the real `/api/health` HTTP route until it returns `{"status":"ok", ...}`, then terminates the backend.

It requires backend dependencies to be installed but does **not** require model/API credentials.

This is intentionally stronger than merely importing `api_server`: it proves that the selected baseline can bind a port and serve a real request through UV Studio's root-level launcher.

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

## Cross-chat continuation

At the start of a new development chat, read:

1. `project-context/PROJECT_STATE.md`
2. `project-context/NEXT_TASK.md`
3. `project-context/DECISIONS.md`
4. `ROADMAP.md`
5. `UPSTREAM.md`
6. current open PRs and recent `main` commits.

The repository is the project memory; old chat history is not required to continue development.
