# Legacy Surface Inventory — D-070 Caller / Migration Map

**Status:** ACTIVE MIGRATION EVIDENCE — `architecture-compression-inventory`  
**Baseline:** lifecycle-closed `main` `e6d23e9444023c0c491ae0800d6aac01d415968c`  
**Decision authority:** D-064 + D-065 + D-067 + D-070  
**Current update:** PR #89 candidate `project-identity-v2-compat-reader`; not merged/accepted until its exact-head gates pass

This document is the behavior-preserving caller and retirement map required by D-070 before further Agent-autonomy work. It replaces the earlier short historical inventory as the current migration evidence for legacy product-composition surfaces. It does **not** become a third runtime architecture authority: `CURRENT_ARCHITECTURE.md`, `UV_STUDIO_V2_ARCHITECTURE_MAP.md` and accepted decisions still define the target architecture.

The original caller evidence below was collected on the accepted PR #77 baseline. Completion annotations for `donor-ui-retirement` describe the result merged through PR #82 as `c1eb609ec1e4c9db082eaa8338ac7f1e4938da11`. Stage-19 annotations describe the current PR #89 candidate state and must not be read as merged completion until its exact-head CI, independent review and lifecycle closure succeed.

## 1. Rules of this inventory

Classifications use the existing vocabulary:

- **KEEP** — canonical authority or reusable domain primitive that remains part of the target architecture.
- **ADAPT** — live compatibility seam whose callers must move before the seam can disappear.
- **MOVE** — useful responsibility/state survives, but ownership moves to a canonical direction/tool/command authority.
- **LEGACY** — supported compatibility or persisted-project path; no new modern callers.
- **DELETE LATER** — obsolete composition/UI/client code removable only after its explicit deletion gate passes.
- **RETIRED IN PR #82** — the accepted deletion/extraction gate was completed and merged through PR #82.

While D-070 is active:

1. no new modern caller may depend on Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 composition or donor workflow APIs;
2. old/imported projects remain recoverable until an explicit schema/project migration proves otherwise;
3. useful dubbing, targeted-edit, continuity and music state/operations are not deleted with obsolete product composition;
4. Stage-18 mutation fencing, Generation idempotency/D-017 reservation, exact canonical freshness and recovery guarantees remain baseline invariants;
5. removal is done in bounded follow-up PRs, never as an unrelated big-bang cleanup.

## 2. Evidence method and zero-caller rule

Positive callers below are bound to concrete files/routes/tests on baseline `e6d23e9444023c0c491ae0800d6aac01d415968c` unless explicitly annotated as updated by merged PR #82 or by the current PR #89 Stage-19 candidate.

GitHub Code Search returned `incomplete_results=true` for repository symbol searches during the original inventory, so a zero result by itself is **not accepted as proof of absence**. The donor-UI retirement therefore required checkout-local recursive proof plus build/browser/API evidence. Stage-19 likewise uses this accepted caller inventory plus exact changed-file evidence and tests rather than treating a zero search result as proof.

Merged donor-retirement evidence from PR #82 and current Stage-19 candidate evidence:

