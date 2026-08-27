# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: agent-stage17-adversarial-assurance -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in review for the bounded research slice `agent-stage17-adversarial-assurance` on branch `research/agent-stage17-adversarial-assurance`, PR #73.

The accepted production baseline is Stage 17 / PR #71, merged as `c3ca3c33f89f67fad97081f889934669e34befa5`, followed by protected-main lifecycle closure PR #72. This slice starts from closure merge `df4b68386bf4518cdf1c2946312ff06be8764ecc`.

The final draft implementation head `4d55fbe48e5448712a0969b3fe4a9952a32677a0` passed PR CI #3575 (`33115890916`) across all five permanent jobs: `development-context`, Ubuntu/Windows bootstrap unit suites, and Ubuntu/Windows app-baseline including browser user-outcome E2E.

## Assurance implementation under review

The Stage-17 adversarial-assurance pilot strengthens already accepted Stage-16/17 Agent guarantees before background execution adds leases, heartbeats, concurrency and longer recovery paths.

The implementation is deliberately narrow:

- no change to UV production Agent semantics;
- mutations run only against isolated temporary copies of the full `uv_studio` package;
- each curated defect class is represented by a named guarantee, exact target source replacement and exact existing regression detector;
- every detector first passes against an unmodified overlay, then runs in a fresh process against the mutated overlay;
- the helper proves the imported target module path equals the exact declared overlay target and that its SHA-256 equals the expected baseline/mutated bytes;
- results distinguish assertion-based `KILLED` from `SURVIVED` and harness/import/source-binding `ERROR`;
- the six initial Stage-17 mutants are required to be killed on both Ubuntu and Windows through the ordinary bootstrap unit suite;
- the regression suite proves checkout source bytes remain unchanged and report output cannot be written inside the repository root.

The initial guarantees cover persistence-time role revalidation, context freshness during delegation/persistence, delegation namespace reservation, Plan-bound provenance classification and exact AgentHarness/Project Store/Planner authority for injected Stage-17 coordinators.

## Authority stack unchanged

Project Store, Production Semantic Core, canonical Timeline, Studio/Application Commands, AgentHarness, Stage-16 Planner/Plan/Task/Skill authority, Stage-17 role factoring, Model Registry, Job/Attempt authority and Capability Registry/D-017 remain unchanged. The assurance runner is test infrastructure only and cannot become a product mutation or execution path.

## Known limitations

This is a curated pilot, not exhaustive automatic mutation testing. It does not yet include background-worker concurrency, lease/heartbeat or recovery mutants because that runtime does not exist yet. Those guarantees belong with D-066 layer 4 once the production implementation exists.

## Handoff

After PR #73 is merged and lifecycle-closed, the next product slice is `studio-v2-agent-background-execution`: D-066 layer 4, bounded background Agent work through existing Job Manager/execution authorities.
