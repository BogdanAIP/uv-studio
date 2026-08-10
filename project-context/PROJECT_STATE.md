# Project State

**Updated:** 2026-08-10  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 1 — Universal Project Store  
**Active branch:** `stage-1/projects-api`  
**Main status:** Stage 0 and Project Store core are merged; Projects API slice is ready for PR.

## Product definition

UV Studio is a universal video production and editing studio. It supports task-specific recipes rather than forcing every project through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities.

## Baseline architecture

- pinned modern VideoClaw application is the reusable runtime/UI baseline;
- pinned upstream SHA: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- `vendor/videoclaw-app` is a compatibility boundary, not the preferred location for new product code;
- UV Studio owns the backend entrypoint through `uv_studio.server`;
- upstream FastAPI routes remain mounted through that server;
- canonical project state is UV Studio's file-first Project Store, not upstream session JSON;
- future provider growth stays behind a semantic capability boundary;
- specialized state remains optional instead of inflating every project schema.

## Merged milestones

- `af24ed11d899ee1f459571c5d774b7ac9ad6d1ca` — reproducible VideoClaw baseline;
- `8d175c2535806841c712582532efea403a2f8599` — UV Studio root runtime/HTTP smoke boundary;
- `2276a854c4109f0039ae1aeb55304650840e1652` — canonical local Project Store v1.

## Stage 1 work completed in current slice

### UV Studio backend wrapper

Added `uv_studio/server.py`.

It:

- loads the pinned upstream FastAPI application;
- preserves existing upstream routes such as `/api/health`;
- mounts UV Studio-owned routers outside the vendored tree;
- becomes the target of `tools/uv_dev.py backend` and `health-smoke`.

No files under `vendor/videoclaw-app` were modified for this feature.

### UV Studio projects API

Added product-owned route family:

```text
GET   /api/uv/projects
POST  /api/uv/projects
GET   /api/uv/projects/{project_id}
PATCH /api/uv/projects/{project_id}
```

The API is intentionally thin and delegates canonical validation/persistence to `ProjectStore`.

Implemented:

- project listing;
- project creation;
- project retrieval;
- universal metadata update;
- explicit 404/409/422/500 translation;
- Pydantic response/request validation;
- rejection of explicit null updates;
- configurable project root via `UV_STUDIO_PROJECTS_DIR`;
- safe local default `data/projects/` during development.

### Project Store corruption behavior

`list_projects()` now ignores unrelated directories without `project.json`, but does not silently hide a directory that contains corrupt/invalid canonical project metadata. Such corruption is surfaced as an explicit error for recovery/UI handling.

### Integration tests

Added `tests_api/test_projects_api.py` using a temporary Project Store root.

Verified through FastAPI TestClient:

- upstream `/api/health` survives the wrapper;
- create/list/get/update project lifecycle;
- update persists through a fresh `ProjectStore` instance;
- missing project returns 404;
- invalid project ID/recipe returns 422;
- explicit null update returns 422.

## Verification

GitHub Actions run `31390452201` succeeded on Ubuntu and Windows.

Verified on both OSes:

- UV Studio unit tests;
- upstream backend compile/install/import;
- UV Studio server import without API credentials;
- Projects API integration tests;
- real HTTP `/api/health` through the UV Studio server wrapper;
- frontend `npm ci` and production build.

## What works now

- reproducible pinned upstream runtime;
- cross-chat repository state/handoff;
- UV Studio-owned backend entrypoint;
- existing upstream backend routes through that entrypoint;
- independent canonical Project Store;
- HTTP create/list/get/update project operations;
- configurable local project storage;
- cross-platform CI covering project API and backend compatibility.

## What does not work yet

- Projects frontend UI does not exist;
- the current product frontend is still the pinned VideoClaw frontend inside `vendor/`;
- source/artifact upload APIs are not implemented;
- ZIP import/export and backup rotation are not implemented;
- Recipe Registry does not exist;
- Capability Bridge/OpenClaw integration does not exist;
- media-specific recipes are not implemented.

## Current architectural risks

1. The user-facing frontend will require major product changes, so repeatedly patching `vendor/videoclaw-app/frontend` would make upstream provenance/update handling progressively worse.
2. The next UI slice should establish an UV Studio-owned frontend derived from the pinned MIT frontend baseline before adding substantial product screens.
3. Keep Project Store schema universal and small.
4. API/UI must call `ProjectStore` instead of duplicating filesystem rules.
5. Keep the large upstream film orchestrator specialized rather than central.
6. SQLite remains unjustified until measured need appears.

## Last verified repository facts

- active branch: `stage-1/projects-api`;
- fully successful relevant CI: `31390452201`;
- current merged main before this slice: `2276a854c4109f0039ae1aeb55304650840e1652`;
- pinned vendored file count: 195.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work here as completed.