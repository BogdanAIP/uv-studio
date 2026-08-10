# Next Task

**Primary target:** expose the canonical Project Store through an UV Studio-owned FastAPI layer without modifying vendored upstream routers.

## Do first

1. Add an UV Studio FastAPI application/wrapper that imports the pinned upstream app and mounts UV Studio-owned routers.
2. Add `/api/uv/projects` endpoints for:
   - list projects;
   - create project;
   - get project;
   - update universal metadata.
3. Configure the project root from an UV Studio-owned setting/environment variable with a safe local default.
4. Make `tools/uv_dev.py backend` and `health-smoke` start the UV Studio server wrapper rather than the raw upstream entrypoint.
5. Preserve the existing upstream `/api/health` route and all existing routes.
6. Add API tests using a temporary project root; tests must not write to real user directories.
7. Keep router/business logic thin: API handlers call `ProjectStore` rather than reimplementing persistence rules.

## Suggested files

- `uv_studio/server.py`
- `uv_studio/config.py`
- `uv_studio/api/__init__.py`
- `uv_studio/api/projects.py`
- `tests/test_projects_api.py`
- updates to `tools/uv_dev.py`
- updates to `docs/PROJECT_STORE.md` / `docs/DEVELOPMENT.md`

## Acceptance criteria

- existing upstream health route still returns success through the UV Studio server;
- `POST /api/uv/projects` creates a real project in the configured temporary root;
- `GET /api/uv/projects` lists it;
- `GET /api/uv/projects/{id}` returns canonical v1 metadata;
- metadata update persists across a fresh `ProjectStore` instance;
- invalid project IDs and validation errors return explicit 4xx responses;
- no files under `vendor/videoclaw-app` are modified;
- CI remains green on Windows and Linux.

## Explicitly out of scope for this slice

- Projects frontend UI;
- delete project;
- ZIP import/export;
- backup rotation;
- Recipe Registry;
- media upload API;
- OpenClaw integration;
- authentication/multi-user support.

The purpose of this slice is to make UV Studio, rather than VideoClaw session storage, the authoritative project API boundary.