# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-model-registry-job-manager-generation -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 14 is active as draft PR #68 on branch `stage-14/model-registry-job-manager-generation`, created from lifecycle-closed `main` commit `03f382c29816218ca32380ac39669df2bc3fc79a`.

Goal: implement the first truthful named-model generation vertical over the existing Studio/Production Semantic Core: backend-owned Model Registry, project-scoped Job/Attempt lifecycle, provider-neutral GenerationContract, generated project-owned media and Take candidate, visible Studio state, Product Truth contract and browser E2E.

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

Stages 12 and 13 already provide the lower production spine that Stage 14 must reuse:

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

Stage 14 must not create a second project/timeline/production authority or a provider-private Shot/Take model.

## Stage 14 required contracts

### Model Registry

Named model identity is backend-owned and user-visible. Provider/adapter/capability mappings are execution details beneath it. Model choice must remain visible in Studio and available to future Agent/script/MCP callers. Offer feature metadata is also surfaced so provider-specific capabilities such as `generation.continuation` can be checked truthfully instead of assumed.

### Job / Attempt

Long-running work is project-scoped and durable with queued/running/succeeded/failed/cancelled states. A generation Attempt records named model, selected execution mapping, normalized inputs, GenerationContract, output/failure and provenance.

Job/Attempt history is execution history. Take acceptance is production history. Undoing acceptance must not erase generation provenance.

### Idempotency

- same idempotency key + same normalized digest: reuse queued/running/succeeded request/result and do not execute twice;
- same key + materially different digest: conflict/fail closed;
- fresh idempotency key: deliberate new creative Attempt, even when project/model/generation inputs are otherwise identical;
- idempotency never bypasses or widens D-017 authorization;
- when sequential continuation is requested, the parent media reference is part of `GenerationContract` and therefore part of the normalized digest.

### GenerationContract

Provider-neutral semantic constraints include fixed constraints, editable variables, forbidden semantic changes and approved project references/keyframes where applicable. Provider prompt text is not canonical production truth.

Stage 14 also reserves `continuation_source_reference_id` as a provider-neutral lineage parent for later stateful/sequential generation. It is accepted only when the selected offer explicitly advertises `generation.continuation`; otherwise generation fails closed. Successful continuation records parent -> child lineage in generated-media provenance.

Provider-private KV caches, latents, session handles, sliding history windows and anchor-frame caches are execution optimizations behind the adapter. They are not canonical Project Store data and are not required to reconstruct the durable generation chain.

### Product Truth

The first machine-readable Product Truth Contract must bind the named-generation feature to its canonical command/API, Studio entry/model control, Job/Attempt/generated-asset/Take-candidate state and browser E2E proof.

A backend-only generation path or an unwired frontend control cannot be marked ready at review. Continuation UI is deliberately not claimed ready in Stage 14 because no real continuation-capable model/adapter is integrated yet.

## Required user-visible proof

```text
existing shared Shot
 -> choose named model in Studio UI
 -> construct GenerationContract
 -> create project-scoped Job/Attempt
 -> show queued/running state
 -> execute through bounded capability/adapter mapping
 -> persist project-owned generated media + provenance
 -> materialize Take candidate
 -> show result in Studio UI
 -> accept via existing shared production command
 -> canonical Timeline
 -> Undo acceptance without deleting Job/Attempt provenance
```

Tests must separately prove replay deduplication, same-key/different-digest conflict and fresh-key intentional reroll. Focused service tests also prove that continuation requests are feature-gated and preserve durable lineage without introducing provider-private project state.

## Explicit non-goals

- no full Agent Runtime, Planner, Memory, Skills or Subagents;
- no JarvisHub Canvas/PostgreSQL/Hono/node project model or duplicate tool registry;
- no desktop Update Service/UI implementation;
- no new Production Direction or direction-private editor/timeline;
- no provider prompt/provider identifier as canonical project meaning;
- no InfinityEdit/Helios runtime integration or user-visible continuation workflow in Stage 14;
- no provider-private continuation cache/latent/session state in Project Store.

## Current implementation status

Draft PR #68 now contains the Model Registry/Job/GenerationContract vertical in progress plus the D-069 continuation-lineage seam. The seam is intentionally backend/contract groundwork only: no real `generation.continuation` offer is shipped to users yet. Until backend, frontend, Product Truth contract and E2E for the base named-generation vertical are fully verified, Stage 14 remains **not yet product-ready**.

## Next handoff

The next post-Stage-14 slice is intentionally not declared here yet. Finish this bounded vertical, synchronize as-built documentation at review, pass the exact-head permanent checks and close the merged lifecycle before selecting later Agent Harness work.
