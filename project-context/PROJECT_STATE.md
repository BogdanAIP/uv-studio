# Project State

**Updated:** 2026-08-10  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 1 — Universal Project Store  
**Active branch:** `stage-1/project-store-core`  
**Main status:** Stage 0 complete and merged; first Stage 1 Project Store slice is ready for PR.

## Product definition

UV Studio is a universal video production and editing studio. It supports task-specific recipes rather than forcing every project through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities.

## Baseline architecture

- pinned modern VideoClaw application is the reusable runtime/UI baseline;
- pinned upstream SHA: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- `vendor/videoclaw-app` is a compatibility boundary, not the preferred location for new product code;
- UV Studio-owned runtime wrapper exists at `tools/uv_dev.py`;
- future provider growth stays behind a semantic capability boundary;
- specialized state remains optional instead of inflating every project schema.

## Stage 0 status

Complete and merged into `main`.

Relevant `main` commits:

- `af24ed11d899ee1f459571c5d774b7ac9ad6d1ca` — reproducible VideoClaw baseline;
- `8d175c2535806841c712582532efea403a2f8599` — UV Studio root runtime/HTTP smoke boundary.

## Stage 1 work completed in current slice

### Canonical project schema v1

Added product-owned package:

```text
uv_studio/projects/
├── models.py
├── migrations.py
└── store.py
```

`project.json` contains only universal metadata:

- schema version;
- stable project ID;
- title;
- recipe ID;
- created/updated timestamps;
- settings;
- project-relative source references;
- artifact references;
- optional extensions namespace.

Music/story/continuity/review fields are not mandatory project fields.

### Local Project Store

Implemented:

- project creation;
- project loading after a new process/store instance;
- project updates;
- project listing;
- canonical directory layout;
- safe ID validation;
- project-relative reference validation including Windows absolute-path rejection;
- atomic `project.json` writes using temp file + flush + `fsync` + `os.replace`;
- cleanup after failed atomic replace;
- explicit malformed-document errors;
- schema migration boundary;
- explicit rejection of future unsupported schema versions;
- no SQLite/cloud dependency.

### Tests/documentation

Added `tests/test_project_store.py` covering:

- create/layout;
- restart/load;
- update;
- duplicate/missing projects;
- project ID traversal;
- reference path traversal;
- malformed JSON;
- unsupported future schema;
- directory/document ID mismatch;
- simulated atomic replace failure preserving previous canonical file;
- project listing.

Added `docs/PROJECT_STORE.md` and D-009 file-first Project Store decision.

## Verification

GitHub Actions run `31389343366` succeeded on Ubuntu and Windows.

Verified:

- all UV Studio unit tests including Project Store pass on both OSes;
- imported backend still compiles/installs/imports;
- real HTTP health smoke still succeeds;
- frontend production build still succeeds.

## What works now

- reproducible upstream runtime baseline;
- cross-chat repository state/handoff;
- root-level UV Studio startup and HTTP smoke;
- independent canonical UV Studio project metadata;
- durable atomic local project create/read/update/list operations;
- project state no longer needs upstream session JSON as its future canonical source.

## What does not work yet

- Project Store has no UV Studio HTTP API yet;
- Projects frontend screen does not exist;
- ZIP import/export and backup rotation are not implemented;
- Recipe Registry does not exist;
- Capability Bridge/OpenClaw integration does not exist;
- media-specific recipes are not implemented.

## Current risks

1. Keep the Project Store schema universal and small.
2. Do not let API/UI layers duplicate filesystem state rules; they must call ProjectStore.
3. Do not modify vendored upstream routers just to expose product endpoints; mount UV Studio routers from an owned server layer.
4. SQLite remains unjustified until measured need appears.
5. Avoid turning `extensions` into an unversioned dumping ground; large specialized data should get dedicated versioned files later.

## Last verified repository facts

- active branch: `stage-1/project-store-core`;
- latest fully successful relevant CI: `31389343366`;
- Stage 0 merged main head before current slice: `8d175c2535806841c712582532efea403a2f8599`;
- vendored upstream file count: 195.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work here as completed.