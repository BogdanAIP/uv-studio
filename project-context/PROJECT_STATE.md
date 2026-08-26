# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: studio-v2-agent-context-command-catalog-trace -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`main` is lifecycle-closed and idle after Stage 15 / PR #69.

- merged PR: #69 `stage 15: agent context, command catalog and trace`;
- exact reviewed head: `a0d6eec7b9cad723aad9d38fc5af2c820b536c1a`;
- merge commit: `273b5ea8f979cf759cfbf6510e1215a55e98d9c9`;
- exact-head CI runs #3328 and #3329 passed all five permanent jobs on Ubuntu/Windows, including unit/API, real-media, frontend and browser user-outcome suites;
- all four inline review findings were fixed, answered and resolved before merge.

No implementation slice is currently active. The declared handoff is `studio-v2-agent-planner-durable-tasks-skills`, which is D-066 Agent Harness layer 2.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-066** — JarvisHub is the Agent Harness architecture/method donor; UV retains canonical project/application authority and defines the bounded Agent-layer order.
- **D-067** — Product Truth Contract/current-document consistency.
- **D-068** — desktop in-place updates remain accepted Stage-9 release work.
- **D-069** — sequential generative continuation persists provider-neutral media lineage while provider cache/latent/session state remains adapter-private.
- **D-033** — canonical Timeline/editor foundation.
- **D-017** — exact one-shot authorization for remote/non-free execution.

## As-built foundation through Stage 15

Stages 12–15 now provide the production, generation and first Agent-Harness foundation:

1. typed Production Direction identity and bounded project/production storage;
2. shared `Scene`, `Shot`, `Take` and accepted-Take semantics across directions;
3. `ProductionSemanticService` as the shared production mutation boundary;
4. canonical Timeline plus `ProjectUnitOfWork` prepared journal, rollback/recovery and durable project Undo/Redo;
5. transactional accepted-Take projection into Timeline while preserving project media provenance;
6. backend-owned user-visible Model Registry above capability/provider transport;
7. project-scoped durable generation Job/Attempt records under the existing `tasks/` authority;
8. exact generation idempotency, retry/failure history and restart reconciliation without hidden provider replay;
9. D-017 exact authorization for remote/non-free execution;
10. provider-neutral `GenerationContract`, including feature-gated D-069 continuation parent lineage;
11. generated output becomes project-owned media and a shared Take candidate before semantic acceptance;
12. resolved `CapabilityEffects` remain the single execution-effects source for Agent policy;
13. machine-readable Product Truth binds the named-generation domain/API/frontend/state/evidence path;
14. cross-platform browser proof covers named generation -> Take candidate -> acceptance -> canonical Timeline -> Undo while Job provenance remains durable;
15. `AgentContextBuilder` derives bounded deterministic context from canonical Project/Production/Timeline/Model/Job state without copying the project into an Agent graph;
16. `AgentActionCatalog` exposes stable metadata only over existing Production/Timeline/Generation authorities, including Job Manager and possible D-017 routing facts;
17. Agent policy projects existing availability/locality/cost/effects/authorization facts without adding a second permission system;
18. `AgentTraceStore` persists append-only project-scoped inspection history linked to canonical identities, excluding secrets, reusable authorization, host paths, provider prompts and private caches;
19. `AgentHarness` executes only through existing UV services and records both success and sanitized failure outcomes;
20. context nesting is bounded with omitted counts; production success traces retain affected canonical Scene/Shot/Take/reference identities; pre-policy context/input failures leave failure trace when project trace storage is available.

## Stage-15 boundary that remains authoritative

The Agent foundation is internal infrastructure, not a user-visible autonomous Agent claim.

It does **not** create:

- a second project graph or canonical state;
- a private Agent project-write path;
- a duplicate JarvisHub-style tool/protocol/permission authority;
- Planner, durable Agent Tasks or Skills yet;
- functional subagents yet;
- background Agent execution, evaluate/repair or long-form autonomy yet.

All future Agent layers must continue to invoke the same Studio/Application Commands, Model Registry, Job Manager, Capability Registry and D-017 boundaries as GUI/scripts/MCP.

## Next handoff

`studio-v2-agent-planner-durable-tasks-skills`

Implement D-066 layer 2 only:

```text
bounded user/production goal
 -> Stage-15 Context Builder + Action Catalog
 -> Planner produces a validated bounded plan
 -> durable project-scoped Agent Tasks with explicit dependencies/state
 -> reusable bounded Skills expand only into approved catalog actions/tasks
 -> task execution continues through AgentHarness / existing UV authorities
 -> append-only trace links plan/task/skill execution to canonical identities
```

Functional subagents (`explore`, `plan`, `media`, `critic`), background work, evaluation/repair, human takeover/edit/resume and long-form autonomy remain later D-066 layers.
