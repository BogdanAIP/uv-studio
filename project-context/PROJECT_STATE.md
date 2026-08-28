# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: studio-v2-agent-background-execution -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is lifecycle-idle after Stage 18 slice `studio-v2-agent-background-execution` merged through PR #75 as `c5051b975a1ba8e747f453dd0a485cac1e308ba7`.

The accepted production Agent baseline now includes D-066 layer 4 bounded background Agent execution. The curated Stage-16/17 adversarial-assurance pilot from PR #73 remains verification infrastructure rather than a runtime authority.

## Stage 18 merged baseline

D-066 layer 4 adds bounded background Agent execution without introducing another scheduler, task graph, project authority, mutation authority or provider-execution authority.

The merged implementation:

- keeps the existing Stage-16 durable `AgentPlanRecord` / `AgentTaskRecord` lifecycle as orchestration truth;
- stores project-scoped worker lease records under the existing `tasks/` authority with bounded claim generations/history;
- persists only a digest of the bearer lease token; the raw token remains ephemeral;
- binds each lease to exact task/worker/generation, bounded Agent observation context, exact canonical-state digest, input/target, frozen policy and deterministic recovery correlation;
- reloads claim-time policy from the existing append-only Stage-16 execution-evidence authority before dispatch, heartbeat, commit and finalization;
- reuses the existing re-entrant cross-process `ProjectTaskRecordStore.project_lock` as the one shared project mutation fence;
- serializes Production and Timeline semantic mutations, ProjectUnitOfWork commits, existing-project `project.json` writes, direct Production/Timeline saves and freshness-tracked JSON writes beneath `production/` or `timeline/` through that shared fence;
- makes Generation same-key lookup, D-017 consumption and durable Job reservation atomic under the same project fence while keeping long provider execution outside it;
- uses a separate exact canonical digest over `project.json`, `production/**/*.json` and `timeline/**/*.json` for background freshness rather than treating the bounded Agent observation digest as an exact concurrency token;
- reserves background coordinator harness ownership atomically and prevents foreground coordinators from replacing installed background fences;
- never redispatches ambiguous RUNNING work and recovers from exact correlated Trace, ProjectUnitOfWork or Generation Job evidence;
- preserves Stage-17 delegation references through the same durable Plan/Task/Trace path;
- provides bounded caller-driven `run_once` / `run_until_blocked` worker execution without autonomous polling or a second scheduler.

## Verification

The final Stage-18 exact head `4c80bc96512e5ba34b0c3ed973c76c1c7a029568` passed all five permanent CI jobs, including Ubuntu and Windows bootstrap/unit suites and Ubuntu and Windows app-baseline/browser user-outcome suites. The final PR state had all concrete review threads resolved before merge.

Focused regressions cover cross-process Production/Timeline serialization, one-job Generation idempotency with single authorization consumption, exact canonical freshness, foreground/background coordinator ownership, direct canonical-store fencing, arbitrary freshness-tracked Timeline JSON writers and concurrent background-coordinator installation.

## Key recovery boundary

A process loss after a canonical commit but before Agent success bookkeeping must recover from existing correlated ProjectUnitOfWork or exact Generation Job evidence without replay. A process loss before canonical commit must not create false success evidence. A stale lease, forged claim or changed canonical state may never authorize a mutation.

The shared project fence protects bounded canonical command/reservation critical sections only. Long external provider execution remains outside that lock and owned by the Generation Job Manager.

## Known limitations

Stage 18 is internal Agent infrastructure. It does not implement automatic critic/repair, human takeover/edit/resume, long-form autonomy, provider-private schedulers as UV truth, or a user-visible autonomous Agent UI.

## Product-first sequencing gate

D-070 changes the work order without discarding Stage 18. Before adding further D-066 autonomy layers, UV Studio must inventory and compress the overlapping legacy product architecture and then prove one user-visible golden vertical.

D-066 layers 5-7 remain accepted target architecture, but they are deferred until the architecture-compression and golden-vertical gates defined by D-070 are satisfied.

## Handoff

The next slice is `architecture-compression-inventory`.

That slice is behavior-preserving inventory work only: map exact callers and migration/deletion gates for Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 6/8 surfaces and related legacy composition; define the migration order; and make the `micro_drama` project-to-export path the first named product vertical. D-066 layer 5 evaluation/repair remains deferred until the D-070 product-first gates are satisfied.
