# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in Draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `a0974c73fcf48c409c07d7e456b78315544b4018` returned two surviving findings. Development-context validation classified both as `CONFIRMED`, so the previous review/Ready CI is stale for merge authority and material repair is required before refreeze.

## Confirmed fresh-review repairs

1. **P1 — crash-safe managed publication.** The shared project fence prevents concurrent archive snapshots from observing split state while a publisher is alive, but it is not durable across process/power loss. `timeline.assemble`, WebVTT and named Generation can crash after canonical `os.replace` and before all owning metadata/state is durable. Generation can additionally crash between artifact registration, Take registration and Job success. The repair must add a durable publication record before canonical byte publication, startup reconciliation that completes or safely removes an interrupted publication without replaying provider work, and archive fail-closed behavior while any unreconciled publication record remains.
2. **P2 — fresh ProjectUnitOfWork commits must not persist schema v1.** Historical undo/redo snapshots still require migration-before-validation so exact legacy bytes can be restored, but new `commit()` input must validate the raw/current schema and reject schema-v1 `project.json` rather than validating a migrated projection and writing the original v1 bytes canonically.

## Existing implemented boundary retained

The repair must preserve the already accepted behavior:

- canonical Project schema v2 with schema-v1 project/archive readability;
- exact historical schema-v1 ProjectUnitOfWork undo/redo bytes;
- explicit legacy recipe compatibility identity;
- archive raw-schema validation, exact streamed ZIP hashing and technical-lock symlink fail-closed behavior;
- source upload staging with the intentional FFprobe-inside-fence exception;
- long `timeline.assemble`, WebVTT and Generation render/provider work outside canonical project trees;
- Generation Job idempotency/authorization/retry semantics and durable Job provenance across user Undo;
- Production Take/Timeline authority and the immediate-next-action Product Truth UI repair.

## Repair design boundary

The P1 repair uses a UV-owned durable publication journal under project `tasks/` with IDs outside the `job_*` namespace. A prepared record exists before canonical byte publication. Normal completion removes it only after all owning metadata/state is durable. Startup recovery reconciles prepared records before abandoned Generation Jobs are failed. Artifact-only publishers can complete their ProjectReference registration from the durable record; Generation recovery can finish missing artifact/Take/Job transitions without another provider call. Archive export must refuse to snapshot any project that still has a prepared publication record after acquiring the shared project fence.

The publication journal is recovery/coordination state, not a second Project/Production/Generation authority and not user Undo/Redo history.

## Verification required before refreeze

The repaired Draft head must prove at minimum:

- fresh schema-v1 `ProjectUnitOfWork.commit()` input is rejected while historical v1 undo/redo still round-trips exact bytes;
- crash simulation after canonical move but before metadata leaves a durable publication record and startup recovery removes or completes the split state deterministically;
- WebVTT and arbitrary-path `timeline.assemble` recovery cannot be silently archived as unregistered files;
- Generation recovery handles bytes-only, artifact-only and artifact+Take/Job-running intermediate durable states without provider replay, ending in one coherent artifact + Take + succeeded Job or a safe rollback where completion is impossible;
- archive export fails closed while a prepared publication record cannot be reconciled;
- existing concurrency, cancellation, idempotency, D-017 authorization, real-media and Product Truth tests remain green on Ubuntu and Windows.

## Final gate after repair

After material repair and exact-head 5/5 Draft CI, synchronize docs/context, freeze lifecycle back to `review`, return PR #89 to Ready without changing the frozen head, require authoritative post-Ready exact-head CI 5/5, resolve all review threads, and run another fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0. Merge only after a `CURRENT` zero-finding result and final exact base/head/check/thread re-resolution.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