- **supported route proof** — the Next app tree keeps `/`, `/projects`, `/projects/[projectId]`, `/projects/[projectId]/studio`, `/settings`; no supported Workflow/Pipeline/Sandbox app route was introduced;
- **donor roots retired** — donor-only `WorkflowPanel`, `HomePage`, `TopBar`, `PipelinePage`, `Sandbox`, `BrandHeader` and `components/stages/**` were removed after exact recursive caller proof;
- **supported Settings seam extracted** — `/settings -> modelRegistry.ts` now obtains `/api/models` through focused `frontend/lib/modelsApi.ts`; the donor `frontend/lib/workflowApi.ts` remainder was removed;
- **write-capable restoration retired** — `.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py` and `tests/test_promote_frontend.py` were removed; `tools/uv_dev.py`, Windows `scripts/setup-dev.ps1` and `docs/FRONTEND.md` now restore tracked frontend source from Git rather than donor bytes;
- **retained vendor tool constrained** — `tools/vendor_videoclaw.py` rejects top-level `frontend/` and every descendant as a destination, so the general vendor CLI cannot recreate the retired overwrite authority;
- **provenance remains read-only** — `tools/verify_frontend_provenance.py` binds the lock to `vendor/videoclaw-app/.uv-upstream.json`, validates the top-level marker/digest from canonical Git blobs, and fails closed on tracked/staged/untracked donor drift without mutating maintained `frontend/`;
- **frontend endpoint-client compatibility edges** — `frontend/lib/recipesApi.ts` still exports list/get clients for `/api/uv/recipes`, while `frontend/lib/projectsApi.ts` still exports compatibility-only `createUVProject()` and `getProjectExecutionPlan()`. These belong to later bounded slices and are intentionally not mixed into Stage 19;
- **direct recipe-identity runtime edges — migrated in PR #89 candidate** — the accepted D-070 reader set `projects/music_analysis_assist.py`, `projects/music_video_review.py`, `projects/music_assembly.py`, `capabilities/adapters/general_video_render.py` and `capabilities/adapters/narrated_render.py` no longer branches directly on `project.recipe_id`; each now obtains the exact legacy identity through `compatibility_recipe_id`. This migrates only recipe-identity access and does **not** retire their later Stage8/Product-Orchestrator dependencies;
- **schema-v2 compatibility boundary — PR #89 candidate** — canonical Project persistence stores the legacy recipe discriminator under `compatibility.recipe_id`; historical schema-v1 top-level `recipe_id` remains accepted by the migration reader without read-time rewrite, including unknown/uncreatable IDs;
- **donor UI deletion proof satisfied by merged PR #82** — repository guards, exact recursive references, frontend lint/build, API integration and browser user-outcome checks cover the bounded deleted donor set. This does not claim later Recipe/Stage8/Product-Orchestrator compatibility is retired.

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
| historical schema-v1 `ProjectDocument.recipe_id` / schema-v2 `compatibility.recipe_id` | **LEGACY** | historical schema-v1 project/archive bytes keep top-level `recipe_id` and are migrated in memory without read-time rewrite; canonical schema v2 persists the exact discriminator under `compatibility.recipe_id`; `ProjectDocument.recipe_id` remains only a transition-time in-memory alias; unknown/uncreatable historical IDs remain exact. PR #89 candidate migrates the five accepted D-070 direct guards in Music Analysis Assist, Music Video review, Music Assembly, General Video render and Narrated render to `compatibility_recipe_id` | typed Studio identity / Production Direction for modern projects; explicit compatibility state only where legacy behavior still needs recipe identity | after PR #89 is merged/closed, remaining retirement still requires zero supported compatibility/API/orchestration readers that need legacy recipe identity, schema-v1 import/export and undo/redo recovery proof, and preservation of unknown historical IDs; do not remove the compatibility reader merely because direct guards moved |
| `STUDIO_COMPAT_RECIPE_ID = "studio_v2"` | **LEGACY** | neutral legacy compatibility marker for modern `extensions.studio` identity; historical v1 stores it as top-level `recipe_id`, while canonical v2 stores it under `compatibility.recipe_id` | typed Studio identity only | remove only when no supported legacy compatibility reader/API requires the marker; schema-v1 recovery remains supported independently |
| `uv_studio/recipes/**` / Recipe Registry | **DELETE LATER** | `api/recipes.py`, `api/projects.py`, `api/execution.py`, Product Orchestrator compatibility, recipe tests/import recovery | Production Directions for product organization; Capability/Generation authorities for operations; compatibility reader for old projects | modern creation/readiness has no registry dependency; old/imported recipe IDs still readable; execution-plan removed; compatibility route migration complete |
| `uv_studio/recipes/builtin.py` declarations | **DELETE LATER** | legacy provider-neutral recipe vocabulary, including general/narrated/music/story/commercial/action-transfer/digital-human/performance and Stage8 media modes | directions for whole-project journeys; contextual tools/capabilities for operations | per-ID mapping accepted and persisted-project compatibility retained |
| `uv_studio/orchestration/catalog.py` creatable catalog | **LEGACY** | `api/recipes.py` + legacy `api/projects.py` creation/update; advertises only Product-Orchestrator-owned recipes | `/api/uv/projects/studio/directions` for modern creation | legacy creation path no longer advertised/supported for new projects; old project reader/import still works |
| `uv_studio/orchestration/project_workflow.py` and package product projections | **ADAPT → DELETE LATER** | `api/project_workflow.py`; tests for general/narrated/music/dubbing/story/commercial/targeted edit | Direction documents + Production Semantic Core + domain commands/contextual tools | every supported legacy recipe has migrated UI/API or explicit read-only compatibility; no product projection caller remains |
| `uv_studio/api/recipes.py` `/api/uv/recipes` | **DELETE LATER** | legacy project/catalog tests and compatibility creation metadata | `/api/uv/projects/studio/directions` for modern creation; compatibility metadata only where needed for old projects | frontend/API has no modern caller; legacy import/project display no longer needs live recipe endpoint |
| `frontend/lib/recipesApi.ts` | **DELETE LATER** | exports `listUVRecipes()` / `getUVRecipe()` clients targeting `/api/uv/recipes`; no positive supported import established by the original inventory | Production Direction client for modern creation; bounded compatibility metadata only if a real legacy caller is found | exact recursive import/reference scan in `recipe-entrypoint-retirement`; migrate any discovered supported caller, otherwise delete the client with the recipe endpoint; build/browser/API CI green |
| `frontend/lib/projectsApi.ts#createUVProject` | **LEGACY → DELETE LATER** | compatibility-only recipe project creation; `CreateProjectInput` requires `recipe_id` and `createUVProject()` POSTs `/api/uv/projects` | `createStudioProject()` + Production Direction discovery for modern creation | exact recursive symbol/import scan in `recipe-entrypoint-retirement`; migrate any discovered compatibility caller or remove `CreateProjectInput`/`createUVProject()` with legacy recipe creation once old project read/import compatibility no longer depends on creating new recipe projects; preserve other live `projectsApi.ts` functions |
| `uv_studio/api/execution.py` `/execution-plan` | **DELETE LATER** | `tests_api/test_project_execution_api.py`; recipe execution readiness incl. Stage8 capability projection | direct Production/Generation/Capability readiness; no second project execution planner | all supported callers read canonical direction/tool/capability state directly; execution tests migrated; no frontend/runtime caller |
| `frontend/lib/projectsApi.ts#getProjectExecutionPlan` | **DELETE LATER** | exported client helper targeting `/execution-plan`; surrounding `projectsApi.ts` remains live | direct Production/Generation/Capability readiness where a real caller needs it; otherwise no replacement | exact recursive symbol/import scan in `execution-plan-retirement`; migrate any discovered caller or remove only this helper/type surface with the endpoint while preserving live `projectsApi.ts` project functions; build/browser/API CI green |
| `uv_studio/api/project_workflow.py` | **ADAPT → DELETE LATER** | live `/projects/[projectId]` compatibility UI through `productWorkflowApi`; domain workflow tests | direct domain commands/contextual APIs + modern Studio | legacy route migrated; every workflow action has one canonical command/capability equivalent; no recipe dispatch remains |
| `frontend/lib/productWorkflowApi.ts` | **ADAPT → DELETE LATER** | live legacy project page; already delegates some targeted-edit compatibility actions directly to newer APIs | direct specialized domain clients / Studio APIs | `/projects/[projectId]` no longer needs workflow projection/action dispatcher |
| legacy `/projects/[projectId]` route | **LEGACY** | project list explicitly exposes “Старый совместимый workflow” for legacy identity; imports Dubbing/General/Music/Narrated/Continuity/Stage8 panels | `/projects/[projectId]/studio` after project/direction migration, with contextual tools as needed | old/imported projects route safely to Studio or explicit recovery UI; browser tests cover migrated legacy projects |
| modern `/projects/[projectId]/studio` route | **KEEP** | `StudioProjectWorkspace` -> `ProductionWorkspacePanel` + `StudioWorkspace`; no Product Orchestrator dependency | canonical | none |
| Stage 8 workspace state/API (`projects.stage8_workspace`, `api/stage8_workspace.py`) | **LEGACY** | live legacy panels and Stage8 API/browser tests; runtime `get_stage8_workspace` callers still include `capabilities/adapters/general_video_render.py`, `capabilities/adapters/narrated_render.py`, and Product Orchestrator projections in `orchestration/commercial.py`, `general_video.py`, `narrated.py`, `story.py`. PR #89 changes only the adapters' recipe-identity access, not their Stage8 input dependency | direction-specific/shared input documents + project media/contextual tools; render adapters must consume canonical direction/input state rather than Stage8 workspace | persisted Stage8 projects migrated/read compatibly; legacy page/tests moved; every runtime adapter/orchestrator `get_stage8_workspace` caller migrated or retired; exact recursive import/reference proof shows no supported runtime caller remains |
| `Stage8CompositionPanel` / `Stage8MediaPanel` | **LEGACY** | imported by live `/projects/[projectId]` compatibility route | modern Studio/direction/contextual tools | legacy route migration completed; do **not** confuse with retired donor `components/stages/**` |
| server-mounted recipe/execution/project-workflow/stage8 routers | **LEGACY / ADAPT** | current UV-owned FastAPI route table | modern Studio/Production/Generation/domain routers | each individual route’s caller/migration gate satisfied; remove independently, not as one server rewrite |
| `/api/stages` compatibility metadata | **DELETE LATER** | former donor `workflowApi.fetchStages` caller is retired in PR #82; backend compatibility endpoint remains separate until exact route/test proof permits removal | no modern equivalent required | exact backend/test/reference proof; do not conflate with already-retired donor frontend client |
| `frontend/components/WorkflowPanel.tsx` | **RETIRED IN PR #82** | donor-only root had no supported Next route | modern Projects + Studio routes | satisfied by merged PR #82 recursive zero-caller proof + frontend build/browser checks |
| `frontend/components/HomePage.tsx` / `TopBar.tsx` | **RETIRED IN PR #82** | donor-only WorkflowPanel composition | Projects/Studio shell | satisfied with donor root deletion proof |
| `frontend/components/pipelines/PipelinePage.tsx` | **RETIRED IN PR #82** | donor-only unrouted pipeline root | contextual capabilities/tools inside Studio | satisfied by merged PR #82 |
| `frontend/components/Sandbox/Sandbox.tsx` | **RETIRED IN PR #82** | donor-only unrouted sandbox root | Model/Generation/Capability surfaces inside Studio | satisfied by merged PR #82 |
| `frontend/components/BrandHeader.tsx` | **RETIRED IN PR #82** | only donor roots depended on it | `AppShell` / UV Studio branding | satisfied after donor roots removed |
| `frontend/components/stages/**` | **RETIRED IN PR #82** | old donor six-stage state/UI only | Production Directions + shared Scene/Shot/Take + Studio | satisfied; live editor Stage8 panels remain distinct and untouched |
| `frontend/lib/workflowApi.ts` | **RETIRED / EXTRACTED IN PR #82** | supported `/settings -> modelRegistry.ts -> fetchApiModels` seam moved to `frontend/lib/modelsApi.ts`; donor-only remainder had no supported caller | focused `modelsApi.ts` for `/api/models`; modern specialized clients elsewhere | satisfied by contract regression test, recursive reference proof, lint/build/browser/API checks |
| write-capable donor frontend restoration | **RETIRED IN PR #82** | old promotion workflow/tool and write-behavior test removed; setup/dev/docs now restore tracked frontend from Git; vendor CLI is forbidden from targeting product frontend | Git checkout restoration + read-only `verify_frontend_provenance.py` | satisfied by merged PR #82; provenance remains verification only and cannot restore maintained `frontend/` |
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
| `studio_v2` | legacy compatibility marker preserved by the schema-v1 reader and schema-v2 compatibility state | legacy compatibility metadata |

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

