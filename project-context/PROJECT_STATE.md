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
- never redispatches ambiguous RUNNING work: reopen first reconciles exact correlated trace, ProjectUnitOfWork or Generation Job evidence;
- records pre-dispatch claim loss as bounded retry history while RUNNING delivery uncertainty remains fail-closed/recovery-only;
- preserves Stage-17 delegation references through the same durable Plan/Task/Trace path;
- provides a bounded `AgentBackgroundWorker` facade (`run_once` / `run_until_blocked`) without autonomous polling or a second scheduler;
- makes no autonomous-product readiness claim without a later real Studio surface and D-067 proof.

## Current proof

The Stage-18 regression and acceptance suites prove:

- successful background execution and reopen;
- exclusive worker ownership and stale/expired-worker fencing;
- safe reclaim after a pre-dispatch crash with bounded lease history;
- post-commit/pre-trace recovery without replay;
- cancellation and existing Stage-16 dependency blocking semantics;
- exact Generation Job identity/history across reopen without moving provider execution out of the existing Job Manager;
- Stage-17 delegation provenance through background execution and reopen;
- live-lease reopen behavior and lease-expiry reconciliation;
- durable lease JSON and claim `repr` do not expose the raw bearer token;
- forged policy digests cannot rebind execution authority;
- heartbeat extends the same lease generation/token authority;
- canonical context changes after claim refuse the background commit.

Security hardening at `eddd70086b1b15dc297a44dffc9d56b4ef7387d7` passed all five permanent CI jobs in run #3611. The synchronized draft head `8901e79d51dfeb2ad8510bea5a418e13392c723a`, including the direct authority tests and current architecture documentation, passed all five permanent jobs in CI run #3619 on Ubuntu and Windows, including app-baseline/browser E2E.

The review transition itself creates a new exact review head. That exact head must pass the same five permanent checks before merge.

## Key recovery boundary

A process loss after a canonical commit but before Agent success bookkeeping must recover from the existing correlated ProjectUnitOfWork or exact Generation Job evidence without replay. A process loss before canonical commit must not create false success evidence. A stale lease, forged claim or changed canonical context may never authorize a mutation.

## Review / merge gate

PR #75 is non-draft and frozen for review. Merge requires:

1. all five permanent CI jobs green on the exact review head;
2. current architecture/context authorities synchronized with Stage 18 review state;
3. focused Codex review against that exact review head for correctness, security, lease fencing, recovery, races and TOCTOU behavior;
4. no unresolved concrete review findings or review threads;
5. every resulting code change, if any, receives a fresh exact-head CI run and a repeat Codex review when material.

## Known limitations

This slice is internal Agent infrastructure. It does not implement automatic critic/repair, human takeover/edit/resume, long-form autonomy, provider-private schedulers as UV truth, or a user-visible autonomous Agent UI.

## Handoff

After Stage 18 is accepted, merged and lifecycle-closed, the next D-066 slice is `studio-v2-agent-evaluate-repair`: bounded critic/evaluation plus dependency-aware local repair over the same Agent authorities.
