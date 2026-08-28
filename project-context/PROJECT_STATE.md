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
- binds each lease to the exact task record, worker, generation, context digest, input digest, target and frozen-policy digest;
- persists the claim-time policy once through the existing Stage-16 append-only execution-evidence authority and reloads that evidence before dispatch, heartbeat, commit and finalization rather than trusting caller-supplied policy;
- acquires, heartbeats and releases leases through the existing cross-runtime task-record lock and compare-and-swap boundary;
- splits foreground's long critical section into short claim/finalize sections while reusing Stage-16 context, frozen-policy, execution-evidence, trace and committed-effect recovery contracts;
- fences canonical Production/Timeline commits and Generation Job submission against the exact live worker lease and exact RUNNING task, refusing stale/expired ownership, policy substitution and stale execution context;
- binds recovery correlation to durable execution-evidence identity rather than trusting the ephemeral claim;
- never redispatches ambiguous RUNNING work: reopen first reconciles exact correlated trace, ProjectUnitOfWork or Generation Job evidence;
- records pre-dispatch claim loss as bounded retry history while RUNNING delivery uncertainty remains fail-closed/recovery-only;
- preserves Stage-17 delegation references through the same durable Plan/Task/Trace path;
- provides a bounded `AgentBackgroundWorker` facade (`run_once` / `run_until_blocked`) without autonomous polling or a second scheduler;
- makes no autonomous-product readiness claim without a later real Studio surface and D-067 proof.

## Current proof

The Stage-18 regression and acceptance suites prove successful background execution/reopen, exclusive ownership, lease expiry/reclaim, post-commit recovery without replay, cancellation/dependency semantics, Generation Job identity, Stage-17 provenance, bearer-token non-persistence, forged policy/correlation rejection, heartbeat extension and stale observed-context refusal.

Security hardening at `eddd70086b1b15dc297a44dffc9d56b4ef7387d7` passed all five permanent CI jobs in run #3611. The synchronized draft head `8901e79d51dfeb2ad8510bea5a418e13392c723a` passed all five permanent jobs in CI run #3619. Review head `e4e632322e9a28244f26b02bef3580c67feceace`, including recovery-correlation hardening, also passed all five permanent jobs before Codex review.

## Codex review blockers

Focused Codex review of exact head `e4e632322e9a28244f26b02bef3580c67feceace` returned three concrete P1 findings that block merge:

1. Production/Timeline `ProjectUnitOfWork` commits are not serialized across independent `ProjectStore` runtimes, so a foreign process can mutate canonical state after the Agent freshness check and before the prepared background transaction writes.
2. Generation idempotency lookup, D-017 consumption and Job reservation are not one cross-runtime atomic section, allowing duplicate Jobs for one idempotency key under concurrent Agent and GUI/API submission.
3. `AgentContextBuilder.digest` is an observation digest rather than an exact canonical Timeline freshness token; clip timing/source-range/reference mutations can be omitted from that digest.

The Stage-18 review-fix scope is therefore narrowly expanded to `uv_studio/projects/transactions.py`, `uv_studio/generation/jobs.py` and `uv_studio/generation/service.py` in addition to the existing Agent/tests/docs/context paths. The intended fix reuses the existing re-entrant cross-process `ProjectTaskRecordStore.project_lock` as the shared critical section for canonical transaction and generation authorities; no second lock/scheduler/project authority is introduced. Background freshness will additionally bind exact canonical Project/Production/Timeline JSON bytes rather than overloading the bounded Agent observation digest.

## Key recovery boundary

A process loss after a canonical commit but before Agent success bookkeeping must recover from the existing correlated ProjectUnitOfWork or exact Generation Job evidence without replay. A process loss before canonical commit must not create false success evidence. A stale lease, forged claim or changed canonical state may never authorize a mutation.

## Review / merge gate

PR #75 is non-draft and remains in review. Merge requires:

1. all three P1 Codex findings fixed at the existing canonical authorities rather than patched only inside Agent;
2. focused regression tests proving cross-runtime Production/Timeline serialization, Generation idempotency atomicity and full Timeline freshness detection;
3. all five permanent CI jobs green on the resulting exact review head;
4. architecture/context authorities synchronized;
5. repeat focused Codex review on the new exact head;
6. no unresolved concrete review findings or review threads.

## Known limitations

This slice is internal Agent infrastructure. It does not implement automatic critic/repair, human takeover/edit/resume, long-form autonomy, provider-private schedulers as UV truth, or a user-visible autonomous Agent UI.

## Handoff

After Stage 18 is accepted, merged and lifecycle-closed, the next D-066 slice is `studio-v2-agent-evaluate-repair`: bounded critic/evaluation plus dependency-aware local repair over the same Agent authorities.
