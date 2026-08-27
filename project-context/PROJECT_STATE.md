# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: agent-stage17-adversarial-assurance -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in a bounded research slice: `agent-stage17-adversarial-assurance` on branch `research/agent-stage17-adversarial-assurance`.

The accepted production baseline is Stage 17 / PR #71, merged as `c3ca3c33f89f67fad97081f889934669e34befa5`, followed by protected-main lifecycle closure PR #72. This slice starts from closure merge `df4b68386bf4518cdf1c2946312ff06be8764ecc`.

## Assurance goal

Strengthen already accepted Stage-16/17 Agent guarantees before background execution adds leases, heartbeats, concurrency and longer recovery paths.

The first pilot is deliberately narrow:

- no change to UV production Agent semantics;
- mutate isolated temporary copies only;
- convert real review defect classes into named guarantees;
- require one exact detector for each curated mutant;
- distinguish assertion-based `KILLED` from `SURVIVED` and harness/import/source-binding `ERROR`;
- prove the detector actually imported the mutated overlay rather than the normal checkout.

Initial guarantees cover persistence-time role revalidation, context freshness during delegation/persistence, delegation namespace reservation, Plan-bound provenance classification and exact AgentHarness authority for injected planners.

## Authority stack unchanged

Project Store, Production Semantic Core, canonical Timeline, Studio/Application Commands, AgentHarness, Stage-16 Planner/Plan/Task/Skill authority, Stage-17 role factoring, Model Registry, Job/Attempt authority and Capability Registry/D-017 remain unchanged. The assurance runner is test infrastructure only and cannot become a product mutation or execution path.

## Handoff

After the assurance slice is reviewed, merged and lifecycle-closed, the next product slice is `studio-v2-agent-background-execution`: D-066 layer 4, bounded background Agent work through existing Job Manager/execution authorities.
