# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-background-execution -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in review for Stage 18 slice `studio-v2-agent-background-execution` on branch `stage-18/agent-background-execution`, PR #75, starting from lifecycle-closed main merge `39c80fabb596f2dce76a473a7f1947a06de3cb36`.

The accepted production Agent baseline is merged through Stage 17 / PR #71 (`c3ca3c33f89f67fad97081f889934669e34befa5`). The curated Stage-16/17 adversarial-assurance pilot merged through PR #73 as `d1413e5753c24f207faf5a20828f891c14f53aa0` and remains verification infrastructure rather than a runtime authority.

## Stage 18 implementation under review

D-066 layer 4 adds bounded background Agent execution without introducing another scheduler, task graph, project authority, mutation authority or provider-execution authority.

The current implementation:

- keeps the existing Stage-16 durable `AgentPlanRecord` / `AgentTaskRecord` lifecycle as orchestration truth;
- stores project-scoped worker lease records under the existing `tasks/` authority with bounded claim generations/history;
- persists only a digest of the bearer lease token; the raw token exists only in the ephemeral `AgentBackgroundClaim` and is excluded from `repr`;
- binds each lease to exact task/worker/generation, bounded Agent observation context, exact canonical-state digest, input/target, frozen policy and deterministic recovery correlation;
- persists the claim-time policy once through the existing Stage-16 append-only execution-evidence authority and reloads that evidence before dispatch, heartbeat, commit and finalization rather than trusting caller-supplied policy;
- reuses the existing re-entrant cross-process `ProjectTaskRecordStore.project_lock` as the one shared project mutation fence rather than adding another lock authority;
- holds that shared fence across complete Production and Timeline semantic read/validate/build/ProjectUnitOfWork commit sequences, while ProjectUnitOfWork history/snapshot/write operations use the same fence;
- holds the same fence across Generation prepare, same-key idempotency lookup, D-017 consumption and durable Job reservation; `GenerationJobManager.create_or_reuse` also uses the shared fence, while long provider execution remains outside it;
- keeps `AgentContextBuilder.digest` as a bounded observation digest and separately hashes exact `project.json`, `production/**/*.json` and `timeline/**/*.json` bytes for commit freshness;
- splits foreground's long Agent critical section into short claim/finalize sections while reusing Stage-16 trace and committed-effect recovery contracts;
- never redispatches ambiguous RUNNING work: reopen first reconciles exact correlated trace, ProjectUnitOfWork or Generation Job evidence;
- preserves Stage-17 delegation references through the same durable Plan/Task/Trace path;
- provides a bounded `AgentBackgroundWorker` facade (`run_once` / `run_until_blocked`) without autonomous polling or a second scheduler;
- makes no autonomous-product readiness claim without a later real Studio surface and D-067 proof.

## Current proof

The base Stage-18 regression and acceptance suites prove successful background execution/reopen, exclusive ownership, lease expiry/reclaim, post-commit recovery without replay, cancellation/dependency semantics, Generation Job identity, Stage-17 provenance, bearer-token non-persistence, forged policy/correlation rejection and heartbeat extension.

The first focused Codex review of exact head `e4e632322e9a28244f26b02bef3580c67feceace` returned three valid P1 findings:

1. cross-process Production/Timeline TOCTOU;
2. non-atomic Generation same-key lookup / D-017 consumption / Job reservation;
3. incomplete Timeline freshness when the bounded Agent observation digest is used as an exact concurrency token.

All three are now addressed at the existing shared authorities rather than patched only inside Agent. Focused P1 regressions prove:

- independent Production runtimes serialize full read/modify/commit and both edits survive;
- independent Timeline runtimes serialize full read/modify/commit and both edits survive;
- a real `spawn` multiprocessing test exercises the OS project fence between independent Python processes;
- concurrent same-key Generation submissions resolve to one durable Job with one authorization consumption;
- a Timeline clip timing edit can intentionally leave the bounded Agent context digest unchanged while the separate exact canonical digest still rejects the stale background claim and preserves the user edit.

The P1 regression set and full unit suite have passed on both Ubuntu and Windows in the review-fix series, including the real spawn process proof. The final synchronized review head still requires all five permanent jobs and repeat exact-head Codex review before merge.

## Key recovery boundary

A process loss after a canonical commit but before Agent success bookkeeping must recover from the existing correlated ProjectUnitOfWork or exact Generation Job evidence without replay. A process loss before canonical commit must not create false success evidence. A stale lease, forged claim or changed canonical state may never authorize a mutation.

The shared project fence protects only bounded canonical command / reservation critical sections. Long external provider execution remains outside that lock and owned by the Generation Job Manager.

## Review / merge gate

PR #75 is non-draft and remains in review. Merge requires:

1. synchronized current architecture/context authorities describing the cross-runtime fence and exact canonical freshness boundary;
2. all five permanent CI jobs green on the final exact review head;
3. the original three P1 threads answered against that exact SHA;
4. repeat focused Codex review of the same exact SHA;
5. no unresolved concrete review findings or review threads.

## Known limitations

This slice is internal Agent infrastructure. It does not implement automatic critic/repair, human takeover/edit/resume, long-form autonomy, provider-private schedulers as UV truth, or a user-visible autonomous Agent UI.

## Product-first sequencing gate

D-070 changes the work order without discarding Stage 18. After Stage 18 closes, UV Studio must stop adding Agent-autonomy layers long enough to inventory and compress the overlapping legacy product architecture and define one user-visible golden vertical.

D-066 layers 5-7 remain accepted target architecture, but they are deferred until the architecture-compression and golden-vertical gates defined by D-070 are satisfied.

## Handoff

After Stage 18 is accepted, merged and lifecycle-closed, the next slice is `architecture-compression-inventory`.

That slice is behavior-preserving inventory work only: map exact callers and migration/deletion gates for Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 6/8 surfaces and related legacy composition; define the migration order; and make the `micro_drama` project-to-export path the first named product vertical. D-066 layer 5 evaluation/repair is deferred until the D-070 product-first gates are satisfied.
