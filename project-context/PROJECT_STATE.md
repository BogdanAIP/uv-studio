# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-agent-background-execution -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in the draft Stage 18 slice `studio-v2-agent-background-execution` on branch `stage-18/agent-background-execution`, starting from lifecycle-closed main merge `39c80fabb596f2dce76a473a7f1947a06de3cb36`.

The accepted production Agent baseline is merged through Stage 17 / PR #71 (`c3ca3c33f89f67fad97081f889934669e34befa5`). The curated Stage-16/17 adversarial-assurance pilot merged through PR #73 as `d1413e5753c24f207faf5a20828f891c14f53aa0` and remains verification infrastructure rather than a runtime authority.

## Stage 18 goal

Implement D-066 layer 4 bounded background Agent execution without introducing another scheduler, task graph, project authority or provider-execution authority.

The implementation direction is:

- keep the existing Stage-16 durable `AgentPlanRecord` / `AgentTaskRecord` lifecycle as orchestration truth;
- use project-scoped durable worker lease records under the existing `tasks/` authority;
- acquire/heartbeat/finalize leases through existing cross-runtime task-record locking and compare-and-swap;
- split foreground's long critical section into short claim/finalize sections while preserving exact Stage-16 context, policy, execution-evidence, trace and committed-effect recovery semantics;
- fence canonical Production/Timeline commits and Generation Job submission against the current live worker ownership so an expired/stolen worker cannot commit after losing authority;
- never silently replay a RUNNING task whose delivery/result is ambiguous: reconcile exact durable trace/transaction/Job evidence first;
- keep background worker/task budgets bounded and retry facts inspectable;
- preserve Stage-17 delegation references through the same durable Plan/Task/Trace path;
- make no autonomous-product readiness claim without a later real Studio surface and D-067 proof.

## Key recovery boundary

A process loss after a canonical commit but before Agent success bookkeeping must recover from the existing correlated ProjectUnitOfWork or exact Generation Job evidence without replay. A process loss before canonical commit must not create false success evidence. A stale lease may never itself authorize a mutation.

## Known limitations

This slice is internal Agent infrastructure. It does not implement automatic critic/repair, human takeover/edit/resume, long-form autonomy, provider-private schedulers as UV truth, or a user-visible autonomous Agent UI.

## Handoff

After Stage 18 is accepted, merged and lifecycle-closed, the next D-066 slice is `studio-v2-agent-evaluate-repair`: bounded critic/evaluation plus dependency-aware local repair over the same Agent authorities.
