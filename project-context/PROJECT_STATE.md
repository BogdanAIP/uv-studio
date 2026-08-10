# Project State

**Updated:** 2026-08-10  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 0 — Clean baseline  
**Active branch:** `stage-0/bootstrap`  
**Main status:** initial README only; Stage 0 bootstrap is ready for PR/merge.

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

## Repository work completed

- initialized `main` with README;
- created `stage-0/bootstrap` branch;
- added `DEVELOPMENT_PROTOCOL.md`, `ROADMAP.md`, decisions and persistent handoff files;
- added UV Studio MIT license and third-party notices;
- pinned VideoClaw with `upstream/video-claw.lock.json`;
- implemented deterministic/safe `tools/vendor_videoclaw.py`;
- added vendoring tests including destination/path safety and upstream-license preservation;
- added automated GitHub Actions vendoring workflow;
- vendored exactly 195 files from the modern VideoClaw subtree into `vendor/videoclaw-app`;
- generated `.uv-upstream.json` provenance and preserved `UPSTREAM_LICENSE`;
- added Linux + Windows CI for bootstrap tests and imported application baseline.

## Verified baseline

GitHub Actions CI run `31387868725` completed successfully on 2026-08-10.

Verified on both Ubuntu and Windows:

- bootstrap Python compiles;
- vendoring unit tests pass;
- upstream lock validates;
- imported backend compiles;
- backend requirements install;
- `api_server` imports without API credentials;
- frontend dependencies install with `npm ci`;
- Next.js production build succeeds.

Automated vendoring workflow run `31387677332` also completed successfully and committed the pinned baseline.

## What works now

- repository can reproducibly reconstruct the exact selected VideoClaw baseline;
- upstream provenance/license are preserved automatically;
- imported backend/frontend are buildable on Linux and Windows;
- development state is durable across ChatGPT chat changes;
- CI catches baseline breakage before architecture changes.

## What does not work yet

- there is no UV Studio top-level launcher/setup command yet;
- baseline CI imports the server but does not yet start it and probe `/api/health` over HTTP;
- user-facing branding/product terminology still reflects VideoClaw in vendored UI/code;
- long-lived UV Studio Project Store does not exist yet;
- Recipe Registry does not exist yet;
- Capability Bridge/OpenClaw integration does not exist yet;
- music-video, dubbing and range-edit UV Studio recipes are not implemented yet.

## Current risks

1. Avoid editing the large upstream film orchestrator into a universal controller.
2. Keep future UV Studio code outside/above vendored upstream where practical so upstream provenance remains clear.
3. The current upstream session storage is insufficient for Stage 1 Project Store.
4. Provider-specific code must not spread into future domain logic.
5. Establish a real HTTP smoke/start path before beginning structural cleanup.

## Last verified repository facts

- vendored source provenance: `vendor/videoclaw-app/.uv-upstream.json`;
- imported file count: 195;
- upstream source SHA: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- first successful cross-platform application baseline CI: run `31387868725`;
- automated vendoring run: `31387677332`.

## Development invariant

Before any chat ends, update this file to the actual repository state. Do not describe future work here as completed.