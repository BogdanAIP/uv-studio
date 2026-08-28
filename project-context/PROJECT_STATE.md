# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: agent-stage17-adversarial-assurance -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is lifecycle-idle after the bounded research slice `agent-stage17-adversarial-assurance` merged through PR #73 as `d1413e5753c24f207faf5a20828f891c14f53aa0`.

The accepted production Agent baseline remains Stage 17 / PR #71 (`c3ca3c33f89f67fad97081f889934669e34befa5`). PR #73 adds verification infrastructure only and does not change production Agent semantics or canonical authorities.

The exact final review head `14e4bde2f40a652fca361d9982ba772143e7fbf0` passed CI #3583 (`33124024674`) across all five permanent jobs, including Ubuntu/Windows bootstrap unit suites with the six curated mutation cases and Ubuntu/Windows browser user-outcome app-baseline.

## Accepted assurance baseline

The Stage-16/17 adversarial-assurance pilot now provides:

- isolated temporary-copy mutation execution with no checkout-source mutation;
- exact target path and SHA-256 source binding;
- one named guarantee, exact replacement and exact existing detector per curated mutant;
- baseline-pass proof before mutant execution;
- fresh-process detector execution;
- distinct `KILLED`, `SURVIVED` and harness/source-binding `ERROR` outcomes;
- six accepted Stage-17 mutants killed on both Ubuntu and Windows through the ordinary unit suite;
- regression proof that report output cannot be written inside the repository root.

The initial guarantees cover persistence-time role revalidation, delegation/persistence context freshness, reserved delegation namespace protection, Plan-bound provenance classification and exact AgentHarness/Project Store/Planner authority for injected Stage-17 coordinators.

## Authority stack unchanged

Project Store, Production Semantic Core, canonical Timeline, Studio/Application Commands, AgentHarness, Stage-16 Planner/Plan/Task/Skill authority, Stage-17 functional role/provenance factoring, Model Registry, Generation Job/Attempt authority and Capability Registry/D-017 remain unchanged. The assurance runner is test infrastructure only.

## Known limitations

The accepted assurance layer is curated rather than exhaustive. Background-worker concurrency, lease/heartbeat, stale-ownership and restart-recovery mutants are intentionally absent until the production D-066 layer 4 runtime exists.

## Handoff

The next product slice is `studio-v2-agent-background-execution`: D-066 layer 4, bounded background Agent work through the existing durable Agent Task and Generation Job authorities, with explicit worker ownership, lease/heartbeat and restart-safe recovery.
