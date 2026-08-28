# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: independent-semantic-review -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in draft for `independent-semantic-review` on branch `chore/independent-semantic-review`, PR #79, starting from lifecycle-idle `main` merge `aa0d17308ca8c034175e4429f8535fb70dc8d026`.

The last completed product/architecture slice remains `architecture-compression-inventory`, merged through PR #77 as `c6831a36eb88289947eed1da65609654a2353524` and lifecycle-closed through PR #78. Its accepted exact caller/migration map satisfies the D-070 **architecture-compression gate**. The separate D-070 **golden-vertical gate** remains open.

The declared product handoff remains `donor-ui-retirement`; PR #79 is a bounded repository-process slice inserted before that implementation work so subsequent material PRs no longer depend on Codex Review quota.

## Independent semantic review under adoption

PR #79 introduces repository-owned semantic review infrastructure only; it does not change product/runtime/frontend/test behavior.

The target process is:

```text
implementation
 -> focused tests / preliminary CI
 -> freeze exact BASE_SHA + HEAD_SHA
 -> required fresh ordinary ChatGPT review via .agents/skills/code-review/SKILL.md
 -> optional @codex review when quota is available
 -> validate findings as CONFIRMED / REJECTED / SUPERSEDED
 -> fix confirmed findings
 -> material HEAD change makes the old review stale
 -> fresh required ordinary ChatGPT review
 -> optional fresh Codex review
 -> final exact-head CI / physical gates
 -> verify reviewed base/head + zero unresolved findings/threads
 -> expected-head merge
```

The mandatory primary reviewer is operationally independent: it runs in a fresh ordinary-ChatGPT context, is read-only, receives an immutable `REVIEW_REQUEST_V1`, reconstructs evidence from the repository and does not inherit the development chat's private reasoning or correctness argument.

ChatGPT Work, Workspace Agents, Codex automation and Codex Review cannot substitute for the mandatory primary review. `@codex review` remains a valuable optional second opinion when quota is available; confirmed quota exhaustion must be stated but does not block merge after the mandatory ordinary-ChatGPT review and all other gates pass.

The review policy is read from `BASE_SHA` while the target diff/code/docs/tests are read from `HEAD_SHA`, so a PR cannot weaken its own accepted review policy. Candidate findings must survive an explicit falsification pass before they are reported. The development context separately validates every reported finding before fixing it.

A one-time ordinary ChatGPT Scheduled Task may launch review only when the resulting reviewer can truthfully establish `review_context=ordinary_chat_fresh`; otherwise a manually opened fresh ordinary-ChatGPT conversation is required.

Because PR #79 introduces this mandatory-review policy for the first time, it is governed by the previously accepted merge discipline. After PR #79 merges, the new policy governs subsequent applicable material PRs.

## Accepted Stage 18 baseline

D-066 layer 4 bounded background Agent execution remains accepted infrastructure. Architecture compression and later retirement work must not weaken or bypass:

- the shared cross-runtime project mutation fence;
- Production/Timeline/project JSON serialization guarantees;
- exact canonical freshness for background claims;
- Generation same-key idempotency and one-shot D-017 consumption/reservation atomicity;
- foreground/background coordinator ownership;
- restart/recovery rules that avoid replay of ambiguous work.

## Accepted D-070 architecture inventory

The exact caller/migration map is recorded in `docs/architecture/LEGACY_SURFACE_INVENTORY.md`. Accepted findings are:

1. **Modern product composition is already separate from Recipe/Product Orchestrator.** New creation uses Production Directions and opens `/projects/{id}/studio`; the modern workspace uses Project/Timeline/Production semantics/Generation rather than `productWorkflowApi`.
2. **Legacy project workflows are still intentionally supported.** The project list exposes a separate “Старый совместимый workflow” link to `/projects/{id}` for legacy identity, and that route uses Product Orchestrator projections plus Dubbing/General/Music/Narrated/Continuity/Stage8 panels.
3. **schema-v1 `recipe_id` is durable compatibility state and still has direct runtime readers.** `ProjectDocument` still requires/serializes it, while typed modern Studio identity lives in `extensions.studio`; imported archives may retain unknown/uncreatable legacy recipe IDs for recovery. Music Analysis Assist, final Music Video review, Music Assembly and the General/Narrated render adapters also branch directly on `project.recipe_id`. `project-identity-v2-compat-reader` must migrate those guards to typed Studio identity/Production Direction or explicit v1 compatibility state before the newest schema can stop requiring the field.
4. **Recipe Registry and `/execution-plan` are compatibility seams, not modern authorities.** `/api/uv/recipes` still serves legacy creation/metadata; `/execution-plan` still resolves `project.recipe_id` and overlays Stage8 Capability readiness. Frontend also exports compatibility seams through `frontend/lib/recipesApi.ts`, `projectsApi.createUVProject()` and `projectsApi.getProjectExecutionPlan()`. Incomplete GitHub Code Search is not absence proof; the corresponding retirement PRs must exact-scan and migrate any real caller or delete the export with the endpoint.
5. **Product Orchestrator is mixed legacy composition over useful modern/domain primitives.** Its HTTP seam dispatches by recipe, but already delegates to Dubbing, Targeted Edit, Music and Capability authorities that must survive extraction.
6. **Stage8 is live runtime compatibility, not only legacy UI state.** Besides its workspace API/state, legacy panels and tests, `get_stage8_workspace` is consumed by `general_video_render.py`, `narrated_render.py` and Commercial/General/Narrated/Story Product Orchestrator projections. Stage8 cannot be retired until those runtime callers migrate or are retired and persisted-project compatibility is proven.
7. **Donor Workflow/Pipeline/Sandbox UI is the first retirement candidate, but `workflowApi.ts` is mixed.** The donor roots have no supported Next app route, while `/settings -> modelRegistry.ts -> workflowApi.fetchApiModels` is a real supported caller. `donor-ui-retirement` must move `fetchApiModels` to a modern model/capability client before deleting the donor-only remainder.
8. **Donor frontend restoration remains supported and verified through multiple paths.** `.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py` with and without `--force`, `tools/uv_dev.py`, Windows `scripts/setup-dev.ps1`, `docs/FRONTEND.md`, `tests/test_promote_frontend.py` and `.github/workflows/ci.yml` all participate in the current restore/provenance contract. `donor-ui-retirement` must eliminate or safely replace all write-capable restoration paths and migrate their write-behavior callers/tests while preserving only intended read-only provenance verification.
9. **Historical “Stage 6” is not treated as a deletion unit.** The accepted inventory classifies concrete surviving paths; no dedicated current Stage-6 runtime authority was positively established, and incomplete code search is not accepted as absence proof.

