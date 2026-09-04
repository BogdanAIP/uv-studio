# Legacy Surface Inventory — D-070 Caller / Migration Map

**Status:** ACTIVE MIGRATION EVIDENCE — `execution-plan-retirement`  
**Baseline:** lifecycle-closed `main` `af9ff888145661381caaacdec78244637058bce2`  
**Decision authority:** D-064 + D-065 + D-067 + D-070  
**Current update:** Draft PR #93 candidate `execution-plan-retirement`; not merged/accepted until exact-head CI, fresh independent review, merge and D-038 closure complete

This document is the behavior-preserving caller and retirement map required by D-070. It does **not** replace `CURRENT_ARCHITECTURE.md`, `UV_STUDIO_V2_ARCHITECTURE_MAP.md` or accepted decisions as runtime architecture authority.

Accepted history relevant to this map:

- PR #82 merged `donor-ui-retirement` as `c1eb609ec1e4c9db082eaa8338ac7f1e4938da11`;
- PR #89 merged `project-identity-v2-compat-reader` as `a0150e1543b8b4c8f5d3ae8d1b701118fcb112d2` after fresh semantic PASS and exact-head permanent CI;
- PR #90 lifecycle-closed that slice on `main` `1068694fac69eb02ff6e0651855c875c532e31a7`;
- PR #91 merged `recipe-entrypoint-retirement` as `050780d013276c3d3de9672244ad54da759f1ed3` after fresh semantic PASS and exact-head permanent CI;
- PR #92 lifecycle-closed PR #91 and produced current baseline `af9ff888145661381caaacdec78244637058bce2`;
- PR #93 is the current bounded D-070 candidate.

## 1. Inventory rules

Classifications:

- **KEEP** — canonical authority or reusable domain primitive in the target architecture.
- **ADAPT** — live compatibility seam whose callers must move before removal.
- **MOVE** — useful responsibility/state survives under canonical ownership.
- **LEGACY** — compatibility/persisted-project path only; no new modern callers.
- **DELETE LATER** — obsolete surface whose explicit later deletion gate has not passed.
- **RETIRED** — accepted removal completed and merged.
- **RETIREMENT CANDIDATE #93** — removed on the current PR head, but not accepted until PR #93 passes review/CI/merge/closure.

While D-070 is active:

1. no new modern caller may depend on Recipe Registry, Product Orchestrator, the retired execution-plan projection, Stage8 composition or donor workflow APIs;
2. modern creation is `Production Direction -> Studio Project`, never recipe-backed public creation;
3. old/imported projects remain recoverable through explicit compatibility state;
4. useful dubbing, targeted-edit, continuity and music state/operations survive composition retirement;
5. Stage-18 mutation fencing, Generation idempotency/D-017, canonical freshness, archive/recovery and Undo/Redo invariants remain baseline requirements;
6. each authority is retired in a bounded slice, not by a big-bang cleanup.

## 2. Current evidence and zero-caller discipline

GitHub Code Search has returned incomplete results for this repository, including empty results for symbols that were known to exist on the exact head. A zero search result is therefore **not** absence proof. Retirement evidence uses exact-head file inspection, explicit regression tests, permanent CI and fresh semantic review.

Accepted evidence through PR #92:

- donor Workflow/Pipeline/Sandbox/stage roots and write-capable donor frontend restoration are retired;
- canonical Project schema v2 and schema-v1 compatibility reader are accepted;
- exact legacy identity persists under `compatibility.recipe_id`; historical schema-v1 top-level `recipe_id` remains readable without read-time rewrite;
- public recipe catalog, recipe-backed project creation/rebinding and obsolete frontend recipe/create clients are retired;
- modern New Project discovers Production Directions and creates through `POST /api/uv/projects/studio`;
- compatibility fixtures seed canonical Project Store state directly instead of reopening retired public creation APIs.

Current PR #93 candidate evidence:

- the modern project page already used `getProjectWorkflow()` plus Studio Timeline/project APIs and had no supported `getProjectExecutionPlan()` caller to migrate;
- `frontend/lib/projectsApi.ts` no longer exports execution-plan types or `getProjectExecutionPlan()`;
- `uv_studio/api/execution.py` is deleted and `execution_router` is no longer mounted by `uv_studio/server.py`;
- `uv_studio/recipes/execution.py` and its recipe-derived execution projection exports are deleted;
- projection-only unit/API tests are removed and a focused `tests/test_execution_plan_retirement.py` regression protects the retired boundary;
- internal Recipe Registry remains available for Product Orchestrator and remaining compatibility readers;
- `/api/uv/projects/{id}/workflow`, Production Directions, Studio project creation, Project Store/archive/import compatibility and Stage8 remain intentionally present;
- Product Orchestrator already owns its own legacy readiness projection and does not import the deleted recipe execution projection.

The absence of a supported UI caller means this slice does not invent or migrate to a new readiness planner. Modern readiness, when needed by supported product behavior, continues to come from the relevant Production / Generation / Capability authorities; legacy `/workflow` remains a separately scheduled compatibility surface.

## 3. Canonical modern destination — KEEP

| Authority | Classification | Current role |
| --- | --- | --- |
| Project Store | **KEEP** | canonical modern and compatibility project persistence |
| Typed Studio identity (`extensions.studio`) | **KEEP** | modern project product identity |
| Production Directions | **KEEP** | new-project discovery and whole-project organization |
| Shared Scene / Shot / Take semantics | **KEEP** | Production semantic API, GUI and Agent actions |
| Canonical Timeline | **KEEP** | Studio commands, editor/export and Agent |
| Studio / Application Commands | **KEEP** | shared GUI/script/MCP/Agent mutation boundary |
| ProjectUnitOfWork + Undo/Redo | **KEEP** | canonical multi-document mutation/history |
| Model Registry + Generation Job Manager | **KEEP** | generation, idempotency and provenance |
| Capability Registry / D-017 / adapters | **KEEP** | availability/effects/auth/execution |
| Stage-15..18 Agent Harness | **KEEP** | orchestration over the same canonical authorities |

`ProductionDirection` is organization, not an execution pipeline. D-070 must not replace Recipe Registry or the retired execution plan with another Recipe-like planner.

## 4. Legacy / modern migration table

| Surface | Classification | Current compatibility reason / caller | Canonical destination / removal proof |
| --- | --- | --- | --- |
| schema-v1 top-level `recipe_id` / schema-v2 `compatibility.recipe_id` | **LEGACY** | old projects/archives, exact historical IDs, remaining compatibility readers | typed Studio identity for modern projects; preserve v1 import/recovery |
| `STUDIO_COMPAT_RECIPE_ID = "studio_v2"` | **LEGACY** | compatibility marker while old readers remain | typed Studio identity after remaining readers move |
| internal Recipe Registry / builtin declarations | **DELETE LATER** | Product Orchestrator and remaining legacy compatibility tests/readers | Production Directions + direct domain/Capability/Generation authorities; retire only after exact caller migration |
| public `/api/uv/recipes` | **RETIRED PR #91** | no supported modern caller | Production Directions |
| `frontend/lib/recipesApi.ts` | **RETIRED PR #91** | obsolete catalog client | Production Direction client |
| recipe-backed public `POST /api/uv/projects` | **RETIRED PR #91** | obsolete recipe creation | `POST /api/uv/projects/studio` |
| generic PATCH `recipe_id` switch | **RETIRED PR #91** | obsolete recipe rebinding | immutable modern identity / explicit migration only |
| `projectsApi#createUVProject` / `CreateProjectInput` | **RETIRED PR #91** | obsolete client creation surface | `createStudioProject()` + directions |
| `/api/uv/projects/{id}/execution-plan` / `api/execution.py` | **RETIREMENT CANDIDATE #93** | no supported UI caller; legacy tests only | no replacement planner; direct canonical authorities when readiness is required |
| `projectsApi#getProjectExecutionPlan` + execution-plan TS types | **RETIREMENT CANDIDATE #93** | stale client surface with no supported caller | removed with endpoint |
| `uv_studio/recipes/execution.py` | **RETIREMENT CANDIDATE #93** | recipe-derived projection used only by retired endpoint/projection tests | Product Orchestrator keeps its own bounded legacy workflow until its slice |
| `orchestration/project_workflow.py` and product projections | **ADAPT → DELETE LATER** | live legacy `/projects/{id}` compatibility | direct domain commands/contextual APIs + modern Studio |
| `api/project_workflow.py` / `productWorkflowApi.ts` | **ADAPT → DELETE LATER** | live legacy project-page compatibility | specialized domain clients / Studio APIs after caller migration |
| legacy `/projects/{id}` UI route | **LEGACY** | old/imported project compatibility and recovery | `/projects/{id}/studio` after explicit safe migration |
| modern `/projects/{id}/studio` | **KEEP** | canonical Studio workspace | none |
| Stage8 workspace state/API | **LEGACY** | legacy panels/tests plus General/Narrated render and Product Orchestrator consumers | canonical direction/input documents; migrate every runtime caller first |
| Stage8 composition/media panels | **LEGACY** | live legacy route | modern Studio/direction/contextual tools after route migration |
| `/api/stages` compatibility metadata | **DELETE LATER** | backend compatibility endpoint; donor frontend caller gone | exact route/test/reference proof |
| donor Workflow/Pipeline/Sandbox/stages frontend roots | **RETIRED PR #82** | removed | canonical Projects/Studio surfaces |
| donor `workflowApi.ts` | **RETIRED / EXTRACTED PR #82** | focused `/api/models` seam moved to `modelsApi.ts` | focused modern clients |
| write-capable donor frontend restoration | **RETIRED PR #82** | removed | Git checkout restoration + read-only provenance |
| vendor pipeline/session/sandbox backend | **DELETE LATER / VENDOR COMPAT** | pinned donor remains compile/provenance input | remove after adapter/package/import proof |
| VideoClaw backend `sys.path` injection | **DELETE LATER** | exact compatibility imports from pinned vendor tree | normal package/adapters after proof |

