# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `d38aec58f491f46db79f1ee2423d53d8f2ce4a7d` passed post-Ready CI #4516 (`33716978812`) **5/5 SUCCESS**. A new inline P2 review thread `PRRT_kwDOT0Lyms6ex9SS` then identified that current publishers could leave root-level `.uv-*` staging behind after hard process termination. The finding survived falsification, so PR #89 was returned to Draft before any material repair.

## Root-staging P2 repair

The repair does not blindly delete `.uv-*` names. That would create a cross-runtime data-loss race in which a newly started UV Studio process could delete staging still owned by another live runtime.

Current root staging instead uses a shared lease authority in `uv_studio/projects/root_staging.py`:

- Generation: `.uv-generation-attempt_<uuid>-<uuid><suffix>`;
- source upload: `.uv-source-upload-src_<uuid>.<uuid>.upload`;
- WebVTT: `.uv-webvtt-sub_<uuid>-<uuid>.vtt`;
- FFconcat: `.uv-ffconcat-<uuid>.txt`;
- timeline assembly: `.uv-timeline-assemble-art_<uuid>-<uuid><suffix>`.

Each current staging name has a `<name>.lease` sidecar. Allocation creates and fsyncs the sidecar, holds a one-byte OS lock for the complete staging lifetime, and deliberately does not pre-create the producer output path. POSIX uses `flock`; Windows uses `msvcrt.locking`. Normal completion removes remaining staging bytes and releases/removes the lease. Hard process termination releases the OS lock automatically.

Application startup now calls `recover_stale_root_staging(store.root)` before existing per-project Generation/publication recovery. Recovery is root-only and non-recursive. It removes only exact current UV-owned staging whose lease can be acquired non-blockingly; a still-locked lease proves another cooperating runtime is active and is preserved. Unknown or malformed root files, project directories, recovery quarantine files, symlinks/non-files and exact-looking legacy staging with no lease are preserved rather than guessed stale.

The producer migrations preserve the existing publication authorities: long work remains outside canonical project directories; Generation/FFmpeg still receive a non-existent output path; the short final consequence-bearing publication remains under the shared project fence; ProjectReference/Production Take/Generation Job authorities are unchanged. Root staging and leases remain transient coordination state outside canonical Project state and outside `.uvproj.zip` archives.

## Repair commits and verification

Regression-first and repair sequence includes:

- `66d94950f7b9b7ffe9b47140f5803a03d88ec8ec` — expose root staging recovery gap;
- `0f577e522b54857a2fd89cc9b1525ed71eda7de5` — producer-safe root staging lease authority;
- `9c6be484e07174a9d952eee4c646ee6c7f10494e` — WebVTT lease migration;
- `708e6930d6f42c6f586c49286829c075fd8eac66` — source-upload lease migration;
- `c93bec95474170d6e9182775b5b6a8bc468f2eb9` — Generation lease migration;
- `54aa5ba2a7a394d2187ee833c1f089f1fed028af` — FFconcat/timeline assemble lease migration;
- startup lifespan hook runs root recovery before project recovery;
- `76e641e5ad5117e9825638a2ca226c1cdff20e28` — lease-aware cross-platform regression and startup-order proof;
- `e3aa1a58036d901f8047a87ac6a39c442757a3c1` — restores two media GET routes accidentally omitted during the source-upload file rewrite; its diff contains only those two routes.

Exact material/test head `e3aa1a58036d901f8047a87ac6a39c442757a3c1` passed CI #4547 (`33720004954`) **5/5 SUCCESS**:

- development-context — SUCCESS;
- Ubuntu full unit suite — SUCCESS, including leased root-staging regression;
- Windows full unit suite — SUCCESS, including the `msvcrt.locking` lease path;
- Ubuntu app-baseline — SUCCESS including API integration, HTTP probe, real-media, frontend lint/audit/build and browser Product Truth;
- Windows app-baseline — SUCCESS including API integration, pinned media toolchain, real-media, frontend lint/audit/build and browser Product Truth.

Documentation synchronization:

- `76e997340b5be75feefcfe5034779598d25d2379` — Project Store root-staging lease/recovery contract;
- `796faffa2d71f5bcf35edbe9ef077cbb82198850` — archive boundary for root staging/leases.

The P2 thread remains intentionally unresolved until the synchronized Draft head has exact 5/5 evidence.

## Existing Stage-19 authority retained

All previous Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, Generation digest authority, exact redo-chain reachability, reserved Generation namespace, canonical Generation path/lineage, same-ID Generation authority immutability and immediate-next-action Product Truth behavior.

The root-staging lease mechanism adds no canonical media, Project, Production, Generation or Undo/Redo authority.

## Next required action

1. obtain synchronized Draft-head CI **5/5** after documentation/context synchronization;
2. reply to and resolve P2 `PRRT_kwDOT0Lyms6ex9SS` with exact material and synchronized-Draft evidence;
3. confirm zero unresolved inline review threads and clean live BASE/HEAD identity;
4. perform one context-only refreeze from `draft` to `review` with no runtime/test/schema/product mutation;
5. mark PR #89 Ready on that exact frozen HEAD and require a **new post-Ready exact-head CI 5/5**;
6. perform the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
7. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with clean live BASE/HEAD/CI/thread identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