Before Recipe Registry / legacy recipe identity / Stage8 compatibility can be retired:

1. establish an explicit newer project-schema/identity migration or compatibility reader; do not mutate Studio identity through generic project update. **PR #89 candidate establishes canonical schema v2 plus a schema-v1 compatibility reader, but this gate is accepted only after merge/lifecycle closure**;
2. migrate every supported direct reader that branches on legacy recipe identity to typed Studio identity / Production Direction or an explicit compatibility discriminator. **PR #89 candidate migrates the accepted five-reader D-070 set to `compatibility_recipe_id`; later slices must still exact-scan their own affected callers before deleting any compatibility surface**;
3. preserve import of schema-v1 archives, including known-but-uncreatable and historically unknown recipe IDs;
4. classify imported projects into modern direction, legacy compatibility or invalid recovery without silently guessing a direction;
5. provide an explicit migration command/path for legacy projects that can be mapped safely where a later slice needs physical migration; read/import compatibility alone must not silently rewrite them;
6. keep source/media/artifact identities and canonical Timeline data stable through migration;
7. prove export/import round-trip for both migrated modern projects and representative unmigrated v1 projects, including stable recovery snapshots under concurrent canonical mutation;
8. only after the remaining supported compatibility callers are migrated may the legacy discriminator itself become removable; the schema-v1 reader may retain it indefinitely.

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

