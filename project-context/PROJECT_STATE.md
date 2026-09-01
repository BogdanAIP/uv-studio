# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in Draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `a0974c73fcf48c409c07d7e456b78315544b4018` returned two surviving findings. Development-context independently classified both as `CONFIRMED`, so that review and its Ready CI remain stale for merge authority.

The material repair is now implemented. Runtime/test work through head `5ad22668038870c019961536530b3f3a8ce7a78b` preserves the existing Stage-19 scope and adds crash/restart reconciliation plus fresh-commit schema enforcement. Earlier material head `a31f9cfd2dc1d16e1ea940c5c3d62542f6780e5f` passed CI #4255 5/5 on Ubuntu/Windows, including unit/API, real-media, frontend build and browser Product Truth. Additional publisher-level crash-boundary regressions were then added, so #4255 is evidence for the repair but not the final exact-head acceptance run.

## Confirmed finding repairs

### P1 — crash-safe managed publication

The shared project fence remains the concurrency/snapshot boundary, but crash durability no longer relies on that live OS lock alone.

- `timeline.assemble` still renders outside the canonical project tree. Inside the final shared project fence, immediately before arbitrary-path canonical `os.replace`, it writes a durable `tasks/pub_<uuid>.json` managed-publication marker. Normal completion removes the marker only after the ProjectReference is durable. After process loss, archive export fails closed while a marker remains; startup reconciliation either clears a stale marker for an already registered output or moves unregistered bytes outside the project tree before clearing it.
- WebVTT `artifacts/sub_<uuid>.vtt` and Generation `artifacts/generated_attempt_<uuid>.*` are self-identifying current publisher outputs. A crash-left unregistered file is moved to a quarantine path at the Project Store root on startup. Archive export also rejects these self-identifying bytes while they are unregistered. Ordinary unrelated unregistered project files remain portable.
- Generation recovery first runs ProjectUnitOfWork prepared-journal recovery, then publication reconciliation. If no durable artifact reference exists, generated orphan bytes are quarantined and the abandoned running Job becomes failed/retryable. If the exact artifact ProjectReference is already durable, recovery validates its bytes/provenance, reuses or creates the missing Take through the normal Production authority, then marks the same Job/Attempt succeeded without provider replay. Archive export rejects a Generation artifact until the durable Job has matching succeeded attempt/output/Take identity.
- Source upload keeps its established exception: request streaming/staging remains outside the fence, while final move, FFprobe validation, portable metadata and source registration remain inside the shared fence. Historical managed-name archive detection remains fail-closed for an incomplete source publication.

The publication marker/quarantine mechanism is recovery/coordination evidence only. It does not replace ProjectReference, Production Take, Generation Job, ProjectUnitOfWork or user Undo/Redo authority.

### P2 — fresh ProjectUnitOfWork commit cannot downgrade schema

Fresh `ProjectUnitOfWork.commit()` now checks the raw schema of staged `project.json` before the shared migration-based semantic validator. New canonical Project writes therefore require schema v2 and cannot submit schema-v1 bytes, validate only a migrated projection and persist the original v1 payload.

Historical undo/redo keeps the separate compatibility behavior: exact schema-v1 snapshots are migrated only for validation, while the original historical bytes remain authoritative for restoration. The permanent v1 transaction regression still proves v2 commit -> exact v1 undo -> exact v2 redo.

## Focused crash-boundary evidence

Permanent regressions now cover:

- fresh schema-v1 `ProjectUnitOfWork.commit()` rejection while exact historical v1 undo/redo remains valid;
- bytes-only Generation restart: orphan `generated_attempt_*` bytes leave the project tree and the running Job becomes failed without provider replay;
- artifact-only Generation restart: the missing Take and Job success are completed from durable artifact evidence;
- artifact + Take + running Job restart: the existing Take is reused and Job success is completed without duplication;
- archive refusal for Generation artifact/Take while the matching Job still claims `RUNNING`, followed by successful export after reconciliation;
- WebVTT `sub_<uuid>` bytes without ProjectReference being quarantined by startup reconciliation;
- real `LocalFFmpegAdapter` `timeline.assemble` process-loss simulation after canonical byte move: the arbitrary output remains accompanied by its durable marker, archive fails closed, and recovery quarantines the bytes rather than silently archiving them;
- direct managed-publication marker recovery for both unregistered and already registered arbitrary-path output;
- ordinary unrelated unregistered artifact files remaining portable;
- existing deterministic archive-vs-publication concurrency tests remaining intact.

## Existing Stage-19 boundary retained

The repair preserves:

- canonical Project schema v2 with schema-v1 project/archive readability;
- exact historical recipe identity and exact historical schema-v1 transaction/archive bytes;
- archive raw-schema matching and exact streamed ZIP hashing;
- technical lock-file symlink fail-closed handling;
- source upload staging with intentional FFprobe-inside-fence behavior;
- long FFmpeg/provider/render work outside canonical project trees where already designed;
- Generation idempotency, D-017 authorization, retry/cancellation and durable Job provenance across user Undo;
- Production Take/Timeline authority;
- immediate-next-action Product Truth UI behavior after the Production refresh repair.

## Verification state

- Frozen review head before fresh findings: `a0974c73fcf48c409c07d7e456b78315544b4018` — stale after confirmed findings.
- Material crash/schema repair head `a31f9cfd2dc1d16e1ea940c5c3d62542f6780e5f` — CI #4255: **5/5 SUCCESS**.
- Focused publisher crash-boundary tests added through `5ad22668038870c019961536530b3f3a8ce7a78b`.
- This documentation synchronization changes the Draft head again, so a new exact-head 5/5 CI run is required before lifecycle can return to `review`.

## Final gate after repair

Before refreeze:

1. exact current Draft head passes all five required CI jobs;
2. Project Store/archive/current-state docs match the implemented crash-recovery contract;
3. PR remains open, Draft, on exact base `52be1939eca51d7147990288cfc6258b023c2cd2`;
4. no confirmed review thread/finding remains unaddressed.

Then perform one context-only `draft -> review` freeze, return PR #89 to Ready without changing that frozen head, require authoritative post-Ready exact-head CI 5/5, verify no unresolved review threads, and run a new fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0. Merge only after a `CURRENT` zero-finding result and final exact base/head/check/thread re-resolution.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
