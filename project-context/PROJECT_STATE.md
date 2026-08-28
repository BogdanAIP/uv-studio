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
3. **schema-v1 `recipe_id` is durable compatibility state and still has direct runtime readers.** `ProjectDocument` still requires/serializes it, while typed modern Studio identity lives in `extensions.studio`; imported archives may retain unknown/uncreatable legacy recipe IDs for recovery. Music Analysis Assist, final Music Video review, Music Assembly and the General/Narrated render adapters also branch directly on `project.recipe_id`. `project-identity-v2-compat-reader` must migrate those guards to typed Studio identity/Production Direction or explicit v1 compatibility state before the newest schema can stop requiring the field.
4. **Recipe Registry and `/execution-plan` are compatibility seams, not modern authorities.** `/api/uv/recipes` still serves legacy creation/metadata; `/execution-plan` still resolves `project.recipe_id` and overlays Stage8 Capability readiness. Frontend still exports matching endpoint clients through `frontend/lib/recipesApi.ts`, compatibility-only `projectsApi.createUVProject()` (requires `recipe_id`), and `projectsApi.getProjectExecutionPlan()`. No positive supported import of those particular exports has been established by this inventory, but incomplete Code Search is not accepted as absence proof; their retirement PRs must exact-scan and migrate any real caller or delete the export with the endpoint.
5. **Product Orchestrator is mixed legacy composition over useful modern/domain primitives.** Its HTTP seam dispatches by recipe, but already delegates to Dubbing, Targeted Edit, Music and Capability authorities that must survive extraction.
6. **Stage8 is live runtime compatibility, not only legacy UI state.** Besides its workspace API/state, legacy panels and tests, `get_stage8_workspace` is consumed by `general_video_render.py`, `narrated_render.py` and Commercial/General/Narrated/Story Product Orchestrator projections. Stage8 cannot be retired until those runtime callers migrate or are retired and persisted-project compatibility is proven.
7. **Donor Workflow/Pipeline/Sandbox UI is the first retirement candidate, but `workflowApi.ts` is mixed.** The donor roots have no supported Next app route, while `/settings -> modelRegistry.ts -> workflowApi.fetchApiModels` is a real supported caller. `donor-ui-retirement` must move `fetchApiModels` to a modern model/capability client before deleting the donor-only remainder.
8. **Donor frontend restoration remains supported and verified through multiple paths.** The manually dispatched `.github/workflows/promote-frontend.yml` runs `tools/promote_frontend.py --force`; plain `python tools/promote_frontend.py` recreates the pinned VideoClaw frontend when `frontend/` is absent; `tools/uv_dev.py` and Windows `scripts/setup-dev.ps1` direct developers to that plain restore; `docs/FRONTEND.md` documents the promotion/provenance mechanism. `tests/test_promote_frontend.py` explicitly tests no-force creation and force replacement, while `.github/workflows/ci.yml` runs that unit suite and separately invokes `tools/promote_frontend.py --check`. `donor-ui-retirement` must migrate all write-behavior callers/tests while preserving only intended read-only provenance verification.
9. **Historical “Stage 6” is not treated as a deletion unit.** The inventory classifies concrete surviving paths; no dedicated current Stage-6 runtime authority has been positively established, and incomplete code search is not accepted as absence proof.

The supported route tree, live legacy page imports, Settings/modelRegistry caller, endpoint-client compatibility exports, direct recipe-identity runtime readers, donor restoration paths/tests/CI, and positive Stage8 runtime callers were independently rechecked during review. That evidence still supports `donor-ui-retirement` as the first bounded candidate without claiming its zero-caller or durable-deletion gates already passed.

## No-new-caller rule

Until D-070 architecture compression is executed, no new modern caller may be added to Recipe Registry, Product Orchestrator, `/execution-plan`, Stage8 composition or donor workflow APIs unless a later accepted decision explicitly reverses their legacy classification.

New work must target Production Directions, Shared Production Semantic Core, Studio/Application Commands, Generation/Model Job authority and Capability/D-017 boundaries.

## Domain state preservation

Dubbing, targeted edit, continuity and music are not deleted as collateral damage. Portable project state and reusable domain commands remain or move toward contextual tools/capabilities; only recipe/orchestrator/workspace composition is retired after caller and persisted-state proof.

## Bounded retirement order

The inventory supports this order:

1. `donor-ui-retirement` — first eliminate/replace every supported write-capable donor frontend restoration path and migrate its tests/CI expectations (workflow, `promote_frontend.py` with or without `--force`, `uv_dev.py`, Windows `setup-dev.ps1`, docs, `tests/test_promote_frontend.py`, CI), preserving only read-only provenance checks; then extract the supported Settings model lookup from `workflowApi.ts`; then retire only donor-only UI/client remainder after zero-caller proof;
2. `project-identity-v2-compat-reader` — add explicit modern schema/identity migration and migrate every direct runtime `recipe_id` guard (Music Analysis Assist, Music Video review/assembly, General/Narrated render) to typed Studio identity/direction or explicit v1 compatibility state before newest-schema identity drops the field;
3. `recipe-entrypoint-retirement` — exact-scan `frontend/lib/recipesApi.ts` and `projectsApi.createUVProject()`, migrate any supported caller or delete those clients with `/api/uv/recipes` / legacy recipe-backed creation, then retire the backend entrypoint subject to persisted-project compatibility;
4. `execution-plan-retirement` — exact-scan `projectsApi.getProjectExecutionPlan()`, migrate any supported caller or remove only that helper/type surface with `/execution-plan`, while preserving the rest of live `projectsApi.ts`;
5. bounded legacy direction/tool migration slices;
6. contextual tool extraction where still needed;
7. `product-orchestrator-retirement` — only after supported legacy workflow callers have moved; this retires the Commercial/General/Narrated/Story Stage8 orchestration projections;
8. `stage8-runtime-dependency-migration` / `stage8-compatibility-retirement` — move remaining render-adapter consumers such as General Video and Narrated Video to canonical direction/input state, then retire Stage8 only after persisted-project and exact zero-runtime-caller proof;
9. combined `micro_drama` golden-vertical proof when the canonical spine is ready (it may move earlier if independently provable).

No big-bang rewrite is authorized by this list.

## Golden vertical gate

The first required combined user-visible proof remains:

`New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`

Existing tests prove important pieces separately, but the D-070 golden-vertical gate remains open until one accepted GUI outcome proves the combined path. If Agent is invoked, it must use the same Production/Timeline/Generation/Capability authorities as GUI/scripts/MCP.

## Verification state

Exact-head Codex review has found concrete documentation/inventory omissions around the supported Settings/modelRegistry caller of `workflowApi.fetchApiModels`, donor frontend restoration authority, live Stage8 runtime callers, D-070 gate semantics, current-authority lifecycle wording, no-force/Windows restore guidance, promotion unit-test/CI callers, exported frontend clients for `/api/uv/recipes` and `/execution-plan`, compatibility-only `createUVProject()`, and direct runtime `recipe_id` readers. All fixes remain documentation/context-only; the corrected final head must receive a fresh full permanent CI pass and exact-head review before merge.

PR #77 has no runtime/product implementation diff. Review must confirm the caller/migration table, persisted-project gates, bounded retirement sequence and no-new-caller rule without treating incomplete GitHub Code Search as zero-caller proof.

## Known adjacent implementation risk

During Stage-18 closure CI, repeated Windows runs exposed a timing-sensitive production-form remount race: `ProductionWorkspacePanel` keys the production semantics panel by history cursor, so a post-command history refresh can remount the form and discard Shot input entered before refresh completion. Exact-SHA reruns alternated which “Создать кадр” E2E hit the timeout; the final closure attempt passed all permanent checks.

This risk is recorded so it is not lost, but PR #77 does not modify runtime behavior. It should be handled in a separate implementation slice when selected.

## Handoff

The next slice is `donor-ui-retirement`, conditional on this inventory being accepted. Its prerequisites are: (1) eliminate or safely replace all supported write-capable donor frontend restoration paths — `.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py` both with and without `--force`, plus `tools/uv_dev.py`, `scripts/setup-dev.ps1`, `docs/FRONTEND.md`, and the write-behavior expectations in `tests/test_promote_frontend.py` — while preserving only check-only provenance verification in `.github/workflows/ci.yml` if still required; (2) migrate `/settings -> modelRegistry.ts -> fetchApiModels` to a modern model/capability client. Only then may the donor-only `workflowApi.ts` remainder and donor UI be deleted after exact recursive zero-caller, route, build and browser proof.

Later project-identity migration is separately gated on migrating every direct runtime `recipe_id` reader before the newest schema can stop requiring that compatibility field. Later recipe/execution endpoint retirement is gated on exact-scanning `recipesApi.ts`, `projectsApi.createUVProject()` and `projectsApi.getProjectExecutionPlan()`; those are not part of `donor-ui-retirement`.

Later Stage8 retirement is separately gated on migration/retirement of every runtime `get_stage8_workspace` caller, including render adapters and Product Orchestrator projections; it is not part of `donor-ui-retirement`.

D-066 layers 5-7 remain deferred until both D-070 gates are satisfied.