## No-new-caller rule

No new modern caller may be added to Recipe Registry, Product Orchestrator, `/execution-plan`, Stage8 composition or donor workflow APIs unless a later accepted decision explicitly reverses their legacy classification.

New work must target Production Directions, Shared Production Semantic Core, Studio/Application Commands, Generation/Model Job authority and Capability/D-017 boundaries.

## Domain state preservation

Dubbing, targeted edit, continuity and music are not deleted as collateral damage. Portable project state and reusable domain commands remain or move toward contextual tools/capabilities; only recipe/orchestrator/workspace composition is retired after caller and persisted-state proof.

## Accepted bounded retirement order

The accepted inventory supports this dependency-aware order:

1. `donor-ui-retirement` — first eliminate/replace every supported write-capable donor frontend restoration path and migrate its tests/CI expectations, preserving only read-only provenance checks; then extract the supported Settings model lookup from `workflowApi.ts`; then retire only donor-only UI/client remainder after zero-caller proof;
2. `project-identity-v2-compat-reader` — add explicit modern schema/identity migration and migrate every direct runtime `recipe_id` guard to typed Studio identity/direction or explicit v1 compatibility state before newest-schema identity drops the field;
3. `recipe-entrypoint-retirement` — exact-scan `frontend/lib/recipesApi.ts` and `projectsApi.createUVProject()`, migrate any supported caller or delete those clients with the legacy recipe-backed endpoints subject to persisted-project compatibility;
4. `execution-plan-retirement` — exact-scan `projectsApi.getProjectExecutionPlan()`, migrate any supported caller or remove only that helper/type surface with `/execution-plan`, while preserving the rest of live `projectsApi.ts`;
5. bounded legacy direction/tool migration slices;
6. contextual tool extraction where still needed;
7. `product-orchestrator-retirement` — only after supported legacy workflow callers have moved;
8. `stage8-runtime-dependency-migration` / `stage8-compatibility-retirement` — move remaining render-adapter consumers to canonical direction/input state, then retire Stage8 only after persisted-project and exact zero-runtime-caller proof;
9. combined `micro_drama` golden-vertical proof when the canonical spine is ready; it may move earlier if independently provable.

No big-bang rewrite is authorized by this list.

## D-070 gate state

The **architecture-compression gate is satisfied** by the accepted PR #77 inventory.

The **golden-vertical gate remains open**. Required combined user-visible proof remains:

`New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`

Existing tests prove important pieces separately, but this gate remains open until one accepted GUI outcome proves the combined path. If Agent is invoked, it must use the same Production/Timeline/Generation/Capability authorities as GUI/scripts/MCP.

D-066 layers 5-7 remain deferred until the golden-vertical gate is also satisfied.

## Verification state

PR #79 is an adoption/process PR. Its final exact head must pass the existing five permanent checks and have zero unresolved review conversations under the previously accepted merge policy. The new mandatory ordinary-ChatGPT semantic-review rule applies to subsequent applicable PRs after #79 is merged.

No runtime/product/frontend/test implementation is in the PR #79 write scope.

## Known adjacent implementation risk

Repeated Windows CI runs have exposed a timing-sensitive production-form remount race: `ProductionWorkspacePanel` keys the production semantics panel by history cursor, so a post-command history refresh can remount the form and discard Shot input entered before refresh completion. Exact-SHA reruns have alternated between pass and a timeout on the disabled “Создать кадр” button.

This remains a separate implementation defect/risk and is not silently folded into the review-policy or donor UI slices.

## Handoff

The next product slice remains `donor-ui-retirement` after PR #79 is merged and lifecycle-closed.

Its prerequisites are: (1) eliminate or safely replace all supported write-capable donor frontend restoration paths — `.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py` both with and without `--force`, plus `tools/uv_dev.py`, `scripts/setup-dev.ps1`, `docs/FRONTEND.md`, and the write-behavior expectations in `tests/test_promote_frontend.py` — while preserving only check-only provenance verification in `.github/workflows/ci.yml` if still required; (2) migrate `/settings -> modelRegistry.ts -> fetchApiModels` to a modern model/capability client. Only then may the donor-only `workflowApi.ts` remainder and donor UI be deleted after exact recursive zero-caller, route, build and browser proof.
