# Legacy Surface Inventory — D-070 Caller / Migration Map

**Status:** ACTIVE MIGRATION EVIDENCE — `architecture-compression-inventory`  
**Baseline:** lifecycle-closed `main` `e6d23e9444023c0c491ae0800d6aac01d415968c`  
**Decision authority:** D-064 + D-065 + D-067 + D-070  
**Runtime change in this inventory:** none

This document is the behavior-preserving caller and retirement map required by D-070 before further Agent-autonomy work. It replaces the earlier short historical inventory as the current migration evidence for legacy product-composition surfaces. It does **not** become a third runtime architecture authority: `CURRENT_ARCHITECTURE.md`, `UV_STUDIO_V2_ARCHITECTURE_MAP.md` and accepted decisions still define the target architecture.

## 1. Rules of this inventory

Classifications use the existing vocabulary:

- **KEEP** — canonical authority or reusable domain primitive that remains part of the target architecture.
- **ADAPT** — live compatibility seam whose callers must move before the seam can disappear.
- **MOVE** — useful responsibility/state survives, but ownership moves to a canonical direction/tool/command authority.
- **LEGACY** — supported compatibility or persisted-project path; no new modern callers.
- **DELETE LATER** — obsolete composition/UI/client code removable only after its explicit deletion gate passes.

While D-070 is active:

1. no new modern caller may depend on Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 composition or donor workflow APIs;
2. old/imported projects remain recoverable until an explicit schema/project migration proves otherwise;
3. useful dubbing, targeted-edit, continuity and music state/operations are not deleted with obsolete product composition;
4. Stage-18 mutation fencing, Generation idempotency/D-017 reservation, exact canonical freshness and recovery guarantees remain baseline invariants;
5. removal is done in bounded follow-up PRs, never in this inventory.

## 2. Evidence method and zero-caller rule

Positive callers below are bound to concrete files/routes/tests on baseline `e6d23e9444023c0c491ae0800d6aac01d415968c`.

GitHub Code Search returned `incomplete_results=true` for repository symbol searches during this inventory, so a zero result is **not accepted as proof of absence**. The donor-UI assessment therefore distinguishes:

- **supported route proof** — the Next app tree contains `/`, `/projects`, `/projects/[projectId]`, `/projects/[projectId]/studio`, `/settings`; there is no supported Workflow/Pipeline/Sandbox app route;
- **known internal donor edges** — donor roots import `workflowApi`, `BrandHeader`, `TopBar` and `components/stages/**` directly;
- **supported shared-client edge** — `/settings` imports `frontend/lib/modelRegistry.ts`, which imports `fetchApiModels` from `frontend/lib/workflowApi.ts`; that function must move to a modern model/capability client before the remaining donor client can be deleted;
- **frontend endpoint-client compatibility edges** — `frontend/lib/recipesApi.ts` exports list/get clients for `/api/uv/recipes`, while `frontend/lib/projectsApi.ts` exports both compatibility-only `createUVProject()` (requires `recipe_id` and POSTs the legacy `/api/uv/projects` creation seam) and `getProjectExecutionPlan()` for `/execution-plan`. This inventory has not established a positive supported import for those exports, but incomplete Code Search is not absence proof; the relevant retirement PRs must exact-scan the checkout and either migrate any discovered caller or delete the client export with its compatibility endpoint;
- **direct recipe-identity runtime edges** — `projects/music_analysis_assist.py`, `projects/music_video_review.py`, `projects/music_assembly.py`, `capabilities/adapters/general_video_render.py` and `capabilities/adapters/narrated_render.py` load the project and branch directly on `project.recipe_id` to authorize Music Video / General Video / Narrated behavior. These callers must move to typed Studio identity / Production Direction or an explicit compatibility discriminator before the newest schema can stop requiring `recipe_id`;
- **repository restoration edges** — `.github/workflows/promote-frontend.yml` is manually dispatchable and runs `python tools/promote_frontend.py --force`, which replaces the UV-owned `frontend/` tree from pinned VideoClaw bytes; plain `python tools/promote_frontend.py` also creates that donor tree when `frontend/` is absent; `tools/uv_dev.py` and Windows `scripts/setup-dev.ps1` tell developers to run the plain command for a missing frontend; `docs/FRONTEND.md` documents the promotion/provenance mechanism; `tests/test_promote_frontend.py` directly asserts no-force creation and force replacement; `.github/workflows/ci.yml` runs that unit suite and separately invokes `tools/promote_frontend.py --check`;
- **final deletion proof** — the retirement PR must run an exact recursive import/reference scan from its checkout, prove no enabled workflow, developer tool, setup script, unit-test expectation, or documented supported recovery path can restore the deleted donor surfaces, preserve only intended read-only provenance checks, then lint + production build + permanent browser/API CI after deletion.

