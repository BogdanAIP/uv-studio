# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-model-registry-job-manager-generation -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 14 is active as draft PR #68 on branch `stage-14/model-registry-job-manager-generation`, created from lifecycle-closed `main` commit `03f382c29816218ca32380ac39669df2bc3fc79a`.

Goal: deliver the first truthful named-model generation vertical over the existing Studio/Production Semantic Core: backend-owned Model Registry, project-scoped Job/Attempt lifecycle, provider-neutral GenerationContract, generated project-owned media and Take candidate, visible Studio state, Product Truth contract and browser E2E.

The previous architecture slice PR #67 merged as `f43437b7716cc5454d49595a07b616b35e3f2324` after exact-head CI success and closed back to idle before this branch was created.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-066** — JarvisHub is the reference architecture/method donor for the future Agent Harness; Stage 14 borrows only idempotency, GenerationContract, effects visibility and durable Job provenance patterns.
- **D-067** — Product Truth Contract/current-document consistency; Stage 14 is the first implementation consumer.
- **D-068** — desktop in-place updates are accepted Stage-9 release work and are out of scope here.
- **D-069** — stateful/sequential generative continuation persists provider-neutral parent-media lineage while provider cache/latent/session state remains adapter-private; InfinityEdit is a donor/candidate adapter, not a required runtime.
- **D-033** — canonical Timeline remains UV-owned; MLT remains derived.
- **D-017** — exact one-shot authorization remains the remote/non-free execution boundary.

## Existing as-built foundation

Stages 12 and 13 provide the lower production spine reused by Stage 14:

1. typed Production Direction identity and bounded production storage;
2. `ProjectUnitOfWork` with prepared journal, rollback/recovery and durable project-level Undo/Redo;
3. strict shared `Scene`, `Shot`, `Take` and accepted-Take contracts;
4. micro-drama Story/Characters/Locations/continuity extensions;
5. one serialized `ProductionSemanticService` command boundary;
6. HTTP semantic handlers over the same service;
7. shared Scene/Shot/Take semantics proven outside micro-drama;
8. transactional `accept_take` spanning production state, project media provenance and canonical Timeline;
9. project-level Undo/Redo of accepted-Take projection;
10. rich shared Studio Production UI and cross-platform browser proof with real media.

Stage 14 does not create a second project/timeline/production authority or a provider-private Shot/Take model.

## Stage 14 as-built contracts

### Model Registry

Named model identity is backend-owned and user-visible. Provider/adapter/capability mappings are execution details beneath it. Model choice is visible in Studio and available to programmatic callers through the same backend catalog. Offer feature metadata remains explicit, including `generation.continuation` gating where a provider actually supports it.

### Job / Attempt

Long-running generation is project-scoped and durable with queued/running/succeeded/failed/cancelled states. Job records live under the existing project `tasks/` authority; each execution Attempt records lifecycle/output/failure without becoming Undo/Redo production state.

Job/Attempt history is execution history. Take acceptance is production history. Undoing acceptance does not erase generation provenance.

### Idempotency

- same idempotency key + same normalized digest: reuse queued/running/succeeded request/result and do not execute twice;
- same key + materially different digest: conflict/fail closed;
- fresh idempotency key: deliberate new creative Job/Attempt, even when project/model/generation inputs are otherwise identical;
- infrastructure retry after failure remains history on the same Job rather than a hidden new creative reroll;
- idempotency never bypasses or widens D-017 authorization;
- when sequential continuation is requested, the parent media reference is part of `GenerationContract` and therefore part of the normalized digest.

### GenerationContract

Provider-neutral semantic constraints include fixed constraints, editable variables, forbidden semantic changes, approved project reference identity and the bounded continuation parent identity. Provider prompt text is not canonical production truth.

`continuation_source_reference_id` is accepted only when the selected offer explicitly advertises `generation.continuation`; otherwise generation fails closed. Successful continuation records parent -> child lineage in generated-media provenance.

Provider-private KV caches, latents, session handles, sliding history windows and anchor-frame caches remain adapter-owned execution optimizations. They are not canonical Project Store data and are not required to reconstruct the durable generation chain.

### Effects metadata

`CapabilityEffects` and `CapabilityRegistry.effects_for_offer()` expose stable inspectable flags for project/Timeline mutation, generated media, destructive behavior, long-running behavior, reversibility and cost-bearing execution. Offer-resolved effects are returned by the existing capability-offers API; no parallel Agent/tool registry is introduced. D-017 still evaluates actual locality/cost permission from the selected offer.

### Product Truth

The first machine-readable Product Truth Contract is now implemented at:

```text
docs/architecture/product-truth/generate-shot-take.json
```

`uv_studio/product_truth.py` validates that the contract resolves to the actual `GenerationService.submit` domain method, FastAPI POST route, `GenerationWorkspacePanel` surface/control labels, canonical dependencies and declared API/browser test methods. `tests/test_product_truth_contracts.py` makes this a permanent deterministic CI invariant rather than prose interpretation.

The contract is truthful about conditional execution: normal named models with `configuration_required`/unavailable offers remain visible and blocked with their reason. Successful API/browser proof uses only the explicitly env-gated `Stage14E2ETestExecutor`, which is absent from the normal model catalog unless `UV_STUDIO_E2E_TEST_GENERATION=1`.

Continuation UI is deliberately not claimed ready in Stage 14 because no real continuation-capable model/adapter is integrated yet.

## Implemented user-visible proof

```text
existing shared Shot
 -> choose named model in Studio UI
 -> construct GenerationContract
 -> create idempotent project-scoped generation Job/Attempt
 -> expose queued/running/error/cancel/result state
 -> execute through bounded capability/adapter mapping
 -> persist project-owned generated media + provenance
 -> materialize shared Take candidate
 -> show result in Studio UI
 -> accept via existing shared production command
 -> canonical Timeline
 -> Undo acceptance without deleting Job/Attempt provenance
```

Focused unit/API tests separately prove replay deduplication, same-key/different-digest conflict, fresh-key intentional reroll, failure/retry history, effects metadata and feature-gated continuation lineage. `e2e/test_named_generation_outcome.py` begins from the visible Studio surface and proves the complete base named-generation outcome.

## Explicit non-goals

- no full Agent Runtime, Planner, Memory, Skills or Subagents;
- no JarvisHub Canvas/PostgreSQL/Hono/node project model or duplicate tool registry;
- no desktop Update Service/UI implementation;
- no new Production Direction or direction-private editor/timeline;
- no provider prompt/provider identifier as canonical project meaning;
- no InfinityEdit/Helios runtime integration or user-visible continuation workflow in Stage 14;
- no provider-private continuation cache/latent/session state in Project Store.

## Current implementation status

The Stage-14 implementation vertical is present in draft PR #68: backend Model Registry, project Job/Attempt/idempotency, GenerationContract, D-017-preserving submission, generated artifact -> shared Take materialization, Studio generation surface, effects metadata, D-069 continuation lineage seam, machine-readable Product Truth registry/validator, API proof and browser user-outcome proof.

The earlier exact head `1286a51061d5f10489ca1ea48baf26e96e670af8` passed all five permanent CI jobs before the final Product Truth/effects validation commits. The current post-validation head must pass the same exact-head checks before the PR moves to review. Until that happens, Stage 14 remains **draft, implemented but not yet review-closed**.

## Next handoff

The next post-Stage-14 slice is intentionally not declared here yet. Finish exact-head verification, move this bounded vertical through review/merge, synchronize the merged lifecycle back to idle, and only then select the later Agent Harness work from current architecture rather than guessing ahead.
