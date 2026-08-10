# Project State

**Updated:** 2026-08-10  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 1 — Universal Project Store  
**Active branch:** `stage-1/frontend-shell`  
**Open PR:** #5 — `Stage 1: promote UV Studio frontend and add Projects UI`  
**Main status:** Stage 0, Project Store core and Projects API are merged; owned frontend/Projects UI is ready for merge after final PR CI.

## Product definition

UV Studio is a universal video production and editing studio. It supports task-specific recipes rather than forcing every project through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities.

## Current architecture

- pinned upstream runtime: `HITsz-TMG/VideoClaw@5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- immutable comparison/runtime snapshot: `vendor/videoclaw-app`;
- UV Studio-owned backend entrypoint: `uv_studio.server`;
- existing upstream FastAPI routes remain mounted through that server;
- canonical project state: UV Studio file-first Project Store (`project.json` v1), not upstream session JSON;
- canonical project API: `/api/uv/projects`;
- UV Studio-owned product frontend: top-level `frontend/`, derived once from the pinned MIT frontend baseline;
- untouched upstream frontend snapshot remains at `vendor/videoclaw-app/frontend`;
- future provider growth stays behind a semantic capability boundary;
- specialized state remains optional instead of inflating every project schema.

## Merged milestones

- `af24ed11d899ee1f459571c5d774b7ac9ad6d1ca` — reproducible VideoClaw baseline;
- `8d175c2535806841c712582532efea403a2f8599` — UV Studio root runtime/HTTP smoke boundary;
- `2276a854c4109f0039ae1aeb55304650840e1652` — canonical local Project Store v1;
- `21016061be2a2aedd59e7ed7b0424467d82bfd2f` — UV Studio server wrapper + canonical Projects API.

## Stage 1 work completed in current frontend slice

### Product-owned frontend

Promoted the exact pinned VideoClaw frontend baseline into:

```text
frontend/
```

The initial source is traceable through:

```text
frontend/.uv-derived.json
frontend/UPSTREAM_LICENSE
```

Current recorded source baseline:

- source commit: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- source subtree: `video-claw/video-claw/frontend`;
- source file count: 47;
- source tree SHA-256: `eacb45953cae0ec5a64043eacbc534ef582a6be4867f5edd27af7cdbdf592bcd`.

`tools/uv_dev.py`, Windows setup and CI now use top-level `frontend/`, not the vendored frontend snapshot.

### Frontend promotion/reset safety

Added `tools/promote_frontend.py` and tests.

Rules:

- `--check` is read-only and reports source digest/count;
- an existing `frontend/` is never replaced by a normal promotion command;
- replacement requires explicit destructive `--force`;
- staging is created on the destination filesystem so Windows checkouts work even when system temp and repository are on different drives;
- GitHub workflow `Reset frontend to pinned baseline` is manual-only.

This prevents ordinary tooling from silently deleting UV Studio product frontend changes.

### Canonical Projects UI

Added:

```text
frontend/lib/projectsApi.ts
frontend/app/projects/page.tsx
frontend/app/projects/[projectId]/page.tsx
```

Implemented:

- list canonical UV Studio projects;
- create a `general_video` project through `/api/uv/projects`;
- open a project using stable UV Studio `project_id`;
- show recipe/schema/source/artifact metadata;
- loading/error/empty states;
- `/api/uv/*` Next.js proxy to the UV Studio backend;
- link from the existing production workspace to `/projects`;
- product metadata/title set to UV Studio.

Legacy VideoClaw session IDs are intentionally not substituted for canonical UV Studio project IDs.

### Migration policy

The existing production workspace remains reachable at `/` while product surfaces are migrated gradually. Full localization/rebranding of old production screens is not required for this slice.

## Verification

GitHub Actions CI run `31392325018` completed successfully on Ubuntu and Windows.

Verified:

- UV Studio bootstrap/unit tests;
- frontend provenance checks;
- backend compile/install/import;
- UV Studio Projects API integration tests;
- real HTTP health smoke through `uv_studio.server`;
- `npm ci` from top-level `frontend/`;
- Next.js production build from top-level `frontend/`.

PR #5 triggers another final CI run after this handoff update before merge.

## What works now

- reproducible pinned backend/runtime baseline;
- durable cross-chat repository handoff;
- UV Studio-owned backend entrypoint;
- canonical local Project Store;
- canonical project HTTP API;
- UV Studio-owned user-facing frontend;
- canonical Projects list/create/open flow;
- existing upstream production UI retained during migration;
- cross-platform build and backend smoke coverage.

## What does not work yet

- project archive export/import is not implemented;
- project backup/recovery helpers are not implemented;
- source/artifact upload/mutation API is not implemented;
- canonical project shell is not yet bound to recipes/workflows;
- Recipe Registry does not exist;
- Capability Bridge/OpenClaw integration does not exist;
- media-specific UV Studio recipes are not implemented;
- existing production screens still contain upstream terminology/language.

## Current risks

1. Never conflate canonical `project_id` with legacy upstream session IDs.
2. Do not run forced frontend reset during normal development.
3. Keep Project Store schema universal and small.
4. Keep product filesystem rules inside `ProjectStore`; API/UI must not duplicate them.
5. Keep the large upstream film orchestrator specialized rather than central.
6. Finish project portability/recovery before beginning Recipe Registry so project state remains safely movable and recoverable.

## Last verified repository facts

- active branch: `stage-1/frontend-shell`;
- open PR: #5;
- latest fully successful branch CI before final handoff commit: `31392325018`;
- current merged `main` before PR #5: `21016061be2a2aedd59e7ed7b0424467d82bfd2f`;
- pinned vendored app file count: 195;
- promoted frontend initial source file count: 47.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work here as completed.