The inventory may nominate a first deletion candidate from route/caller evidence, but only the retirement PR may claim the zero-caller gate satisfied.

## 3. Canonical modern destination — KEEP

| Authority | Classification | Current callers / role | Retirement gate |
| --- | --- | --- | --- |
| Project Store | **KEEP** | all modern and compatibility project reads/writes | none |
| Typed Studio product identity (`extensions.studio`) | **KEEP** | modern project projection and route selection | none |
| Production Directions | **KEEP** | `/api/uv/projects/studio/directions`, new-project UI | none |
| Shared Scene / Shot / Take semantics | **KEEP** | Production semantic API, GUI, Agent action catalog | none |
| Canonical Timeline | **KEEP** | Studio commands, editor/export, Agent | none |
| Studio / Application Commands | **KEEP** | GUI, scripts, MCP, Agent shared mutation boundary | none |
| ProjectUnitOfWork + Undo/Redo | **KEEP** | canonical multi-document mutation/history | none |
| Model Registry + Generation Job Manager | **KEEP** | named generation, idempotency, provenance | none |
| Capability Registry / D-017 / adapters | **KEEP** | availability/effects/auth/execution | none |
| Stage-15..18 Agent Harness | **KEEP** | internal orchestration over the same commands/jobs | none |

`ProductionDirection` is explicitly not an execution pipeline. All directions share Project Store, Studio shell, Timeline, tools, models, jobs and command authority. That is the replacement model for product composition; it must not be wrapped by a new Recipe-like planner.

## 4. Exact legacy / modern caller and migration table

