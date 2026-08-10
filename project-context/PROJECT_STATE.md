# Project State

**Updated:** 2026-08-10  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 0 — complete; Stage 1 is next  
**Active branch:** `stage-0/runtime-smoke`  
**Main status:** Stage 0 bootstrap baseline is merged; runtime-smoke slice is ready for PR.

## Product definition

UV Studio is a universal video production and editing studio. It supports task-specific recipes rather than forcing every project through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities.

## Chosen technical direction

- Base: modern `video-claw/video-claw` application from `HITsz-TMG/VideoClaw`.
- Pinned upstream commit: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276` (2026-07-17).
- Imported baseline contains FastAPI backend + Next.js frontend + current pipelines + model/task infrastructure.
- VideoClaw's large film orchestrator remains a legacy/specialized workflow, not the universal UV Studio core.
- New product workflows should be independent recipes/pipelines.
- Future provider expansion should go through a semantic Capability Bridge; OpenClaw remains the preferred replaceable runtime candidate.
- `musical-mv-storyboard` remains a separate specialized module planned for adapter integration in Stage 7.

## Stage 0 completed work

### Bootstrap/provenance

- initialized repository and durable cross-chat development protocol;
- added roadmap, decisions, upstream policy and third-party notices;
- pinned VideoClaw through `upstream/video-claw.lock.json`;
- implemented safe deterministic `tools/vendor_videoclaw.py`;
- vendored exactly 195 files from `video-claw/video-claw`;
- preserved upstream MIT license and provenance;
- added automated vendoring workflow;
- added Linux + Windows CI for bootstrap and imported application builds.

### UV Studio-owned runtime boundary

- added `tools/uv_dev.py` as the stable repository-root development launcher;
- root launcher resolves backend/frontend without requiring contributors to know `vendor/` internals;
- launcher supports `paths`, `backend`, `frontend` and `health-smoke`;
- health smoke starts the real FastAPI process, calls `/api/health` over HTTP, validates `status=ok`, and terminates the process;
- added Windows `.venv` setup and root launch scripts;
- added `docs/DEVELOPMENT.md`;
- added launcher/unit tests;
- kept the vendored application unchanged in this slice.

## Verified Stage 0 baseline

### Initial imported application

GitHub Actions CI run `31387868725` succeeded on Ubuntu and Windows:

- bootstrap tests;
- imported backend compile/install/import;
- frontend `npm ci`;
- Next.js production build.

Automated vendoring run `31387677332` succeeded and committed the pinned baseline.

### UV Studio runtime smoke

GitHub Actions run `31388566191` verified on Ubuntu and Windows:

- UV Studio-owned Python launcher compiles;
- all unit tests pass;
- root paths resolve correctly;
- backend requirements install;
- backend imports without API credentials;
- `python tools/uv_dev.py health-smoke` starts the backend and successfully receives real HTTP health response;
- frontend dependencies install;
- Next.js production build succeeds.

## What works now

- exact upstream baseline is reproducible;
- provenance and licenses are preserved;
- development can resume from repository state across chats;
- backend/frontend are buildable on Windows and Linux;
- UV Studio can start/probe the backend from repository root;
- Windows developers have root-level setup/backend/frontend scripts;
- no model/API credentials are required for startup smoke tests.

## What does not work yet

- there is no UV Studio long-lived Project Store;
- existing upstream session JSON is not the product project model;
- Recipe Registry does not exist yet;
- Capability Bridge/OpenClaw integration does not exist yet;
- music-video, dubbing and range-edit recipes are not implemented yet;
- product UI/branding still largely comes from the pinned upstream application;
- final end-user desktop packaging is Stage 9 work.

## Current risks

1. Keep product state independent from upstream chat/session persistence.
2. Avoid editing the large upstream film orchestrator into a universal controller.
3. Keep new UV Studio code outside/above `vendor/` whenever practical.
4. Provider-specific code must not spread into product domain logic.
5. Stage 1 Project Store must remain small/local and not turn into a premature cloud/database platform.

## Last verified repository facts

- `main` contains Stage 0 bootstrap squash commit `af24ed11d899ee1f459571c5d774b7ac9ad6d1ca`;
- current Stage 0 runtime-smoke CI: run `31388566191`, successful Ubuntu + Windows HTTP smoke and builds;
- vendored file count: 195;
- upstream source SHA: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`.

## Development invariant

Before any chat ends, update this file to the actual repository state. Do not describe future work here as completed.