# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-agent-functional-subagents -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 17 is the active draft slice on branch `stage-17/agent-functional-subagents`, PR #71, created from lifecycle-closed `main` commit `145395fe58db811c39bc1099188e15c58736174f` after Stage 16 / PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2`.

The Stage-16 closure CI #3444 (`33073018940`) completed successfully across all five permanent jobs, so this slice starts from a clean idle authority state.

## Stage-17 goal

D-066 layer 3 adds **functional subagents** over the already merged Agent infrastructure:

```text
Stage 15
  Context Builder / Action Catalog / Policy / Trace
Stage 16
  Planner / Plan / durable Tasks / bounded Skills / foreground coordinator
Stage 17
  bounded functional roles: explore / plan / media / critic
```

The roles must consume the existing UV Agent contracts rather than creating another project graph, task authority, command registry, permission system, trace store or provider runtime. Any canonical mutation remains executable only through the existing Stage-16 Task/AgentHarness path and the existing Production / Timeline / Generation authorities.

## Required boundary

- `explore` observes bounded canonical/Agent context and may return structured findings/references only;
- `plan` may produce bounded structured planning proposals that still pass the existing deterministic `AgentPlanner` validation before durable Plan creation;
- `media` may reason about/select media- or generation-related approved Agent actions, but cannot call providers or mutate the project directly;
- `critic` may inspect a plan/task/result/trace and return bounded evaluation findings, but automatic repair/evaluate loops remain D-066 layer 5;
- role delegation remains foreground/synchronous in this slice;
- background workers, leases/heartbeats, autonomous polling, evaluate/repair loops, human takeover/edit/resume and long-form autonomy remain later layers.

## Product Truth boundary

Stage 17 remains internal Agent infrastructure unless a real Studio surface is deliberately added with D-067 backend/frontend/browser proof. No user-visible autonomous-Agent readiness claim is made by this slice.

## Next action

Implement the smallest UV-owned role/delegation contract, prove each role is bounded by the existing context/planner/task/skill/action authorities, add restart/trace/reference-safe tests where durable state is involved, and move the PR to review only after the exact head passes all five permanent checks.