| Surface | Classification | Concrete current callers / compatibility reason | Canonical replacement | Proof required before removal |
| --- | --- | --- | --- | --- |
| schema-v1 `ProjectDocument.recipe_id` | **LEGACY** | mandatory in `uv_studio/projects/models.py`; serialized and required on read; archives may carry unknown/uncreatable legacy IDs; direct runtime guards also read it in `projects/music_analysis_assist.py`, `projects/music_video_review.py`, `projects/music_assembly.py`, `capabilities/adapters/general_video_render.py` and `capabilities/adapters/narrated_render.py` | typed Studio identity / Production Direction for modern projects; explicit compatibility discriminator in the v1 reader where legacy behavior still needs recipe identity | new schema/version or equivalent compatibility reader; migrate every direct runtime `recipe_id` guard to typed Studio identity/direction or explicit compatibility state before newest-schema `recipe_id` becomes optional; v1 import/export round-trip; legacy unknown recipe remains recoverable |
| `STUDIO_COMPAT_RECIPE_ID = "studio_v2"` | **LEGACY** | neutral schema-v1 compatibility marker for modern `extensions.studio` identity | typed Studio identity only | same identity/schema migration proof; no direct deletion in schema v1 |
| `uv_studio/recipes/**` / Recipe Registry | **DELETE LATER** | `api/recipes.py`, `api/projects.py`, `api/execution.py`, Product Orchestrator compatibility, recipe tests/import recovery | Production Directions for product organization; Capability/Generation authorities for operations; compatibility reader for old projects | modern creation/readiness has no registry dependency; old/imported recipe IDs still readable; execution-plan removed; compatibility route migration complete |
| `uv_studio/recipes/builtin.py` declarations | **DELETE LATER** | legacy provider-neutral recipe vocabulary, including general/narrated/music/story/commercial/action-transfer/digital-human/performance and Stage8 media modes | directions for whole-project journeys; contextual tools/capabilities for operations | per-ID mapping accepted and persisted-project compatibility retained |
| `uv_studio/orchestration/catalog.py` creatable catalog | **LEGACY** | `api/recipes.py` + legacy `api/projects.py` creation/update; advertises only Product-Orchestrator-owned recipes | `/api/uv/projects/studio/directions` for modern creation | legacy creation path no longer advertised/supported for new projects; old project reader/import still works |
| `uv_studio/orchestration/project_workflow.py` and package product projections | **ADAPT → DELETE LATER** | `api/project_workflow.py`; tests for general/narrated/music/dubbing/story/commercial/targeted edit | Direction documents + Production Semantic Core + domain commands/contextual tools | every supported legacy recipe has migrated UI/API or explicit read-only compatibility; no product projection caller remains |
| `uv_studio/api/recipes.py` `/api/uv/recipes` | **DELETE LATER** | legacy project/catalog tests and compatibility creation metadata | `/api/uv/projects/studio/directions` for modern creation; compatibility metadata only where needed for old projects | frontend/API has no modern caller; legacy import/project display no longer needs live recipe endpoint |
| `frontend/lib/recipesApi.ts` | **DELETE LATER** | exports `listUVRecipes()` / `getUVRecipe()` clients targeting `/api/uv/recipes`; no positive supported import established by this inventory, but incomplete Code Search is not zero-caller proof | Production Direction client for modern creation; bounded compatibility metadata only if a real legacy caller is found | exact recursive import/reference scan in `recipe-entrypoint-retirement`; migrate any discovered supported caller, otherwise delete the client with the recipe endpoint; build/browser/API CI green |
| `frontend/lib/projectsApi.ts#createUVProject` | **LEGACY → DELETE LATER** | explicitly documented in source as compatibility-only recipe project creation; `CreateProjectInput` requires `recipe_id` and `createUVProject()` POSTs `/api/uv/projects`; no positive supported import established by this inventory | `createStudioProject()` + Production Direction discovery for modern creation | exact recursive symbol/import scan in `recipe-entrypoint-retirement`; migrate any discovered compatibility caller or remove `CreateProjectInput`/`createUVProject()` with legacy recipe creation once old project read/import compatibility no longer depends on creating new recipe projects; preserve other live `projectsApi.ts` functions |
| `uv_studio/api/execution.py` `/execution-plan` | **DELETE LATER** | `tests_api/test_project_execution_api.py`; recipe execution readiness incl. Stage8 capability projection | direct Production/Generation/Capability readiness; no second project execution planner | all supported callers read canonical direction/tool/capability state directly; execution tests migrated; no frontend/runtime caller |
| `frontend/lib/projectsApi.ts#getProjectExecutionPlan` | **DELETE LATER** | exported client helper targeting `/execution-plan`; the surrounding `projectsApi.ts` remains a live project client, while no positive supported import of this helper is established by this inventory | direct Production/Generation/Capability readiness where a real caller needs it; otherwise no replacement | exact recursive symbol/import scan in `execution-plan-retirement`; migrate any discovered caller or remove only this helper/type surface with the endpoint while preserving live `projectsApi.ts` project functions; build/browser/API CI green |
| `uv_studio/api/project_workflow.py` | **ADAPT → DELETE LATER** | live `/projects/[projectId]` compatibility UI through `productWorkflowApi`; domain workflow tests | direct domain commands/contextual APIs + modern Studio | legacy route migrated; every workflow action has one canonical command/capability equivalent; no recipe dispatch remains |
| `frontend/lib/productWorkflowApi.ts` | **ADAPT → DELETE LATER** | live legacy project page; already delegates some targeted-edit compatibility actions directly to newer APIs | direct specialized domain clients / Studio APIs | `/projects/[projectId]` no longer needs workflow projection/action dispatcher |
| legacy `/projects/[projectId]` route | **LEGACY** | project list explicitly exposes “Старый совместимый workflow” for legacy identity; imports Dubbing/General/Music/Narrated/Continuity/Stage8 panels | `/projects/[projectId]/studio` after project/direction migration, with contextual tools as needed | old/imported projects route safely to Studio or explicit recovery UI; browser tests cover migrated legacy projects |
| modern `/projects/[projectId]/studio` route | **KEEP** | `StudioProjectWorkspace` -> `ProductionWorkspacePanel` + `StudioWorkspace`; no Product Orchestrator dependency | canonical | none |
| Stage 8 workspace state/API (`projects.stage8_workspace`, `api/stage8_workspace.py`) | **LEGACY** | live legacy panels and Stage8 API/browser tests; runtime `get_stage8_workspace` callers include `capabilities/adapters/general_video_render.py`, `capabilities/adapters/narrated_render.py`, and Product Orchestrator projections in `orchestration/commercial.py`, `general_video.py`, `narrated.py`, `story.py` | direction-specific/shared input documents + project media/contextual tools; render adapters must consume canonical direction/input state rather than Stage8 workspace | persisted Stage8 projects migrated/read compatibly; legacy page/tests moved; every runtime adapter/orchestrator `get_stage8_workspace` caller migrated or retired; exact recursive import/reference proof shows no supported runtime caller remains |
| `Stage8CompositionPanel` / `Stage8MediaPanel` | **LEGACY** | imported by live `/projects/[projectId]` compatibility route | modern Studio/direction/contextual tools | legacy route migration completed; do **not** confuse with donor `components/stages/**` |
| server-mounted recipe/execution/project-workflow/stage8 routers | **LEGACY / ADAPT** | current UV-owned FastAPI route table | modern Studio/Production/Generation/domain routers | each individual route’s caller/migration gate satisfied; remove independently, not as one server rewrite |
| `/api/stages` compatibility metadata | **DELETE LATER** | donor `workflowApi.fetchStages`; old six Chinese VideoClaw stages | no modern equivalent required | donor frontend/client zero-caller proof; route contract absent from supported tests/UI |
| `frontend/components/WorkflowPanel.tsx` | **DELETE LATER** | donor root: old six-stage UI; imports `workflowApi`, `TopBar`, `HomePage`, `components/stages/**`; no supported app route identified | modern Projects + Studio routes | exact recursive import scan proves no supported caller; delete + lint/build/browser CI |
| `frontend/components/HomePage.tsx` / `TopBar.tsx` | **DELETE LATER** | donor WorkflowPanel composition; old stage catalog/VideoClaw UX | Projects/Studio shell | same donor-root zero-caller gate |
| `frontend/components/pipelines/PipelinePage.tsx` | **DELETE LATER** | donor root; `standard`, `action_transfer`, `digital_human`; imports `workflowApi` + `BrandHeader`; no supported app route identified | contextual capabilities/tools inside Studio | exact recursive import scan; no supported route; lint/build/browser CI |
| `frontend/components/Sandbox/Sandbox.tsx` | **DELETE LATER** | donor root; imports donor API base/history/upload + BrandHeader; no supported app route identified | Model/Generation/Capability surfaces inside Studio | exact recursive import scan; no supported route; lint/build/browser CI |
| `frontend/components/BrandHeader.tsx` | **DELETE LATER** | known donor callers PipelinePage/Sandbox | `AppShell` / UV Studio branding | recursive import scan after donor roots removed |
| `frontend/components/stages/**` | **DELETE LATER** | old `WorkflowPanel` six-stage state/UI | Production Directions + shared Scene/Shot/Take + Studio | recursive import scan; do not delete live editor Stage8 panels by name similarity |
| `frontend/lib/workflowApi.ts` | **ADAPT → DELETE LATER** | mixed client: donor Workflow/Pipeline/Sandbox calls plus supported `/settings -> modelRegistry.ts -> fetchApiModels` model lookup | move `fetchApiModels` to a modern model/capability client; delete donor-only remainder after callers move | first prove Settings/modelRegistry uses the new client with unchanged model-selection behavior; then exact recursive scan proves no supported caller remains; donor roots gone; lint/build/browser CI green |
| donor frontend restoration (`.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py`, `tools/uv_dev.py`, `scripts/setup-dev.ps1`, `docs/FRONTEND.md`, `tests/test_promote_frontend.py`, `.github/workflows/ci.yml`) | **ADAPT → DELETE LATER** | workflow dispatch uses `promote_frontend.py --force` to replace maintained frontend bytes; plain `promote_frontend.py` recreates pinned donor bytes when `frontend/` is absent; `uv_dev.py` and Windows `setup-dev.ps1` recommend that restore; frontend support docs describe promotion/provenance; promotion unit tests assert no-force creation and force replacement; permanent CI runs those tests and separately invokes `--check` | read-only provenance verification with no write authority over maintained `frontend/`; replace write-behavior tests with tests for that safe contract; explicit archival/reconstruction flow outside the maintained product branch only if still required | disable/remove/replace every supported write-capable restoration path; update workflow/tool/setup/documentation callers; migrate write-behavior tests instead of deleting proof; preserve CI/read-only provenance validation where intended; prove no supported recovery/test/automation path can restore retired donor files |
| donor pipeline/session/sandbox backend from pinned upstream | **DELETE LATER / VENDOR COMPAT** | full upstream route table is not mounted by UV server; pinned vendor remains compile/provenance input | UV-owned Capability/Generation/domain routes | dependency/package/provenance proof shows no adapter still imports required donor runtime modules |
| VideoClaw backend `sys.path` injection in `uv_studio/server.py` | **DELETE LATER** | supports exact compatibility imports from pinned vendor tree even though full route table is unmounted | normal package/adapters without global path injection | import graph + package/bootstrap proof on Windows/Ubuntu; remove separately from donor frontend |

