# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of the prior frozen head `a0974c73fcf48c409c07d7e456b78315544b4018` returned two surviving findings. Development-context independently classified both as `CONFIRMED`; that review and all CI on that old head are stale for merge authority.

The repaired runtime/tests are complete through `5ad22668038870c019961536530b3f3a8ce7a78b`. Documentation synchronization is complete on Draft head `6a3fa91ee1acb3ab52d5c28bc5ea3a7b2d765411`. Exact-head CI #4261 and the later #4262 both completed **5/5 SUCCESS** on that Draft head across development-context, Ubuntu/Windows bootstrap, Ubuntu/Windows app-baseline, API integration, pinned real-media verification, frontend lint/audit/build and browser Product Truth. This commit changes only durable lifecycle/context from `draft` to `review`; runtime, tests and architecture documents remain unchanged from the accepted Draft head.

## Confirmed finding repairs

### P1 — crash-safe managed publication

The shared project fence remains the concurrency/snapshot boundary, but crash durability no longer relies on that live OS lock alone.

- `timeline.assemble` renders outside the canonical project tree. Inside the final shared project fence, immediately before arbitrary-path canonical `os.replace`, it writes a durable `tasks/pub_<uuid>.json` managed-publication marker. Normal completion removes the marker only after the ProjectReference is durable. After process loss, archive export fails closed while a marker remains; startup reconciliation clears a stale marker for an already registered output or moves unregistered bytes outside the project tree before clearing it.
- WebVTT `artifacts/sub_<uuid>.vtt` and Generation `artifacts/generated_attempt_<uuid>.*` are self-identifying current publisher outputs. Crash-left unregistered bytes are quarantined at the Project Store root on startup and are rejected by archive export before reconciliation. Ordinary unrelated unregistered project files remain portable.
- Generation recovery first restores any prepared ProjectUnitOfWork journal, then reconciles publication state. If no durable artifact reference exists, generated orphan bytes are quarantined and the abandoned running Job becomes failed/retryable. If the exact artifact ProjectReference is already durable, recovery validates its bytes/provenance, reuses or creates the missing Take through the normal Production authority, then marks the same Job/Attempt succeeded without provider replay. Archive export rejects a Generation artifact until the durable Job has matching succeeded attempt/output/Take identity.
- Source upload keeps its established exception: request streaming/staging remains outside the fence, while final move, FFprobe validation, portable metadata and source registration remain inside the shared fence. Historical managed-name archive detection remains fail-closed for an incomplete source publication.

The publication marker/quarantine mechanism is recovery/coordination evidence only. It does not replace ProjectReference, Production Take, Generation Job, ProjectUnitOfWork or user Undo/Redo authority.

### P2 — fresh ProjectUnitOfWork commit cannot downgrade schema

Fresh `ProjectUnitOfWork.commit()` now checks the raw schema of staged `project.json` before the shared migration-based semantic validator. New canonical Project writes require schema v2 and cannot submit schema-v1 bytes, validate only a migrated projection and persist the original v1 payload.

Historical undo/redo keeps the separate compatibility behavior: exact schema-v1 snapshots are migrated only for validation while original historical bytes remain authoritative for restoration. Permanent regression coverage proves v2 commit -> exact v1 undo -> exact v2 redo.

## Focused crash-boundary evidence

Permanent regressions cover:

- fresh schema-v1 `ProjectUnitOfWork.commit()` rejection while exact historical v1 undo/redo remains valid;
- bytes-only Generation restart quarantining `generated_attempt_*` bytes and failing the running Job without provider replay;
- artifact-only Generation restart completing the missing Take and Job success from durable artifact evidence;
- artifact + Take + running Job restart reusing the existing Take and completing Job success without duplication;
- archive refusal for Generation artifact/Take while the matching Job still claims `RUNNING`, followed by successful export after reconciliation;
- WebVTT `sub_<uuid>` bytes without ProjectReference being quarantined by startup reconciliation;
- actual `LocalFFmpegAdapter` `timeline.assemble` process-loss simulation after canonical byte move leaving its durable marker, blocking archive, and quarantining the arbitrary output on recovery;
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
- long FFmpeg/provider/render work outside canonical project trees where designed;
- Generation idempotency, D-017 authorization, retry/cancellation and durable Job provenance across user Undo;
- Production Take/Timeline authority;
- immediate-next-action Product Truth UI behavior after the Production refresh repair.

## Verification evidence

- Prior frozen review head `a0974c73fcf48c409c07d7e456b78315544b4018`: stale after confirmed P1/P2.
- Intermediate material repair head `a31f9cfd2dc1d16e1ea940c5c3d62542f6780e5f`: CI #4255 **5/5 SUCCESS**.
- Focused publisher crash-boundary tests added through `5ad22668038870c019961536530b3f3a8ce7a78b`.
- Final Draft material/docs head `6a3fa91ee1acb3ab52d5c28bc5ea3a7b2d765411`: CI #4261 **5/5 SUCCESS** and CI #4262 **5/5 SUCCESS**.
- All existing inline GitHub review threads were resolved before this freeze.

## Final review gate

Lifecycle is now `review`. The frozen exact head must remain unchanged except for PR metadata operations.

Before merge, PR #89 requires:

1. Ready-for-review state on this exact frozen head;
2. authoritative post-Ready exact-head CI with all five required checks green;
3. no unresolved review threads;
4. a new fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0 with zero surviving findings;
5. final re-resolution of PR base/head identity immediately before merge.

Any material code, test or behavior change invalidates this review cycle and requires returning lifecycle to `draft`.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
