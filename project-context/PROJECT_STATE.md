# Project State

<!-- uv-active-slice: fix-dependency-ownership -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 3.5 — Runtime Independence & Security

**Last verified `main` baseline:** `dfa4c6aad1ee08bbe8dc0d715c38e4f889936542`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio is a local-first, provider-neutral video-production foundation with a product-owned canonical Project Store, Recipe Registry, Production Policy, Capability Registry, explicit D-017 execution authorization, bounded MCP/local/native adapters and deterministic targeted existing-video mechanics.

After PR #22 / D-025, UV Studio also owns the default FastAPI security boundary. The complete VideoClaw route table is no longer inherited; unsafe legacy provider/configuration/file/pipeline surfaces fail closed by default, machine provider secrets are write-only and stay outside `vendor/` and canonical projects, browser origins are explicitly restricted, and the server remains loopback-only.

The stable product-owned execution path is:

```text
Canonical Project
  -> Recipe / Production Policy
  -> semantic capability
  -> CapabilityOffer
  -> SelectionPolicy
  -> execution preparation
  -> D-017 authorization when required
  -> exact adapter
  -> portable artifact/provenance
```

Stage 4 mechanical work on `main` provides exact integer-microsecond range extraction and deterministic prepared-replacement reinsertion under D-021/D-022.

## Stable capabilities on `main`

- canonical project create/read/update with atomic persistence and migrations;
- portable `.uvproj.zip` export/import with checksums, staging and traversal protection;
- provider-neutral Recipe Registry and Production Policy;
- Capability Registry with explicit availability/locality/cost facts and fail-closed selection;
- D-017 exact one-shot authorization;
- exact direct-MCP bindings and project-file contracts;
- exact native VideoClaw Edge TTS compatibility path with optional dependency;
- local FFprobe/FFmpeg media probe, assembly, exact range extraction and exact prepared-replacement reinsertion;
- UV Studio-owned FastAPI root and secret-safe machine configuration under D-025;
- Linux/Windows unit, API, real HTTP smoke and frontend production-build matrix;
- D-023 repository-owned multi-agent development contract;
- D-024 runtime/security and real-media gating roadmap.

## Active Stage 3.5 dependency-ownership work

The current slice removes the remaining implicit dependency on `vendor/videoclaw-app/backend/requirements.txt` and brings frontend lint/security dependency health under CI.

Implemented on the active branch so far:

- `requirements-uv.txt` explicitly declares the UV Studio core runtime instead of only MCP;
- `requirements-uv-dev.txt` layers test-only HTTP transport on the core requirements;
- provider/heavy optional packages such as OpenAI, DashScope, Edge TTS and Playwright stay out of the baseline;
- `scripts/setup-dev.ps1` installs only UV Studio-owned development requirements and runs `pip check`;
- CI core bootstrap installs only `requirements-uv.txt` and imports `uv_studio.server` without vendor dependency installation;
- app-baseline installs only `requirements-uv-dev.txt` before API/HTTP tests; the pinned VideoClaw snapshot is compiled for provenance but not imported as the application runtime;
- dependency-contract unit tests guard against reintroducing the vendor requirements file or provider SDKs into core;
- frontend `next` and `eslint-config-next` are being aligned on the security-patched 16.2.12 line;
- ESLint flat config is being migrated to the supported Next 16 configuration;
- a GitHub runner has regenerated the npm lockfile; integration of that generated lock and final lint/audit gates are still in progress.

## Remaining Stage 3.5 gaps

### Frontend lock/lint/audit

The regenerated `package-lock.json` must be integrated, the temporary generation job removed, then `npm ci`, `npm run lint`, `npm audit --audit-level=high` and production build must all become real CI gates. Any actual lint violations must be fixed rather than globally ignored.

### Development-state lifecycle

D-023 still needs an explicit post-merge/idle handoff state so `main` cannot retain a merged PR as the declared active slice indefinitely.

### Project portable-state enforcement

Free-form `settings`, `extensions` and reference `metadata` still need proportionate typed portability enforcement for future durable feature models.

## Next product proof after Stage 3.5

After dependency ownership is merged, Stage 4A must prove the existing extraction/reinsertion mechanics against deterministic real encoded media on Ubuntu and Windows. That work is the single handoff in `NEXT_TASK.md`.

`RangeContinuityBrief` remains intentionally after real-media mechanical evidence; Stage 4C remains the later complete timeline/preview/accept/export user workflow.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