## 5. Stage 6 versus Stage 8

D-070 names “Stage 6/8” because earlier architecture used numbered workspace layers. On the current baseline, Stage 8 has concrete surviving code (`api/stage8_workspace.py`, project Stage8 workspace state and live compatibility panels/tests). It is also still consumed by runtime render adapters for General Video and Narrated Video and by Commercial/General/Narrated/Story Product Orchestrator projections, so Stage8 retirement is not a UI-only deletion problem.

This inventory does **not** invent a current `stage6` module merely to satisfy the historical label. No dedicated Stage-6 path has been established as a current runtime authority by the positive caller evidence collected here; GitHub Code Search was incomplete and therefore cannot prove total absence. Any retirement PR that encounters a surviving Stage-6-named file/caller must classify it by its real path and responsibility before deletion.

The migration unit is a concrete path/caller, not a historical stage number.

## 6. Recipe ID destination map

| Legacy identity / mode | Destination | Type |
| --- | --- | --- |
| `story_video` | `micro_drama` | Production Direction |
| `commercial_product` | `commercial` | Production Direction |
| `music_video` | `music_video` | Production Direction + Music Map domain tools |
| `narrated_video` | `narrated_video` | Production Direction + narration/subtitle tools |
| `general_video` | `free_project` / explicit compatibility decision, not a seventh direction | migration decision |
| `dubbing` | ordinary dubbing contextual tool | tool, **not** automatically `dub_battle` |
| `free_project` targeted-edit composition | targeted-edit contextual tool inside `free_project` | tool |
| `photo_to_video` | `video.compose_photos`-style contextual capability | capability/tool |
| `visualizer` | `audio.visualize`-style contextual capability | capability/tool |
| `action_transfer` | action-transfer contextual capability | capability/tool |
| `digital_human` / `performance_lip_sync` | talking-character/lip-sync contextual capability | capability/tool |
| `studio_v2` | schema-v1 compatibility marker only | legacy schema metadata |

