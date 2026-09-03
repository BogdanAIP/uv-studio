# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `d38aec58f491f46db79f1ee2423d53d8f2ce4a7d` passed post-Ready CI #4516 (`33716978812`) **5/5 SUCCESS**. A later inline P2 `PRRT_kwDOT0Lyms6ex9SS` identified crash-left root-level staging. The PR was correctly returned to Draft before material repair. That P2 is now repaired, verified, replied to and resolved; a live review-thread check after resolution shows zero unresolved inline threads.

No runtime, test, schema or product behavior changed after the successful synchronized Draft gate recorded below. The commits after that gate are context-only lifecycle/refreeze commits.

## Root-staging P2 repair

Current Generation, source-upload, WebVTT, FFconcat and timeline-assemble root staging uses a shared lease authority in `uv_studio/projects/root_staging.py` rather than unsafe prefix deletion.

Each exact current UV-owned staging name has a `<name>.lease` sidecar. Allocation creates and fsyncs the sidecar, holds a one-byte OS lock for the complete staging lifetime and deliberately does not pre-create the producer output path. POSIX uses `flock`; Windows uses `msvcrt.locking`. Hard process termination releases the OS lock automatically.

Application startup invokes `recover_stale_root_staging(store.root)` before existing project-scoped publication and Generation recovery. Recovery is root-only and non-recursive. It removes only exact current staging whose lease can be acquired non-blockingly. A still-locked lease proves another cooperating runtime is active and is preserved. Unknown/malformed files, project directories, recovery quarantine files, symlinks/non-files and exact-looking legacy staging without a lease remain untouched rather than being guessed stale.

The producer migrations retain the existing publication authorities: long work remains outside canonical project directories; Generation/FFmpeg still receive a non-existent output path; consequence-bearing final publication remains under the shared project fence; ProjectReference, Production Take, Generation Job/Attempt, ProjectUnitOfWork/Redo and archive authority remain unchanged. Root staging and leases are transient coordination only and are not part of canonical Project state or `.uvproj.zip` payloads.

## Repair evidence

Regression/repair sequence includes:

- `66d94950f7b9b7ffe9b47140f5803a03d88ec8ec` — expose root staging recovery gap;
- `0f577e522b54857a2fd89cc9b1525ed71eda7de5` — producer-safe root staging lease authority;
- `9c6be484e07174a9d952eee4c646ee6c7f10494e` — WebVTT lease migration;
- `708e6930d6f42c6f586c49286829c075fd8eac66` — source-upload lease migration;
- `c93bec95474170d6e9182775b5b6a8bc468f2eb9` — Generation lease migration;
- `54aa5ba2a7a394d2187ee833c1f089f1fed028af` — FFconcat/timeline assemble lease migration;
- `76e641e5ad5117e9825638a2ca226c1cdff20e28` — lease-aware cross-platform regression and startup-order proof;
- `e3aa1a58036d901f8047a87ac6a39c442757a3c1` — restore the two source/artifact media GET routes accidentally omitted during a full source-upload file rewrite; this commit adds only those routes.

Exact material/test head `e3aa1a58036d901f8047a87ac6a39c442757a3c1` passed CI #4547 (`33720004954`) **5/5 SUCCESS** on Ubuntu/Windows, including full unit suites, API integration, real-media, frontend lint/audit/build and browser Product Truth.

Documentation synchronization:

- `76e997340b5be75feefcfe5034779598d25d2379` — Project Store root-staging lease/recovery contract;
- `796faffa2d71f5bcf35edbe9ef077cbb82198850` — archive boundary for root staging/leases.

The first synchronized Draft head `c41da89addb469eac48b0a65220edf7856b44bd5` passed CI #4553 (`33720676160`) **5/5 SUCCESS**. A later PR-body-only edit accidentally removed the mandatory `## Changes` heading, so CI #4554 (`33720709846`) failed only `development-context`; all four code/test jobs still succeeded. The live PR body was corrected, and context-only commit `a77c5f35cf42da44a5526b38dadde3027827ed10` generated a fresh synchronize event.

Exact synchronized Draft head `a77c5f35cf42da44a5526b38dadde3027827ed10` then passed authoritative CI #4557 (`33723007026`) **5/5 SUCCESS**:

- development-context — SUCCESS;
- Ubuntu full unit suite — SUCCESS;
- Windows full unit suite — SUCCESS;
- Ubuntu app-baseline — SUCCESS including API, real-media, frontend and browser Product Truth;
- Windows app-baseline — SUCCESS including API, pinned media toolchain, real-media, frontend and browser Product Truth.

P2 top-level comment `3921210117` was answered with exact material and synchronized-Draft evidence in reply `3921717659`, then thread `PRRT_kwDOT0Lyms6ex9SS` was resolved. A subsequent live thread listing shows every inline thread resolved.

## Existing Stage-19 authority retained

All previous Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility preservation, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, source FFprobe publication-fence exception, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, Generation digest/provenance authority, exact redo-chain reachability, reserved Generation namespace, canonical Generation path/lineage, same-ID Generation authority immutability, direct Redo binary validation and immediate-next-action Product Truth behavior.

The root-staging lease mechanism adds no second Project, Production, Generation, media-history or Undo/Redo authority.

## Review freeze

`ACTIVE_SLICE.json` was changed only from lifecycle `draft` to `review` after the synchronized Draft gate. This file records the corresponding review freeze. No runtime/test/schema/product mutation is allowed while this freeze remains current; a supported finding requires returning the PR/context to Draft before material repair.

## Next required action

1. synchronize the PR body with the final frozen review HEAD while preserving exactly one mandatory `## Changes` section;
2. mark PR #89 Ready without changing that frozen HEAD;
3. require a **new post-Ready exact-head CI 5/5** distinct from all Draft runs;
4. re-resolve live BASE/HEAD/mergeability and zero unresolved threads;
5. perform the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
6. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with clean live BASE/HEAD/CI/thread identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