Modern creation uses `listProductionDirections()` + `createStudioProject()` and opens `/studio`. The modern workspace uses Project/Timeline/History, Production semantics, Generation and Studio components rather than `productWorkflowApi`.

After merged PR #82, the old donor Workflow/Pipeline/Sandbox/stages roots are no longer physically present. `modelRegistry.ts` uses the focused `modelsApi.ts` for the preserved `/api/models` contract, and `workflowApi.ts` has been removed. Maintained `frontend/` source is restored from Git checkout rather than from pinned donor bytes. The retained vendor CLI cannot target `frontend/`, while read-only provenance verification remains available for the pinned comparison material. The explicit legacy `/projects/{id}` compatibility route and its Stage8/domain panels remain intentionally live and are not donor-UI residue.

## 10. Tests that currently bind compatibility behavior

Legacy paths cannot be declared dead while permanent CI intentionally exercises them. Representative surviving tests include:

- `tests_api/test_recipes_api.py`;
- `tests_api/test_recipe_creation_catalog_api.py`;
- `tests_api/test_project_recipe_validation.py`;
- `tests_api/test_project_execution_api.py`;
- `tests_api/test_project_workflow_api.py`;
- `tests_api/test_stage8_workspace_api.py`;
- dubbing/general/narrated/music/targeted-edit/commercial workflow API tests;
- browser recipe-workspace reconciliation and Stage8 composition/media outcomes.

