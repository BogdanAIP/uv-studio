# Project State

<!-- uv-active-slice: fix-runtime-security-boundary -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 3.5 — Runtime Independence & Security

**Last verified `main` baseline:** `13ae5b101109dead4c493d2aa8582f1db64ad4e3`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio is a local-first, provider-neutral video-production foundation with a product-owned canonical Project Store, Recipe Registry, Production Policy, Capability Registry, explicit execution authorization, bounded MCP/local/native adapters and early targeted existing-video mechanics.

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

PR #21/D-024 corrected the roadmap so application-wide runtime trust, dependency ownership and representative real-media evidence gate later product intelligence. Stage 4 is now separated into mechanical proof, edit intelligence and the complete user workflow.

## Stable capabilities on `main`

- canonical project create/read/update with schema validation and atomic persistence;
- portable `.uvproj.zip` export/import with checksums, staged validation and traversal protection;
- provider-neutral Recipe Registry and Production Policy;
- Capability Registry with explicit availability/locality/cost facts and fail-closed selection;
- D-017 exact one-shot authorization inside UV Studio capability execution;
- exact direct-MCP bindings, bounded stdio execution, project-file contracts and portable provenance;
- exact native VideoClaw Edge TTS compatibility path;
- local FFprobe/FFmpeg media probe, timeline assembly, range extraction and range replacement;
- Linux/Windows unit, API, real HTTP smoke and frontend production-build matrix;
- D-023 repository-owned multi-agent development contract;
- D-024 runtime/security and real-media gating roadmap.

Completed slice history is recorded in `PROJECT_HISTORY.md`. Prioritized engineering debt is recorded in `ENGINEERING_BACKLOG.md`.

## Active Stage 3.5 security work

The current slice is replacing the inherited application-wide VideoClaw runtime boundary with a UV Studio-owned boundary without editing the pinned vendor snapshot.

Implemented on the active slice so far:

- machine runtime settings belong under UV Studio-owned `data/config` rather than the vendored source tree;
- public runtime settings and provider secrets are stored separately;
- provider secret fields are write-only through the new configuration API and reads expose only boolean configured/not-configured state;
- public configuration cannot contain `api_key` fields;
- secret replacement does not require sending the previous value and explicit `null` is required to clear a key;
- local server host configuration is restricted to loopback;
- allowed browser origins are explicit and wildcard CORS is rejected;
- `uv_studio.server` is now an independent FastAPI root rather than `app = upstream_app`;
- legacy VideoClaw sandbox, workflow, pipeline and raw configuration routers are not mounted by default;
- a small read-only `/api/stages` compatibility endpoint remains UV Studio-owned without importing the workflow engine;
- the root `.gitignore` defensively excludes transitional `vendor/videoclaw-app/backend/config.yaml`;
- Settings UI uses separate `secret_updates` and never receives an existing raw credential;
- focused unit/API tests cover secret separation, loopback/CORS restrictions and absence of legacy remote execution routes.

## Security invariant after this slice

The slice is complete only when the exact final head proves through the normal app route table that:

- raw provider credentials do not appear in configuration HTTP responses;
- machine secrets do not become normal files in the vendor source tree or portable projects;
- arbitrary browser origins are not granted CORS access;
- legacy provider-generating routes cannot bypass product authorization because they are not part of the default app boundary;
- local/free UV Studio capabilities remain available without extra consent;
- Linux/Windows unit, API, HTTP and frontend build regressions remain green.

## Remaining important engineering gaps

### Dependency ownership

`requirements-uv.txt` still does not own the complete UV Studio runtime dependency contract. The next Stage 3.5 slice must separate UV Studio core dependencies from optional provider/runtime extras and repair frontend dependency/lint health.

### Development lifecycle

D-023 still needs an explicit post-merge/idle handoff state so `main` cannot retain a merged PR as the declared active slice indefinitely.

### Project portable-state enforcement

Canonical reference paths are validated, but free-form `settings`, `extensions` and reference `metadata` still need proportionate typed portability enforcement for future durable feature models.

### Real media verification

Real encoded-media golden E2E for `video.extract_range` and `video.replace_range` remains the Stage 4A gate after Stage 3.5 dependency ownership.

### Media-edit scalability

Current reinsertion creates a whole lossless FFV1/FLAC intermediate. It remains the correctness foundation, not the final repeated-edit state model; non-destructive edit decisions are still planned.

### Frontend user outcome

Projects UI exists, but targeted range selection, context, brief/review state, preview, accept/reject and final export are not yet a complete Stage 4C user workflow.

## Next implementation slice

After the current runtime security boundary is merged, execute `fix-dependency-ownership` from `NEXT_TASK.md` before real-media golden work or `RangeContinuityBrief`.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
