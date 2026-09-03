# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The latest material repair head `386e5a8794dd79e53f1920a78cd06a8657a857fb` passed CI #4574 (`33724694161`) **5/5 SUCCESS**. Context-only synchronization head `963e85123dd36ac4e6bef84ed5d702c915a3fc00` then passed authoritative synchronized Draft CI #4577 (`33730244111`) **5/5 SUCCESS** across all five permanent jobs. A live review-thread listing after that gate shows every inline thread resolved, including follow-up P2s `PRRT_kwDOT0Lyms6ezYYl` and `PRRT_kwDOT0Lyms6ezYYn`.

No runtime, test, schema or product behavior changed after synchronized Draft gate #4577. Commit `526419717c4e2f7f8e1471d7880f4bcb798b4589` changes only `ACTIVE_SLICE.json` lifecycle from `draft` to `review`; this commit records the corresponding review freeze.

## Follow-up root-staging repairs

### Mounted crash-safe FFmpeg adapter

P2 `PRRT_kwDOT0Lyms6ezYYl` identified that the actually mounted `CrashSafeLocalFFmpegRangeAdapter` still used unleased root staging. Regression-first commit `30e148d7e0575ab8b5390c2aff1006fd15877c70` covers the mounted path. Runtime commit `386e5a8794dd79e53f1920a78cd06a8657a857fb` moves its FFconcat manifest and `timeline.assemble` output to shared lease-backed root staging while preserving the existing project-fence and managed-publication marker authority. Reply `3922278700` records exact evidence; the thread is resolved.

### Lease allocation versus startup recovery

P2 `PRRT_kwDOT0Lyms6ezYYn` identified a cross-runtime window between visible lease creation and ownership-lock establishment. Regression-first commit `30e148d7e0575ab8b5390c2aff1006fd15877c70` covers the interleaving. Runtime commit `8d22cf3eae23050630b84958bfcbb73c45daf172` serializes only the short lease allocation/recovery inspection critical section across runtimes, preventing recovery from unlinking an allocation before ownership is established. Long producer work remains outside that coordination lock and producer output paths remain absent until written. Reply `3922279936` records exact evidence; the thread is resolved.

## Verification

Material head `386e5a8794dd79e53f1920a78cd06a8657a857fb`, CI #4574 (`33724694161`): **5/5 SUCCESS**.

Synchronized Draft head `963e85123dd36ac4e6bef84ed5d702c915a3fc00`, CI #4577 (`33730244111`): **5/5 SUCCESS**:

- development-context — SUCCESS;
- Ubuntu full unit suite — SUCCESS;
- Windows full unit suite — SUCCESS;
- Ubuntu app-baseline — SUCCESS including API, real-media, frontend and browser Product Truth;
- Windows app-baseline — SUCCESS including API, pinned media toolchain, real-media, frontend and browser Product Truth.

Live PR identity immediately before refreeze remained open, Draft, mergeable, BASE `52be1939eca51d7147990288cfc6258b023c2cd2`, HEAD `963e85123dd36ac4e6bef84ed5d702c915a3fc00`. The live thread listing showed zero unresolved inline threads.

## Existing Stage-19 authority retained

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, source FFprobe publication-fence exception, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, Generation digest/provenance authority, exact redo-chain reachability, reserved Generation namespace, canonical Generation path/lineage, same-ID Generation authority immutability, direct Redo binary validation and immediate-next-action Product Truth behavior.

Root staging/leases and the root coordination lock are transient runtime coordination only. They add no Project, Production, Generation, media-history or Undo/Redo authority and remain outside `.uvproj.zip` payloads.

## Review freeze

The review freeze consists only of context lifecycle/evidence commits after successful Draft gate #4577. No material runtime/test/schema/product mutation is allowed while this freeze remains current. Any supported material finding requires returning PR #89 and lifecycle to Draft before repair.

## Next required action

1. synchronize the PR body with this final review freeze and exact frozen HEAD;
2. mark PR #89 Ready without changing that frozen HEAD;
3. require a **new post-Ready exact-head CI 5/5** distinct from all Draft/refreeze runs;
4. re-resolve live BASE/HEAD/mergeability and zero unresolved threads;
5. perform the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
6. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with clean live identity and zero unresolved findings.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
