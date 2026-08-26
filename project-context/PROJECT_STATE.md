# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: studio-v2-model-registry-job-manager-generation -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`main` is lifecycle-closed and idle after Stage 14 / PR #68.

- merged PR: #68 `stage 14: model registry, jobs and named generation`;
- exact reviewed head: `0117a622a50dd506855f8557ff6c6c0ac0124811`;
- merge commit: `daa9381f45e136f7e406ac29888f8ac597da3f79`;
- exact-head CI run #3306 passed all five permanent jobs on Ubuntu/Windows, including API, real-media, frontend build and browser user-outcome suites;
- all inline review threads were resolved before merge.

No implementation slice is currently active. The declared handoff is `studio-v2-agent-context-command-catalog-trace`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-066** — JarvisHub is the Agent Harness architecture/method donor; UV retains canonical project/application authority.
- **D-067** — Product Truth Contract/current-document consistency.
- **D-068** — desktop in-place updates remain accepted Stage-9 release work.
- **D-069** — sequential generative continuation persists provider-neutral media lineage while provider cache/latent/session state remains adapter-private.
- **D-033** — canonical Timeline/editor foundation.
- **D-017** — exact one-shot authorization for remote/non-free execution.

## As-built foundation through Stage 14

Stages 12–14 now provide the lower production and generation spine needed by the Agent Harness:

1. typed Production Direction identity and bounded project/production storage;
2. shared `Scene`, `Shot`, `Take` and accepted-Take semantics across directions;
3. `ProductionSemanticService` as the shared production mutation boundary;
4. canonical Timeline plus `ProjectUnitOfWork` prepared journal, rollback/recovery and durable project Undo/Redo;
5. transactional accepted-Take projection into Timeline while preserving project media provenance;
6. backend-owned user-visible Model Registry above capability/provider transport;
7. project-scoped durable generation Job/Attempt records under the existing `tasks/` authority;
8. exact idempotency: same key + same digest reuses, same key + different digest conflicts, fresh key permits a deliberate identical-input creative reroll;
9. D-017 remains independent: every new remote/non-free execution requires the normal exact authorization;
10. provider-neutral `GenerationContract`, including feature-gated D-069 continuation parent lineage;
11. generated output becomes project-owned media and a shared Take candidate before semantic acceptance;
12. Studio generation UI exposes model/Shot/prompt/contract choice and queued/running/succeeded/failed/cancelled/result states;
13. resolved `CapabilityEffects` are exposed through the existing Capability Registry/API for later Agent policy/trace use;
14. the first machine-readable Product Truth record, `docs/architecture/product-truth/generate-shot-take.json`, deterministically binds domain/API/frontend mount-chain/state/evidence;
15. cross-platform browser proof covers named generation -> Take candidate -> acceptance -> canonical Timeline -> Undo while Job provenance remains durable.

## Stage-14 recovery/retry guarantees

The final review added three important execution guarantees:

- a named model whose selected offer is `configuration_required` or unavailable is rejected before authorization consumption and before Job creation;
- retry first durably transitions `failed -> queued` before the HTTP response/background execution, so Studio polling cannot lose the retry transition;
- FastAPI startup reconciliation converts abandoned `queued`/`running` generation Jobs into explicit retryable `failed` history rather than leaving them permanently stuck.

Restart reconciliation **never automatically replays provider work**. For an interrupted provider call the external outcome may be unknown; a new remote/non-free retry therefore remains explicit and goes through the ordinary D-017 boundary. Existing Attempt history is preserved.

## Product Truth status

The named-generation feature is the first implemented D-067 consumer. Its ready contract resolves to:

```text
GenerationService.submit
 -> FastAPI generation route
 -> Next Studio route mount chain
 -> GenerationWorkspacePanel controls
 -> Job/Attempt + artifact + Take state
 -> API integration proof
 -> browser user-outcome proof
```

The env-gated `Stage14E2ETestExecutor` remains test-only and absent from the normal model catalog unless `UV_STUDIO_E2E_TEST_GENERATION=1`. Normal unconfigured models remain visible but cannot be launched.

D-069 continuation is only a durable contract/lineage seam today. There is no real `generation.continuation` provider offer or user-visible Continue/Edit workflow yet.

## Explicit non-goals still in force

- no full Planner/Tasks/Skills/Subagents runtime yet;
- no Agent-only project write path;
- no JarvisHub Canvas/node/PostgreSQL/Hono authority or duplicate tool registry;
- no provider-private cache/latent/session state in Project Store;
- no desktop Update Service/UI implementation in the Agent slice;
- no claim that a real continuation-capable provider is integrated.

## Next handoff

`studio-v2-agent-context-command-catalog-trace`

Implement only the first bounded Agent Harness layer from D-066:

```text
canonical project/context observation
 -> UV-owned Context Builder
 -> catalog of existing Studio/Application Commands + models/jobs/capabilities
 -> effects/policy inspection using existing authorities
 -> one bounded execution seam through the same commands/services
 -> append-only inspectable trace linked to canonical project identities
```

Do not add Planner, durable Task graphs, Skills, functional subagents or long-form autonomy until this foundation is independently proven.
