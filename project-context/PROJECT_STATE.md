# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: architecture-compression-inventory -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in review for `architecture-compression-inventory` on branch `research/architecture-compression-inventory`, PR #77, starting from lifecycle-closed `main` merge `e6d23e9444023c0c491ae0800d6aac01d415968c`.

Stage 18 `studio-v2-agent-background-execution` remains the last completed Agent slice, merged through PR #75 as `c5051b975a1ba8e747f453dd0a485cac1e308ba7` and lifecycle-closed through PR #76.

## Accepted Stage 18 baseline

D-066 layer 4 bounded background Agent execution remains accepted infrastructure. Architecture compression must not weaken or bypass:

- the shared cross-runtime project mutation fence;
- Production/Timeline/project JSON serialization guarantees;
- exact canonical freshness for background claims;
- Generation same-key idempotency and one-shot D-017 consumption/reservation atomicity;
- foreground/background coordinator ownership;
- restart/recovery rules that avoid replay of ambiguous work.

## D-070 inventory under review

PR #77 is behavior-preserving documentation/inventory work only. Runtime, frontend implementation and tests are outside its write scope.

The exact caller/migration map is recorded in `docs/architecture/LEGACY_SURFACE_INVENTORY.md`. Review-state findings are:

1. **Modern product composition is already separate from Recipe/Product Orchestrator.** New creation uses Production Directions and opens `/projects/{id}/studio`; the modern workspace uses Project/Timeline/Production semantics/Generation rather than `productWorkflowApi`.
2. **Legacy project workflows are still intentionally supported.** The project list exposes a separate “Старый совместимый workflow” link to `/projects/{id}` for legacy identity, and that route uses Product Orchestrator projections plus Dubbing/General/Music/Narrated/Continuity/Stage8 panels.
3. **schema-v1 `recipe_id` is durable compatibility state.** `ProjectDocument` still requires/serializes it, while typed modern Studio identity lives in `extensions.studio`; imported archives may retain unknown/uncreatable legacy recipe IDs for recovery.
4. **Recipe Registry and `/execution-plan` are compatibility seams, not modern authorities.** `/api/uv/recipes` still serves legacy creation/metadata; `/execution-plan` still resolves `project.recipe_id` and overlays Stage8 Capability readiness.
5. **Product Orchestrator is mixed legacy composition over useful modern/domain primitives.** Its HTTP seam dispatches by recipe, but already delegates to Dubbing, Targeted Edit, Music and Capability authorities that must survive extraction.
6. **Stage8 remains live compatibility.** Its workspace API/state, legacy editor panels and API/browser tests cannot be removed before persisted-project migration.
7. **Donor Workflow/Pipeline/Sandbox UI is the first retirement candidate, but `workflowApi.ts` is mixed.** The donor roots have no supported Next app route, while `/settings -> modelRegistry.ts -> workflowApi.fetchApiModels` is a real supported caller. `donor-ui-retirement` must move `fetchApiModels` to a modern model/capability client before deleting the donor-only remainder.
8. **The donor frontend reset is still authoritative and destructive.** Manually dispatching `.github/workflows/promote-frontend.yml` runs `tools/promote_frontend.py --force`, which removes the maintained `frontend/` and recreates it from the pinned VideoClaw frontend. `donor-ui-retirement` must disable or replace that reset authority before deletion can be considered durable.
9. **Historical “Stage 6” is not treated as a deletion unit.** The inventory classifies concrete surviving paths; no dedicated current Stage-6 runtime authority has been positively established, and incomplete code search is not accepted as absence proof.

The supported route tree, the live legacy page imports, the Settings/modelRegistry caller, and the destructive frontend reset path were independently rechecked during review. That evidence still supports `donor-ui-retirement` as the first bounded candidate without claiming its zero-caller or durable-deletion gates already passed.

## No-new-caller rule

Until D-070 architecture compression is executed, no new modern caller may be added to Recipe Registry, Product Orchestrator, `/execution-plan`, Stage8 composition or donor workflow APIs unless a later accepted decision explicitly reverses their legacy classification.

New work must target Production Directions, Shared Production Semantic Core, Studio/Application Commands, Generation/Model Job authority and Capability/D-017 boundaries.

## Domain state preservation

Dubbing, targeted edit, continuity and music are not deleted as collateral damage. Portable project state and reusable domain commands remain or move toward contextual tools/capabilities; only recipe/orchestrator/workspace composition is retired after caller and persisted-state proof.

## Bounded retirement order

The inventory supports this order:

1. `donor-ui-retirement` — first disable/replace the destructive donor reset, then extract the supported Settings model lookup from `workflowApi.ts`, then retire only donor-only UI/client remainder after zero-caller proof;
2. `project-identity-v2-compat-reader`;
3. `recipe-entrypoint-retirement`;
4. `execution-plan-retirement`;
5. bounded legacy direction/tool migration slices;
6. contextual tool extraction where still needed;
7. `stage8-compatibility-retirement`;
8. `product-orchestrator-retirement`;
9. combined `micro_drama` golden-vertical proof when the canonical spine is ready (it may move earlier if independently provable).

No big-bang rewrite is authorized by this list.

## Golden vertical gate

The first required combined user-visible proof remains:

`New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`

Existing tests prove important pieces separately, but the D-070 golden-vertical gate remains open until one accepted GUI outcome proves the combined path. If Agent is invoked, it must use the same Production/Timeline/Generation/Capability authorities as GUI/scripts/MCP.

## Verification state

Draft head `c72d0ac12aae79bcb8f3dd63f4111256962181c8` passed CI run #3716 before the review transition. Exact review head `2b589aa78ade48e631363c13d99f45287eb6c1b5` entered full permanent CI and Codex review. Review found two concrete inventory omissions: the supported Settings/modelRegistry caller of `workflowApi.fetchApiModels`, and the destructive manual donor-frontend reset path. Both are being corrected in documentation/context only; the corrected final head must receive a fresh full permanent CI pass before merge.

PR #77 has no runtime/product implementation diff. Review must confirm the caller/migration table, persisted-project gates, bounded retirement sequence and no-new-caller rule without treating incomplete GitHub Code Search as zero-caller proof.

## Known adjacent implementation risk

During Stage-18 closure CI, repeated Windows runs exposed a timing-sensitive production-form remount race: `ProductionWorkspacePanel` keys the production semantics panel by history cursor, so a post-command history refresh can remount the form and discard Shot input entered before refresh completion. Exact-SHA reruns alternated which “Создать кадр” E2E hit the timeout; the final closure attempt passed all permanent checks.

This risk is recorded so it is not lost, but PR #77 does not modify runtime behavior. It should be handled in a separate implementation slice when selected.

## Handoff

The next slice is `donor-ui-retirement`, conditional on this inventory being accepted. Its prerequisites are: (1) disable or replace `.github/workflows/promote-frontend.yml` / `promote_frontend.py --force` as a destructive write path over maintained frontend bytes while preserving any required provenance-check capability; (2) migrate `/settings -> modelRegistry.ts -> fetchApiModels` to a modern model/capability client. Only then may the donor-only `workflowApi.ts` remainder and donor UI be deleted after exact recursive zero-caller, route, build and browser proof.

D-066 layers 5-7 remain deferred until both D-070 gates are satisfied.
