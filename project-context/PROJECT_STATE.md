# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen Ready head `6c991dc646c491fb954df4a19a53c8a963123197` passed authoritative post-Ready CI #4563 (`33723641170`) **5/5 SUCCESS**. During the mandatory final live thread recheck, two new P2 review threads appeared on that exact head. Both survived direct code falsification, so PR #89 and lifecycle were returned to Draft before any material repair.

## Confirmed follow-up staging P2s

### Mounted crash-safe FFmpeg adapter still stages without leases

Thread `PRRT_kwDOT0Lyms6ezYYl` points to `uv_studio/capabilities/adapters/crash_safe_ffmpeg.py`. The package-level `LocalFFmpegAdapter` in `adapters/__init__.py` actually instantiates `CrashSafeLocalFFmpegRangeAdapter`; its overridden `timeline.assemble` still creates `.uv-ffconcat-*` and `.uv-timeline-assemble-*` via `tempfile.NamedTemporaryFile`. Therefore the leased implementation added to `local_ffmpeg.py` does not cover the mounted arbitrary-path assembly path, and hard process loss can still leave unrecoverable root staging.

### Lease sidecar is visible before ownership lock is established

Thread `PRRT_kwDOT0Lyms6ezYYn` points to `_allocate_leased_path()` in `uv_studio/projects/root_staging.py`. Allocation currently creates the lease pathname with `open("x+b")`, writes/fsyncs it, and only then acquires the OS lock. A concurrent startup recovery can acquire that newly visible unlocked sidecar while the staging file is still absent, release its recovery lock and unlink the pathname. The allocator can then acquire its still-open file descriptor after that unlink and proceed with a lease inode that is no longer discoverable by future startup cleanup. This defeats the intended crash-recovery authority and can again leave large root staging permanently.

Both findings are concrete recovery/liveness defects introduced by the root-staging repair. The previous post-Ready CI remains valid evidence for the old frozen head but cannot authorize merge after these supported findings.

## Existing root-staging authority retained

The repair direction remains correct: current Generation, source-upload, WebVTT, FFconcat and timeline-assemble staging should use exact UV-owned root names plus OS-lock-backed coordination; producer output paths must remain non-existent until written; startup cleanup must remain root-only/non-recursive; live cooperating runtimes must be preserved; unknown/malformed/legacy-unleased state must not be guessed stale.

Existing ProjectReference, Production Take, Generation Job/Attempt, ProjectUnitOfWork/Redo, publication-marker and archive authorities remain unchanged. Root staging/leases are coordination only, not canonical Project state.

## Prior evidence retained

- material/test head `e3aa1a58036d901f8047a87ac6a39c442757a3c1`: CI #4547 (`33720004954`) **5/5 SUCCESS**;
- synchronized Draft head `a77c5f35cf42da44a5526b38dadde3027827ed10`: CI #4557 (`33723007026`) **5/5 SUCCESS**;
- previous frozen Ready head `6c991dc646c491fb954df4a19a53c8a963123197`: post-Ready CI #4563 (`33723641170`) **5/5 SUCCESS**;
- previous P2 `PRRT_kwDOT0Lyms6ex9SS` is resolved;
- current unresolved threads are intentionally `PRRT_kwDOT0Lyms6ezYYl` and `PRRT_kwDOT0Lyms6ezYYn` until the follow-up repair has exact-head evidence.

## Next required action

1. add regression-first proof that the actually mounted `CrashSafeLocalFFmpegRangeAdapter` uses leased FFconcat/timeline staging and that hard-kill cleanup can reclaim those names;
2. close the lease-allocation race so recovery cannot unlink a sidecar before ownership is durably established, with a deterministic cross-runtime/interleaving regression;
3. run exact material-head CI 5/5 on Ubuntu/Windows;
4. synchronize docs/context/PR body, obtain synchronized Draft CI 5/5, then answer and resolve both P2 threads with exact evidence;
5. verify zero unresolved threads, refreeze context-only to `review`, mark Ready, and require a new post-Ready exact-head CI 5/5;
6. only then launch the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
7. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0`, clean live identity and zero unresolved threads.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
