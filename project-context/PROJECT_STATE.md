# Project State

**Updated:** 2026-08-10  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 0 — Clean baseline  
**Active branch:** `stage-0/bootstrap`  
**Main status:** repository initialized; no product baseline merged yet.

## Product definition

UV Studio is a universal video production and editing studio. It must support different task-specific recipes rather than forcing all media through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities.

## Chosen technical direction

- Base candidate selected after repository/code comparison: modern `video-claw/video-claw` application from `HITsz-TMG/VideoClaw`.
- Upstream commit currently pinned for Stage 0 analysis: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276` (2026-07-17).
- Use modern FastAPI backend + Next.js frontend + pipeline/task/model capability infrastructure.
- Do not treat VideoClaw's large film orchestrator as the universal core.
- New product workflows should be independent recipes/pipelines.
- Future provider expansion should go through a semantic Capability Bridge; OpenClaw is the preferred replaceable runtime candidate.
- `musical-mv-storyboard` is intended to remain a separate specialized module integrated later through an adapter.

## Repository work completed

- initialized `main` with README;
- created `stage-0/bootstrap` branch;
- added cross-chat development protocol;
- added full roadmap;
- started durable project context.

## What works now

Repository management and development handoff structure only.

No UV Studio application code has been imported yet.

## What does not work yet

- backend/frontend are not present in `uv-studio`;
- no baseline build/test exists;
- no CI exists;
- no upstream source manifest exists yet;
- no Windows run verification has been performed in this repository;
- no product Project Store/Recipe Registry/Capability Bridge exists yet.

## Current risks

1. Importing more of VideoClaw than is actually required would bring historical/demo coupling into the new product.
2. The current upstream session storage is too weak to become the long-lived Project Store.
3. The large film orchestrator must remain isolated rather than becoming the universal product control flow.
4. Provider-specific code must not spread into future domain logic.
5. Stage 0 must establish reproducible tests before structural cleanup.

## Last verified facts

- `BogdanAIP/uv-studio` exists, is public, empty before initialization, default branch `main`, and connected GitHub permissions include push/admin.
- upstream VideoClaw latest commit observed during bootstrap: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`.
- upstream modern application contains `backend/`, `frontend/`, Windows `install.bat`, pipeline registry, task/artifact persistence and model capability metadata.

## Development invariant

Before any chat ends, update this file to the actual repository state. Do not describe future work here as completed.