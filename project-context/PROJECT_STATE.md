# Project State

<!-- uv-active-slice: chore-roadmap-runtime-gates -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 3.5 preparation — Runtime Independence & Security

**Last verified `main` baseline:** `3845af01f7c5a6d00f24b1a2dac681e36a66464f`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio is a local-first, provider-neutral video-production foundation with a product-owned canonical Project Store, Recipe Registry, Production Policy, Capability Registry, explicit execution authorization, bounded MCP/local/native adapters and early targeted existing-video mechanics.

The product-owned execution path is already well structured:

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

Stage 4 mechanical work on `main` also provides:

```text
ProjectMediaRange
  -> bounded exact extraction
  -> prepared replacement
  -> deterministic exact reinsertion
```

However, the running application still mounts UV Studio routers onto the complete vendored VideoClaw FastAPI app and the derived frontend still uses legacy VideoClaw configuration/sandbox/pipeline routes. The application-wide runtime boundary therefore does not yet guarantee the same authorization, secret handling and dependency independence as the UV Studio-owned capability path.

## Stable capabilities on `main`

- canonical project create/read/update with schema validation and atomic persistence;
- portable `.uvproj.zip` export/import with checksums, staged validation and traversal protection;
- provider-neutral Recipe Registry and Production Policy;
- Capability Registry with explicit availability/locality/cost facts and fail-closed selection;
- D-017 exact one-shot authorization inside UV Studio capability execution;
- exact direct-MCP bindings, bounded stdio execution, project-file contracts and portable provenance;
- exact native VideoClaw Edge TTS compatibility path;
- local FFprobe/FFmpeg media probe and bounded timeline assembly;
- `video.extract_range` under D-021;
- `video.replace_range` under D-022;
- Linux/Windows unit, API, real HTTP smoke and frontend production-build matrix;
- D-023 repository-owned multi-agent development contract.

Completed slice history is recorded in `PROJECT_HISTORY.md`. Prioritized engineering debt is recorded in `ENGINEERING_BACKLOG.md`.

## Current roadmap correction slice

The repository is correcting development order after a full repository audit found that backend/domain ownership has advanced farther than application/runtime ownership.

The corrected roadmap introduces Stage 3.5 before additional product intelligence and makes two kinds of completion explicit:

- engineering gates for runtime/security/portable-state/real execution;
- user-outcome gates for workflows completed through the product UI rather than manual API calls.

Stage 4 is split into mechanical editing, edit intelligence and the complete user workflow. Real FFmpeg media evidence moves into Stage 4A rather than being deferred to release hardening.

## Highest-priority runtime risks

### P0 — secret exposure and commit-prone provider configuration

The vendored `/api/config` returns the complete VideoClaw configuration, including provider credential fields, and the frontend consumes that route. VideoClaw persists configuration to `vendor/videoclaw-app/backend/config.yaml`, which is not currently protected by the repository root ignore rules. Real credentials must not be used through this path until the Stage 3.5 security slice fixes storage and API semantics.

### P0 — legacy execution can bypass product authorization

D-017 protects UV Studio capability execution, but legacy VideoClaw sandbox/pipeline/provider routes remain mounted on the same application and can invoke upstream model clients without the product-owned authorization preparation/consent flow. The global product invariant is therefore not yet achieved.

### P0 — wildcard browser access to the local backend

The upstream FastAPI app enables wildcard CORS while also exposing mutating configuration, sandbox, file and pipeline APIs. The backend binds to localhost by default, but arbitrary browser origins must not receive unrestricted access to sensitive local APIs.

## Important engineering gaps

### Dependency ownership

`requirements-uv.txt` currently declares only MCP while UV Studio runtime imports are satisfied incidentally by the vendored VideoClaw backend dependency set. Core UV Studio dependencies and optional provider extras need product-owned declarations so optional providers are truly optional.

### Project portable-state enforcement

Canonical reference paths are validated, but free-form `settings`, `extensions` and reference `metadata` do not yet provide a central typed portability/secret contract. New durable models should use explicit versioned schemas rather than unvalidated provider/runtime blobs.

### Real media verification

FFmpeg unit/API tests strongly verify command and failure contracts, but CI does not yet execute `video.extract_range` and `video.replace_range` against representative real encoded CFR/VFR + audio fixtures on Windows and Linux.

### Media-edit scalability

Current deterministic reinsertion produces a whole lossless FFV1/FLAC intermediate. This is appropriate as a correctness foundation but should not become the permanent state model for repeated edits to long compressed sources. Stage 4A must move toward project-owned non-destructive edit decisions with full render at an explicit preview/export gate.

### Frontend

Projects UI exists, but the default production interface remains substantially VideoClaw-derived. Timeline/range selection, bounded context, brief/review state, preview, accept/reject and explicit export are still missing from the targeted-range user outcome.

### Quality gates

The current matrix does not yet enforce frontend lint, browser E2E, measured coverage, Python lint/type checks, dependency audit or real encoded-media assertions.

### Development lifecycle

D-023 validates active-slice/PR consistency during PR events, but `main` can retain a merged PR as the declared active slice. Stage 3.5 includes an idle/handoff lifecycle fix so repository memory remains machine-correct after merge.

## Next implementation slice

After this roadmap correction is merged, execute `fix-runtime-security-boundary` from `NEXT_TASK.md` before `RangeContinuityBrief` or any new provider integration.

The security slice must first close the two P0 boundaries: raw/commit-prone provider secrets and legacy remote execution that bypasses product authorization. Range continuity work remains the next Stage 4 intelligence target after the runtime gate is trustworthy.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
