# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-model-registry-job-manager-generation -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 14 is active in draft:

- slice `studio-v2-model-registry-job-manager-generation`;
- branch `stage-14/studio-v2-model-registry-job-manager-generation`;
- base `main` at `e9b249124c48203c71d386a5fc997cbbfe61e3e6`;
- PR is not opened yet;
- last completed Stage 13 / PR #66, merge `16409d2d01ce4ca2be3eab61a02a06655650f444`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-033** — canonical Timeline remains UV-owned; MLT remains derived.
- Capability Registry / adapter boundaries own execution availability, authorization and transport; they do not own user-visible model identity.

## Stage 14 implementation target

Stage 14 must establish the missing execution spine between shared Shot intent and generated Take candidates:

1. a backend-owned user-visible Model Registry with stable `model_id` independent from provider/adapter/offer identity;
2. explicit model-to-capability/transport bindings with availability/locality/cost facts reused from Capability Registry rather than duplicated as product authority;
3. durable project-scoped generation Jobs with queued/running/succeeded/failed/cancelled lifecycle and bounded exact provenance;
4. canonical Job documents under the existing Project Store `tasks/` boundary rather than a second project-state root;
5. one explicitly labelled local demo/test generation model and adapter for deterministic cross-platform proof without pretending it is a production AI model;
6. generated media materialized into project-owned bytes/reference metadata before it can become a shared Take candidate;
7. Take registration through the existing `ProductionSemanticService`, with acceptance and canonical Timeline projection left on the Stage-13 `accept_take` / `ProjectUnitOfWork` path;
8. Undo of acceptance must restore production/project/Timeline state without erasing successful Job/model/provider provenance;
9. GUI and API must expose meaningful model choice and Job state through backend authority rather than donor-era frontend registries;
10. the implementation must remain ready for the next slice to replace the demo binding with a first real named Image AI model without introducing provider-specific project schemas.

## Storage and authority decisions for this slice

- Reuse canonical `tasks/` for durable Job documents; do not add a project-level `jobs/` root.
- Keep minimal shared Take semantics (`take_id`, `shot_id`, project `reference_id`) provider-neutral; generation provenance belongs to the durable Job and generated ProjectReference metadata.
- Persist a resolved execution snapshot on each Job so later registry/config changes cannot rewrite historical model/provider provenance.
- Job lifecycle is not a second undo stack. Acceptance remains a separate product transaction after Job success and candidate registration.

## Compatibility rule

Recipe/Product Orchestrator/numbered Stage routes remain compatibility code. Stage 14 must not route new model/job/generation state through recipe identity, Stage workspaces or provider-private project documents.

## Next handoff

After Stage 14 is reviewed, merged and lifecycle-closed, `studio-v2-first-real-image-ai` should bind a real named image model to the same Model Registry / Job Manager path and prove a user-visible generated image enters the Project Store/Media Bin without provider-specific frontend branching.