PR #89 candidate adds/updates direct Project compatibility evidence in `tests/test_project_store.py`, `tests/test_project_identity.py`, `tests/test_project_archive.py`, `tests/test_project_transactions_v1_compat.py` and `tests_api/test_projects_api.py`. Those tests cover schema-v1/v2 read/write/archive/API identity behavior and durable legacy transaction recovery; they do not prove later Recipe/Execution Plan/Product Orchestrator/Stage8 retirement.

The retired promotion write-behavior suite is no longer current evidence. PR #82 replaces it with `tests/test_donor_ui_retirement.py` and `tests/test_frontend_provenance.py`, while permanent CI retains read-only provenance verification. Modern proof continues through production-semantics, Studio Timeline, cold-start, micro-drama and named-generation tests. Migration PRs must move or replace compatibility tests when authority moves; simply deleting tests is not removal proof.

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

1. **`donor-ui-retirement` — MERGED IN PR #82 as `c1eb609ec1e4c9db082eaa8338ac7f1e4938da11`.** The merged slice removes write-capable donor restoration, preserves read-only provenance, extracts `/api/models` to `modelsApi.ts`, deletes the unrouted donor Workflow/Pipeline/Sandbox/stage UI and donor-only `workflowApi.ts`, and guards the retained vendor CLI from targeting maintained `frontend/`.

Before continuing the product-migration sequence with item 2, the repository lifecycle inserts the bounded `actions-hardening` security/process slice. It changes GitHub Actions supply-chain controls only; it is not a new D-070 runtime migration authority.

