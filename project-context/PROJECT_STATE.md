# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-agent-background-execution -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in the draft Stage 18 slice `studio-v2-agent-background-execution` on branch `stage-18/agent-background-execution`, PR #75, starting from lifecycle-closed main merge `39c80fabb596f2dce76a473a7f1947a06de3cb36`.

The accepted production Agent baseline is merged through Stage 17 / PR #71 (`c3ca3c33f89f67fad97081f889934669e34befa5`). The curated Stage-16/17 adversarial-assurance pilot merged through PR #73 as `d1413e5753c24f207faf5a20828f891c14f53aa0` and remains verification infrastructure rather than a runtime authority.

## Stage 18 implementation in draft

D-066 layer 4 adds bounded background Agent execution without introducing another scheduler, task graph, project authority or provider-execution authority.

The current implementation:

- keeps the existing Stage-16 durable `AgentPlanRecord` / `AgentTaskRecord` lifecycle as orchestration truth;
- stores project-scoped worker lease records under the existing `tasks/` authority with bounded claim generations/history;
- acquires, heartbeats and releases leases through the existing cross-runtime task-record lock and compare-and-swap boundary;
- splits foreground's long critical section into short claim/finalize sections while reusing Stage-16 context, frozen-policy, execution-evidence, trace and committed-effect recovery contracts;
- fences canonical Production/Timeline commits and Generation Job submission against the exact live worker lease and exact RUNNING task, refusing stale/expired ownership and stale execution context;
- never redispatches ambiguous RUNNING work: reopen first reconciles exact correlated trace, ProjectUnitOfWork or Generation Job evidence;
- records pre-dispatch claim loss as bounded retry history while RUNNING delivery uncertainty remains fail-closed/recovery-only;
- preserves Stage-17 delegation references through the same durable Plan/Task/Trace path;
- provides a bounded `AgentBackgroundWorker` facade (`run_once` / `run_until_blocked`) without autonomous polling or a second scheduler;
- makes no autonomous-product readiness claim without a later real Studio surface and D-067 proof.

## Current proof

The first Stage-18 regression suite proves exclusive worker ownership, expired-worker fencing, safe reclaim after a pre-dispatch crash, successful background execution/reopen, post-commit/pre-trace recovery without replay, and cancellation blocking descendants on both Linux and Windows unit bootstrap for the initial six-case set.

The expanded acceptance set additionally exercises exact Generation Job identity/history across reopen, Stage-17 delegation provenance through background execution, live-lease reopen behavior and downstream cancellation after a real dependency failure. Those newer checks remain under draft CI until the current head is stabilized.

## Key recovery boundary

A process loss after a canonical commit but before Agent success bookkeeping must recover from the existing correlated ProjectUnitOfWork or exact Generation Job evidence without replay. A process loss before canonical commit must not create false success evidence. A stale lease may never itself authorize a mutation.

## Known limitations

This slice is internal Agent infrastructure. It does not implement automatic critic/repair, human takeover/edit/resume, long-form autonomy, provider-private schedulers as UV truth, or a user-visible autonomous Agent UI.

## Handoff

After Stage 18 is accepted, merged and lifecycle-closed, the next D-066 slice is `studio-v2-agent-evaluate-repair`: bounded critic/evaluation plus dependency-aware local repair over the same Agent authorities.