`dub_battle` remains a Production Direction because it organizes an entire scene/dialogue/cast/takes/mix journey. Ordinary dubbing remains reusable inside other directions.

## 7. Domain state that must survive composition retirement

| Domain | Keep / move | Obsolete composition to retire later |
| --- | --- | --- |
| Dubbing | transcript/translation/prepared speech/review/accept/render domain authorities and project-owned references; expose as contextual tool | recipe-specific workflow projection and Product Orchestrator dispatch |
| Targeted edit | range selection, continuity/evidence, replacement plan/preparation/review/acceptance, render command | `free_project` recipe as product engine and workflow action dispatcher |
| Continuity | reusable continuity briefs/review evidence/sequence semantics | story-only workflow ownership assumptions |
| Music | Music Map, direction, assembly, review and current project-owned state | `music_video` recipe/Product Orchestrator action envelope where direct domain commands exist |

The extraction rule is “move authority, preserve data identity”. A deletion PR must prove portable project state remains readable and that accepted artifacts/revisions are not orphaned.

## 8. Persisted-project migration gates

Before Recipe Registry / `recipe_id` / Stage8 compatibility can be retired:

1. introduce an explicit newer project-schema/identity migration or compatibility reader; do not mutate Studio identity through generic project update;
2. before newest-schema `recipe_id` becomes optional, migrate every supported direct reader that currently branches on it — including Music Analysis Assist, final Music Video review, Music Assembly, General Video render and Narrated render — to typed Studio identity / Production Direction or an explicit compatibility discriminator supplied by the v1 reader;
3. preserve import of schema-v1 archives, including known-but-uncreatable and historically unknown recipe IDs;
4. classify imported projects into modern direction, legacy compatibility or invalid recovery without silently guessing a direction;
5. provide an explicit migration command/path for legacy projects that can be mapped safely;
6. keep source/media/artifact identities and canonical Timeline data stable through migration;
7. prove export/import round-trip for both migrated modern projects and at least representative unmigrated v1 projects;
8. only then stop requiring `recipe_id` in the newest schema; the v1 reader may still retain it indefinitely.