2. **`project-identity-v2-compat-reader` — CURRENT PR #89 CANDIDATE.** Canonical Project persistence advances to schema v2 with exact legacy identity under `compatibility.recipe_id`; historical schema-v1 files/archives remain readable without read-time rewrite; unknown/uncreatable IDs stay exact; the accepted five direct runtime recipe-identity readers use the compatibility accessor; Project archive and transaction recovery cover the v1→v2 boundary. This item is not marked complete until PR #89 passes its final exact-head CI, fresh independent semantic review, merge and lifecycle closure.
3. **`recipe-entrypoint-retirement`** — move remaining modern/creation callers from Recipe Registry and `/api/uv/recipes`; exact-scan `frontend/lib/recipesApi.ts` and `projectsApi.createUVProject()`, migrate any real caller or delete those compatibility client exports with the recipe-backed creation/metadata endpoints; retain only bounded compatibility metadata if still required for reading/importing old projects.
4. **`execution-plan-retirement`** — replace `/execution-plan` with direct canonical Production/Generation/Capability readiness, migrate its tests, exact-scan callers of `projectsApi.getProjectExecutionPlan()`, and remove that helper/type surface with the endpoint once no supported caller remains.
5. **legacy direction/tool migration slices** — move old `/projects/{id}` recipe workflows onto modern Studio/domain commands in bounded responsibility groups rather than one rewrite.
6. **contextual tool extraction slices** — finish dubbing, targeted-edit, continuity and music ownership separation where Product Orchestrator still supplies composition.
7. **`product-orchestrator-retirement`** — remove final recipe dispatch/projection only when no supported route/API/test depends on it; this also removes the Commercial/General/Narrated/Story orchestration callers of Stage8.
8. **`stage8-runtime-dependency-migration` / `stage8-compatibility-retirement`** — migrate remaining runtime consumers such as `general_video_render.py` and `narrated_render.py` to canonical direction/input state, then remove Stage8 workspace/API/editor compatibility only after persisted projects migrate or have a supported reader path and exact proof shows no supported `get_stage8_workspace` caller remains.
9. **`micro-drama-golden-vertical`** — accept one combined GUI project-to-export proof on the canonical spine (may be moved earlier if preceding migrations make it independently provable).

A later slice may split an item further. It may not combine multiple independent authorities into a big-bang cleanup merely because they are all labelled legacy.

## 13. First retirement result

Merged PR #82 satisfies the first bounded donor retirement dependency set without deleting live compatibility surfaces:

- donor Workflow/Pipeline/Sandbox roots had no supported Next app route and are removed;
- modern project creation and Studio routes remain independent of those donor roots;
- the live legacy `/projects/[projectId]` route remains on `productWorkflowApi` and domain/Stage8 compatibility panels;
- the Settings model-listing seam moved from `workflowApi.ts` to focused `modelsApi.ts` with the same `/api/models` query contract;
- write-capable promotion/recovery paths were removed or redirected to Git checkout restoration;
- read-only canonical-blob provenance verification is retained and bound to vendored upstream identity;
- the retained `vendor_videoclaw.py` cannot target maintained `frontend/`.

This is merged/as-built state from PR #82, not pending candidate work. Its exact-head review, permanent CI and browser evidence were completed before merge; the lifecycle closure synchronizes the current authorities to that result.

### Current Stage-19 migration candidate

PR #89 is the bounded second D-070 migration candidate. Its current code makes schema v2 canonical, keeps historical schema-v1 bytes readable through explicit compatibility migration, moves the accepted direct recipe-identity readers behind `compatibility_recipe_id`, and preserves archive/transaction recovery across that boundary. This annotation is active candidate evidence only; subsequent retirement work must not treat Stage 19 as accepted until PR #89 is merged and lifecycle-closed.

## 14. Known adjacent defect — not part of this inventory

Closure CI exposed a Windows timing race in the production form: the production panel is keyed by history cursor, so a post-command history refresh can remount the form after a test/user begins the next input and discard local Shot intent. Repeated exact-SHA Windows runs alternated which “Создать кадр” scenario timed out; a later rerun passed all browser tests.

That is a separate implementation defect/risk. This inventory records it so it is not lost; changing the remount/busy behavior remains outside donor-ui-retirement.

## 15. Exit criteria for this inventory

The accepted inventory requires:

- this caller/migration map and the current architecture authorities agree;
- the no-new-caller rule is explicit;
- every remaining LEGACY/MOVE/DELETE LATER row names a replacement and deletion proof;
- persisted schema-v1 compatibility requirements are explicit;
- the bounded retirement order is dependency-valid;
- the golden vertical contract is explicit;
- each implementation slice passes its own exact-head repository checks and review.

Acceptance of the original inventory satisfied the D-070 **architecture-compression gate** by establishing the caller/migration map and bounded retirement sequence. It does **not** satisfy the separate **golden-vertical gate**. Follow-up migration/retirement slices execute the accepted map with their own proof.