## 5. Stage6 / Stage8 rule

D-070 historical language mentions Stage6/8, but retirement is by concrete caller and responsibility, not by number. Stage8 has live runtime consumers and cannot be deleted as UI residue. Any surviving Stage6-named path must be classified by its actual authority before change.

## 6. Legacy identity destination map

| Legacy identity / mode | Destination | Type |
| --- | --- | --- |
| `story_video` | `micro_drama` | Production Direction |
| `commercial_product` | `commercial` | Production Direction |
| `music_video` | `music_video` | Production Direction + Music tools |
| `narrated_video` | `narrated_video` | Production Direction + narration/subtitle tools |
| `general_video` | `free_project` / explicit compatibility decision | migration decision |
| `dubbing` | ordinary dubbing contextual tool | tool; not automatically `dub_battle` |
| `free_project` targeted edit | targeted-edit contextual tool | tool |
| `photo_to_video` | photo composition capability | capability/tool |
| `visualizer` | audio visualization capability | capability/tool |
| `action_transfer` | action-transfer contextual capability | capability/tool |
| `digital_human` / `performance_lip_sync` | talking-character/lip-sync contextual capability | capability/tool |
| `studio_v2` | compatibility marker only | legacy metadata |

`dub_battle` remains a Production Direction because it organizes a whole dialogue/cast/takes/mix journey. Ordinary dubbing remains reusable inside other directions.

## 7. Domain state that survives composition retirement

| Domain | Keep / move | Composition to retire later |
| --- | --- | --- |
| Dubbing | transcript, translation, prepared speech, review, accept and render authorities | recipe-specific workflow projection/dispatch |
| Targeted edit | range, continuity/evidence, replacement plan/preparation/review/acceptance and render | `free_project` recipe as product engine |
| Continuity | continuity briefs, review evidence and sequence semantics | story-only workflow ownership assumptions |
| Music | Music Map, direction, assembly, review and project-owned state | recipe/Product Orchestrator action envelope where direct domain commands exist |

The extraction rule is: **move authority, preserve data identity**. Accepted artifacts/revisions and portable project state must not be orphaned by composition deletion.

## 8. Persisted-project gates

PR #89 completed the first identity gate. Later retirement still requires:

1. preserve schema-v1 archive import, including known-but-uncreatable and historically unknown IDs;
2. never silently guess a Production Direction for imported compatibility state;
3. use explicit migration when a later slice needs physical conversion;
4. keep source/media/artifact identities and canonical Timeline data stable;
5. retain export/import and Undo/Redo/recovery proof across compatibility state;
6. remove the legacy discriminator only after every supported compatibility reader has migrated; the v1 reader may remain indefinitely if needed.

PR #93 does not mutate persisted Project identity and does not require physical conversion of old projects.

## 9. Supported frontend boundary