## 9. Supported frontend boundary

Current supported route structure:

```text
/
 -> /projects
     -> modern create via Production Directions
     -> /projects/{id}/studio       [canonical]
     -> /projects/{id}              [explicit legacy compatibility link]
/settings
```

Modern creation already uses `listProductionDirections()` + `createStudioProject()` and opens `/studio`. The modern workspace uses Project/Timeline/History, Production semantics, Generation and Studio components rather than `productWorkflowApi`.

The donor Workflow/Pipeline/Sandbox components are physically present and compile, but no corresponding supported `app/` route is identified. They remain the safest **component roots** for the first retirement slice. However, `workflowApi.ts` itself is mixed: `/settings` reaches `fetchApiModels` through `modelRegistry.ts`. The first retirement slice must extract that supported model lookup before deleting the donor-only remainder of the client. It must also eliminate or safely replace every supported donor-frontend restoration path and migrate its proof: the manually dispatchable `--force` workflow, the plain `promote_frontend.py` path, `uv_dev.py`, Windows `setup-dev.ps1`, `docs/FRONTEND.md`, and unit tests that assert write-capable promotion. Permanent CI may retain `promote_frontend.py --check` or an equivalent verifier only if it is read-only with respect to `frontend/`. The slice must still satisfy the strict recursive zero-caller/build gate above.

## 10. Tests that currently bind compatibility behavior

Legacy paths cannot be declared dead while permanent CI intentionally exercises them. Representative current tests include:

- `tests_api/test_recipes_api.py`;
- `tests_api/test_recipe_creation_catalog_api.py`;
- `tests_api/test_project_recipe_validation.py`;
- `tests_api/test_project_execution_api.py`;
- `tests_api/test_project_workflow_api.py`;
- `tests_api/test_stage8_workspace_api.py`;
- dubbing/general/narrated/music/targeted-edit/commercial workflow API tests;
- browser recipe-workspace reconciliation and Stage8 composition/media outcomes;
- `tests/test_promote_frontend.py`, whose current no-force/force write expectations must be migrated when write-capable donor restoration is retired, while the intended CI provenance check remains read-only.

Modern proof exists in parallel through production-semantics, Studio Timeline, cold-start, micro-drama and named-generation tests. Migration PRs must move or replace compatibility tests when authority moves; simply deleting tests is not removal proof.

## 11. Golden vertical contract

D-070 requires one combined user-visible proof:

```text
New Project
 -> micro_drama
 -> Scene
 -> Shot
 -> named generation Job
 -> Take candidate
 -> Accept
 -> canonical Timeline
 -> Export
```

Current tests prove important pieces separately (micro-drama Scene/Shot/Take/Timeline, named generation, and cold-start/export), but the gate is not considered satisfied until one accepted GUI user-outcome test proves the combined path on the canonical Studio route.

If Agent participates in that proof:

- it must call the same `ProductionSemanticService` / Timeline command / `GenerationService` authorities exposed to other callers;
- it must not write project/production/timeline files directly;
- it must not create a private model/job/capability registry;
- D-017 and Generation idempotency remain unchanged;
- the final accepted Take and export must be visible through canonical project/Timeline state, not Agent trace alone.

## 12. Bounded retirement / extraction sequence

The intended order is deliberately small-slice and dependency-aware:

1. **`donor-ui-retirement`** — first eliminate or safely replace every supported write-capable donor restoration path (`promote-frontend.yml`, `promote_frontend.py` with and without `--force`, `uv_dev.py`, Windows `setup-dev.ps1`, `docs/FRONTEND.md`) and migrate `tests/test_promote_frontend.py` away from write-behavior assertions while preserving only read-only CI provenance verification; move the supported `workflowApi.fetchApiModels` dependency used by `/settings -> modelRegistry.ts` to a modern model/capability client; then remove only the unrouted donor Workflow/Pipeline/Sandbox/stage UI and donor-only remainder of frontend client glue after exact recursive zero-caller proof; retire `/api/stages` only if that same proof shows no supported caller.
2. **`project-identity-v2-compat-reader`** — add explicit modern schema/identity migration while preserving schema-v1 import/read compatibility; migrate all direct runtime `recipe_id` readers to typed Studio identity/direction or explicit v1 compatibility state before newest-schema identity stops requiring the field.
3. **`recipe-entrypoint-retirement`** — move remaining modern/creation callers from Recipe Registry and `/api/uv/recipes`; exact-scan `frontend/lib/recipesApi.ts` and `projectsApi.createUVProject()`, migrate any real caller or delete those compatibility client exports with the recipe-backed creation/metadata endpoints; retain only bounded compatibility metadata if still required for reading/importing old projects.
4. **`execution-plan-retirement`** — replace `/execution-plan` with direct canonical Production/Generation/Capability readiness, migrate its tests, exact-scan callers of `projectsApi.getProjectExecutionPlan()`, and remove that helper/type surface with the endpoint once no supported caller remains.
5. **legacy direction/tool migration slices** — move old `/projects/{id}` recipe workflows onto modern Studio/domain commands in bounded responsibility groups rather than one rewrite.
6. **contextual tool extraction slices** — finish dubbing, targeted-edit, continuity and music ownership separation where Product Orchestrator still supplies composition.
7. **`product-orchestrator-retirement`** — remove final recipe dispatch/projection only when no supported route/API/test depends on it; this also removes the Commercial/General/Narrated/Story orchestration callers of Stage8.
8. **`stage8-runtime-dependency-migration` / `stage8-compatibility-retirement`** — migrate remaining runtime consumers such as `general_video_render.py` and `narrated_render.py` to canonical direction/input state, then remove Stage8 workspace/API/editor compatibility only after persisted projects migrate or have a supported reader path and exact proof shows no supported `get_stage8_workspace` caller remains.
9. **`micro-drama-golden-vertical`** — accept one combined GUI project-to-export proof on the canonical spine (may be moved earlier if preceding migrations make it independently provable).

A later slice may split an item further. It may not combine multiple independent authorities into a big-bang cleanup merely because they are all labelled legacy.

## 13. First retirement recommendation

The caller map supports `donor-ui-retirement` as the provisional first bounded slice because:

- donor Workflow/Pipeline/Sandbox roots have no supported Next app route identified;
- modern project creation and Studio routes do not import those donor roots;
- the live legacy `/projects/[projectId]` route uses `productWorkflowApi`, not the donor workflow UI;
- the only supported caller found inside `workflowApi.ts` is the model-listing seam `/settings -> modelRegistry.ts -> fetchApiModels`, which can be extracted first rather than forcing retention of the donor UI;
- repository/developer/setup recovery and its current unit tests can recreate or assert recreation of the donor frontend, so all write-capable restoration entry points and their callers/tests must be migrated before deletion is durable;
- the permanent CI provenance check is useful evidence but must remain read-only rather than preserving write authority;
- removing donor UI does not require changing schema-v1 project identity or Stage8 persisted state.

This is a **candidate, not a deletion claim**. The follow-up PR must first eliminate every supported donor restoration write path and migrate its write-behavior tests while preserving only read-only provenance checking if required, preserve Settings/model selection through the extracted modern client, then prove exact recursive zero supported callers for every deleted donor file/client remainder and preserve the supported route/build/browser contract.

## 14. Known adjacent defect — not part of this inventory

Closure CI exposed a Windows timing race in the production form: the production panel is keyed by history cursor, so a post-command history refresh can remount the form after a test/user begins the next input and discard local Shot intent. Repeated exact-SHA Windows runs alternated which “Создать кадр” scenario timed out; a later rerun passed all browser tests.

That is a separate implementation defect/risk. This inventory records it so it is not lost, but changing the remount/busy behavior would violate the behavior-preserving write scope of PR #77.

## 15. Exit criteria for this inventory

The inventory slice may enter review when:

- this caller/migration map and the two current architecture authorities agree;
- the no-new-caller rule is explicit;
- every LEGACY/MOVE/DELETE LATER row names a replacement and deletion proof;
- persisted schema-v1 compatibility requirements are explicit;
- the bounded retirement order and first candidate are named;
- the golden vertical contract is explicit;
- runtime diff is empty;
- permanent repository checks pass on the exact review head.

Acceptance of this inventory satisfies the D-070 **architecture-compression gate** by establishing the accepted exact caller/migration map and bounded retirement sequence. It does **not** satisfy the separate **golden-vertical gate**. The follow-up migration/retirement slices execute the accepted map with their own proof, but they are not prerequisites for the architecture-compression gate itself.