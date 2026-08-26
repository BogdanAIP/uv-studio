# Agent Harness foundation — Stage 15

**Status:** implemented and merged in PR #69  
**Date:** 2026-08-26  
**Merge commit:** `273b5ea8f979cf759cfbf6510e1215a55e98d9c9`  
**Decision authority:** D-066 + D-017

## Purpose

Stage 15 implements only the first bounded UV-owned Agent Harness layer from D-066. It does not introduce a second project model, tool registry, permission system or autonomous planner.

The implemented control flow is:

```text
canonical Project / Production / Timeline / Model / Job state
 -> AgentContextBuilder
 -> deterministic AgentActionCatalog over existing UV authorities
 -> effects / locality / cost / D-017 policy projection
 -> AgentHarness bounded invocation
 -> existing ProductionSemanticService / TimelineCommandService / GenerationService
 -> canonical ProjectUnitOfWork / Job Manager effects
 -> append-only project-scoped Agent trace
```

## Context Builder

`uv_studio.agent.AgentContextBuilder` builds a compact deterministic observation from existing canonical authorities:

- modern Production Direction identity;
- Project identity/title/update time and bounded project-owned reference identities;
- shared Scene/Shot/Take state, with an optional Shot target;
- bounded target Take identities and bounded Shot reference/Take/Timeline-clip identity lists, each with omitted counts;
- canonical Timeline summary with bounded track identities and bounded per-track clip identities, with omitted counts;
- visible named Model Registry descriptions;
- bounded Job identities and bounded per-Job Attempt status/provenance identities, with omitted counts.

The context intentionally does **not** copy project `settings`/`extensions`, raw Job requests, provider prompts, reusable authorization tokens, provider-private cache/session/latent state, arbitrary project files or absolute host paths.

The snapshot has a stable SHA-256 digest so a trace can bind an action to the observed canonical state without persisting a second copy of that state. Large projects remain observations of bounded collections rather than a complete Agent-owned duplicate graph.

## Existing-authority action catalog

`AgentActionCatalog` is metadata over existing UV services, not a parallel Jarvis-style tool authority. The initial bounded actions are:

- `production.create_scene`;
- `production.create_shot`;
- `production.register_take`;
- `production.accept_take`;
- `timeline.create_track`;
- `timeline.add_clip`;
- `timeline.move_clip`;
- `timeline.trim_clip`;
- `timeline.remove_clip`;
- `generation.submit`.

Each relevant entry exposes its existing authority, bounded input fields/effects and machine-readable Job Manager / possible D-017 routing facts. Unknown actions fail closed. In particular, there is no generic `project.write_file`, shell, Python or arbitrary provider command hidden behind the Agent catalog.

## Effects and policy

For Production/Timeline commands, the catalog exposes bounded local/free command effects while canonical mutation still happens only inside the existing command service and `ProjectUnitOfWork`.

For named generation, policy resolves the existing `ModelRegistry -> CapabilityOffer -> CapabilityRegistry.effects_for_offer()` chain. Availability, locality, cost and semantic effects therefore come from the same existing authority used elsewhere in UV Studio.

D-017 remains authoritative. The Agent policy can report that consent is required, but `AgentHarness` cannot manufacture or persist a grant. Remote/non-free generation still succeeds only when the caller supplies a valid one-shot authorization created for the exact `GenerationService.prepare()` intent; `GenerationService.submit()` consumes that grant exactly as before.

## Inspectable trace

`AgentTraceStore` writes append-only records under the project's existing `tasks/` root through `ProjectTaskRecordStore`.

Each record contains only bounded inspection facts:

- trace/project/time identity;
- context digest;
- action identity;
- digest of non-secret accepted action input, or a fixed rejected-input digest when validation fails;
- canonical project/target/result identities;
- affected Scene/Shot/Take/reference identities for successful production mutations;
- resolved policy/effects facts;
- success/failure status;
- transaction, Job, Attempt, output, Take, track or clip references where applicable;
- bounded sanitized failure type/message.

Trace is execution history, not canonical Production/Timeline truth. Raw action arguments, prompts and authorization tokens are not persisted. Portable-state validation rejects sensitive keys and absolute host-path leakage. Context-construction and portable-input validation failures are also traced when the project-scoped trace authority can be resolved, without persisting the rejected values.

## Bounded execution proof

`tests/test_agent_harness.py` proves:

1. deterministic context construction without leaking settings/extensions;
2. nested Timeline collections remain bounded with explicit omitted counts;
3. deterministic catalog and fail-closed unknown actions;
4. a successful Agent action using the existing `ProductionSemanticService` transaction path;
5. success trace contains the affected canonical production identities rather than relying on raw action input;
6. durable trace reopening through a fresh `ProjectStore` instance;
7. failed existing commands leave a failure trace without false success state;
8. context/input validation failures leave sanitized failure traces without storing rejected host-path values;
9. unknown actions cannot become a direct project-file write;
10. token/absolute-host-path data is rejected from portable trace/context state;
11. unavailable generation fails before Job creation;
12. remote/non-free generation still requires the exact D-017 one-shot authorization and the token is not recorded in trace.

`tests/test_agent_catalog_contract.py` additionally proves machine-readable Job Manager and possible-D-017 routing facts for catalog entries.

The final exact reviewed head `a0d6eec7b9cad723aad9d38fc5af2c820b536c1a` passed all five permanent CI jobs on Ubuntu and Windows, including browser E2E. Four automated review findings were fixed and resolved before merge.

## Explicitly deferred by D-066

Stage 15 does **not** implement:

- Planner;
- durable Agent Task graph;
- Skills runtime;
- functional subagents (`explore`, `plan`, `media`, `critic`);
- autonomous/background Agent orchestration;
- evaluation/repair loops;
- dependency-aware long-form autonomy;
- an Agent-specific canonical write path;
- a user-facing Agent readiness/product claim.

## Next D-066 layer

After Stage 15 lifecycle closure, the next bounded slice is `studio-v2-agent-planner-durable-tasks-skills`:

```text
Stage-15 Context / Catalog / Policy / Trace
 -> Planner
 -> durable Agent Tasks
 -> Skills
 -> execution only through AgentHarness / existing UV authorities
```

Functional subagents remain the following separate D-066 layer. Background work, evaluate/repair, human takeover/edit/resume and long-form autonomy remain later still.