```text
/
 -> /projects
     -> modern create via Production Directions
     -> /projects/{id}/studio       [canonical]
     -> /projects/{id}              [explicit legacy compatibility]
/settings
```

Modern creation uses Production Direction discovery plus `createStudioProject()` and opens `/studio`. The legacy route remains intentionally supported for old/imported projects; its Product Orchestrator/Stage8 panels are compatibility, not modern creation authority.

PR #93 removes only the unused execution-plan client/projection path. It does **not** remove the legacy project route, `/workflow`, Product Orchestrator, internal Recipe Registry or Stage8.

## 10. Compatibility evidence

Permanent CI still exercises old-project behavior without reopening retired public entrypoints.

Current evidence pattern:

- API/real-media compatibility tests create historical identity directly through `ProjectStore`;
- browser compatibility tests use `e2e/legacy_project_fixture.py` for canonical test-only seeding;
- user-visible interactions after fixture setup still execute through the real frontend/backend;
- Class-C cold-start creation remains fully user-visible through Production Directions;
- Project Store/archive/v1 transactions, Product Workflow, Stage8, dubbing/general/narrated/music/targeted-edit/commercial APIs and browser legacy-workspace outcomes remain covered;
- execution-plan-specific projection tests are intentionally removed with their authority, while the new retirement regression proves the removed files/client/server mount and preserved Recipe Registry/Product Workflow/Studio router boundaries.

Deleting a test is not proof by itself. Here the deletion is paired with exact caller classification, focused retirement regression and full permanent CI.

## 11. Golden vertical contract

The separate D-070 golden-vertical gate remains:

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

If Agent participates, it must use the same Production Semantic / Timeline / Generation / Capability authorities as GUI and scripts; it may not create private registries or direct canonical-file mutation paths. PR #93 does not claim this gate complete.

## 12. Bounded retirement sequence

1. **`donor-ui-retirement` — COMPLETE, PR #82.**
2. **`project-identity-v2-compat-reader` — COMPLETE, PR #89 + closure PR #90.**
3. **`recipe-entrypoint-retirement` — COMPLETE, PR #91 + closure PR #92.** Public recipe catalog/create/rebinding surfaces are retired; compatibility Registry remains.
4. **`execution-plan-retirement` — CURRENT PR #93 CANDIDATE.** Retire unused recipe execution-plan client/API/projection; preserve Product Orchestrator and Registry.
5. **legacy direction/tool migration slices.** Move old `/projects/{id}` workflows onto modern Studio/domain commands in bounded responsibility groups.
6. **contextual tool extraction slices.** Finish dubbing, targeted-edit, continuity and music ownership separation where Product Orchestrator still composes them.
7. **`product-orchestrator-retirement`.** Remove final recipe dispatch/projection after supported callers move.
8. **Stage8 runtime dependency migration / compatibility retirement.** Move remaining render/orchestrator consumers, then remove Stage8 after persisted-project proof.
9. **`micro-drama-golden-vertical`.** Accept one combined GUI project-to-export proof on the canonical spine; it may move earlier if independently provable.

A later item may be split further. Independent authorities must not be collapsed into one cleanup merely because they are all legacy.

## 13. Adjacent known issue

A previously observed Windows browser timing race can remount a production form after history refresh and discard in-progress Shot intent. It is outside execution-plan retirement. Browser failures must always be classified from exact logs rather than attributed to that historical race automatically.

## 14. Exit criteria for PR #93 inventory update

Before `execution-plan-retirement` can be accepted:

- no supported caller remains for the execution-plan endpoint/client;
- `api/execution.py`, `recipes/execution.py`, execution-plan client/types and server mount are absent;
- no replacement Recipe-like planner is introduced;
- Product Orchestrator `/workflow`, internal Recipe Registry, modern Production Directions/Studio creation and legacy read/import compatibility remain intact;
- current architecture/map/inventory/context describe the candidate state accurately;
- all five permanent CI jobs pass on the exact frozen head;
- a genuinely fresh ordinary-ChatGPT semantic review returns no actionable findings;
- merge is followed by mandatory D-038 lifecycle closure before the next D-070 slice begins.

Acceptance of PR #93 retires only the bounded execution-plan projection. It does not imply Product Orchestrator, Stage8, the legacy project route or legacy identity compatibility are gone.
