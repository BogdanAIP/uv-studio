# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen Ready head `6c991dc646c491fb954df4a19a53c8a963123197` passed authoritative post-Ready CI #4563 (`33723641170`) **5/5 SUCCESS**. During the mandatory final live thread recheck, two new P2 review threads appeared on that exact head. Both survived direct code falsification, so PR #89 and lifecycle were returned to Draft before material repair.

Both follow-up findings are now repaired on material head `386e5a8794dd79e53f1920a78cd06a8657a857fb`, which passed CI #4574 (`33724694161`) **5/5 SUCCESS**. Both P2 threads were answered with exact regression/repair/CI evidence and resolved. A synchronized Draft gate is still required after this context/PR-body synchronization before refreeze.

## Follow-up root-staging repairs

### Mounted crash-safe FFmpeg adapter

Thread `PRRT_kwDOT0Lyms6ezYYl` identified that the actually mounted `CrashSafeLocalFFmpegRangeAdapter` still used unleased `NamedTemporaryFile` root staging in its `timeline.assemble` override even though the lower adapter had been migrated.

Regression-first commit `30e148d7e0575ab8b5390c2aff1006fd15877c70` extends permanent Stage-19 root-staging coverage to this mounted path. Runtime commit `386e5a8794dd79e53f1920a78cd06a8657a857fb` moves both its FFconcat manifest and timeline output to the shared lease-backed root-staging helpers while preserving the existing arbitrary-path publication marker and shared project-fence semantics.

### Lease allocation versus startup recovery

Thread `PRRT_kwDOT0Lyms6ezYYn` identified an interprocess window between creation of a visible lease sidecar and acquisition of its ownership lock. Another runtime could otherwise acquire and remove that visible unlocked sidecar before the allocator established ownership, leaving a producer holding an unlinked lease inode that future startup recovery could not discover.

Regression-first commit `30e148d7e0575ab8b5390c2aff1006fd15877c70` adds deterministic allocation/recovery interleaving coverage. Runtime commit `8d22cf3eae23050630b84958bfcbb73c45daf172` serializes only the short root lease allocation/recovery inspection critical section across runtimes. Recovery can no longer observe an allocation between sidecar publication and ownership-lock establishment. Long producer work remains outside that coordination lock; the producer output path is still not pre-created.

## Verification

Exact material/test head `386e5a8794dd79e53f1920a78cd06a8657a857fb` passed CI #4574 (`33724694161`) **5/5 SUCCESS**:

- development-context — SUCCESS;
- Ubuntu full unit suite — SUCCESS, including the new root lease interleaving and mounted-adapter regressions;
- Windows full unit suite — SUCCESS, including the Windows lock path;
- Ubuntu app-baseline — SUCCESS including API integration, real-media, frontend lint/audit/build and browser Product Truth;
- Windows app-baseline — SUCCESS including API integration, pinned media toolchain, real-media, frontend lint/audit/build and browser Product Truth.

P2 `PRRT_kwDOT0Lyms6ezYYl` was answered in reply `3922278700` and resolved. P2 `PRRT_kwDOT0Lyms6ezYYn` was answered in reply `3922279936` and resolved. No additional material finding was present in the live thread listing used for this synchronization.

Prior evidence remains historical support only:

- root-staging material head `e3aa1a58036d901f8047a87ac6a39c442757a3c1`: CI #4547 (`33720004954`) 5/5;
- synchronized Draft head `a77c5f35cf42da44a5526b38dadde3027827ed10`: CI #4557 (`33723007026`) 5/5;
- previous frozen Ready head `6c991dc646c491fb954df4a19a53c8a963123197`: post-Ready CI #4563 (`33723641170`) 5/5.

## Existing Stage-19 authority retained

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, source FFprobe publication-fence exception, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, Generation digest/provenance authority, exact redo-chain reachability, reserved Generation namespace, canonical Generation path/lineage, same-ID Generation authority immutability, direct Redo binary validation and immediate-next-action Product Truth behavior.

The root-staging mechanism remains transient coordination only. It adds no Project, Production, Generation, media-history or Undo/Redo authority, and remains outside `.uvproj.zip` payloads.

## Next required action

1. synchronize the PR body with material head `386e5a8794dd79e53f1920a78cd06a8657a857fb`, both repaired/resolved P2s and CI #4574 evidence;
2. require a new synchronized Draft-head CI **5/5** after this context-only synchronization;
3. recheck zero unresolved inline threads and exact live BASE/HEAD identity;
4. perform a context-only refreeze from `draft` to `review` with no runtime/test/schema/product mutation;
5. mark PR #89 Ready on the exact frozen HEAD and require a **new post-Ready exact-head CI 5/5**;
6. perform the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
7. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0`, clean live identity and zero unresolved threads.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
