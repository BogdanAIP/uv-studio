# Legacy Surface Inventory — D-070 Caller / Migration Map

**Status:** ACTIVE MIGRATION EVIDENCE — `recipe-entrypoint-retirement`  
**Baseline:** lifecycle-closed `main` `1068694fac69eb02ff6e0651855c875c532e31a7`  
**Decision authority:** D-064 + D-065 + D-067 + D-070  
**Current update:** PR #91 candidate `recipe-entrypoint-retirement`; not merged/accepted until exact-head CI, fresh independent review, merge and D-038 closure complete

This document is the behavior-preserving caller and retirement map required by D-070. It does **not** replace `CURRENT_ARCHITECTURE.md`, `UV_STUDIO_V2_ARCHITECTURE_MAP.md` or accepted decisions as runtime architecture authority.

The accepted history relevant to this map is now:

- PR #82 merged `donor-ui-retirement` as `c1eb609ec1e4c9db082eaa8338ac7f1e4938da11`;
- PR #89 merged `project-identity-v2-compat-reader` as `a0150e1543b8b4c8f5d3ae8d1b701118fcb112d2` after fresh semantic PASS and exact-head permanent CI;
- PR #90 merged the mandatory D-038 lifecycle closure as `1068694fac69eb02ff6e0651855c875c532e31a7`;
- PR #91 is the current bounded D-070 candidate and must still pass its own acceptance gates.

## 1. Inventory rules

Classifications:

- **KEEP** — canonical authority or reusable domain primitive in the target architecture.
- **ADAPT** — live compatibility seam whose callers must move before removal.
- **MOVE** — useful responsibility/state survives under canonical ownership.
- **LEGACY** — compatibility/persisted-project path only; no new modern callers.
- **DELETE LATER** — obsolete surface whose explicit later deletion gate has not passed.
- **RETIRED** — accepted removal completed and merged.
- **RETIREMENT CANDIDATE #91** — removed in current PR code, but not accepted until PR #91 passes review/CI/merge/closure.

While D-070 is active:

1. no new modern caller may depend on Recipe Registry, Product Orchestrator, `/execution-plan`, Stage8 composition or donor workflow APIs;
2. modern creation is `Production Direction -> Studio Project`, never recipe-backed public creation;
3. old/imported projects remain recoverable through explicit compatibility state;
4. useful dubbing, targeted-edit, continuity and music state/operations survive composition retirement;
5. Stage-18 mutation fencing, Generation idempotency/D-017, canonical freshness, archive/recovery and Undo/Redo invariants remain baseline requirements;
6. each authority is retired in a bounded slice, not by a big-bang cleanup.

## 2. Current evidence and zero-caller discipline

GitHub Code Search has previously returned incomplete repository results, so a zero search result alone is not absence proof. Retirement slices use exact changed-file inspection, repository-local regression tests, build/API/real-media/browser evidence and fresh semantic review.

Accepted evidence before PR #91:

- donor Workflow/Pipeline/Sandbox/stage roots and write-capable donor frontend restoration were retired in PR #82;
- focused `/api/models` ownership moved to `frontend/lib/modelsApi.ts`;
- canonical Project schema v2 and the schema-v1 compatibility reader were accepted in PR #89;
- exact legacy identity now persists under `compatibility.recipe_id`; historical top-level schema-v1 `recipe_id` remains readable without read-time rewrite;
- the accepted direct runtime recipe-identity readers moved behind `compatibility_recipe_id` in PR #89;
- unknown/uncreatable historical recipe IDs remain recoverable exactly.

Current PR #91 candidate evidence:

- `frontend/lib/recipesApi.ts` is removed;
- `frontend/lib/projectsApi.ts` no longer exports `CreateProjectInput` or `createUVProject()`; live project list/get/archive/import/update and `getProjectExecutionPlan()` remain for their own slices;
- `/api/uv/recipes` is no longer mounted;
- recipe-backed public `POST /api/uv/projects` is retired;
- generic project PATCH can no longer change `recipe_id`;
- internal Recipe Registry remains available only for compatibility readers that have not yet been retired, including `/execution-plan` / Product Orchestrator work scheduled after this slice;
- supported New Project UI already discovers `/api/uv/projects/studio/directions` and creates through `POST /api/uv/projects/studio`;
- API and real-media fixtures that require historical recipe identity seed canonical `ProjectStore` state directly rather than pretending the retired public create route still exists;
- browser compatibility outcomes use `e2e/legacy_project_fixture.py` for the same bounded test-only seeding, while all user-visible interactions after setup still execute through the real frontend/backend;
- browser catalog reconciliation now checks Production Directions instead of the retired recipe catalog.

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

`ProductionDirection` is organization, not an execution pipeline. Directions share Project Store, Studio shell, Timeline, tools, models, jobs and command authority; D-070 must not replace Recipe Registry with another Recipe-like planner.

## 4. Legacy / modern migration table

| Surface | Classification | Current compatibility reason / caller | Canonical destination / removal proof |
| --- | --- | --- | --- |
| schema-v1 top-level `recipe_id` / schema-v2 `compatibility.recipe_id` | **LEGACY** | old projects/archives, exact unknown historical IDs, remaining compatibility readers | typed Studio identity for modern projects; remove only after no supported compatibility reader needs the discriminator and v1 import/recovery remains proven |
| `STUDIO_COMPAT_RECIPE_ID = "studio_v2"` | **LEGACY** | compatibility marker for modern Studio projects while old readers still exist | typed Studio identity only after remaining compatibility readers are gone |
| `uv_studio/recipes/**` / internal Recipe Registry | **DELETE LATER** | `/execution-plan`, Product Orchestrator and remaining legacy compatibility tests/readers | Production Directions + direct domain/Capability/Generation authorities; exact caller proof in later slices |
| `uv_studio/recipes/builtin.py` declarations | **DELETE LATER** | legacy provider-neutral recipe vocabulary for compatibility composition | directions for whole-project journeys; contextual tools/capabilities for reusable operations |
| public `/api/uv/recipes` | **RETIREMENT CANDIDATE #91** | no modern caller remains | Production Directions; exact-head API/browser proof and fresh review required before marking RETIRED |
| `frontend/lib/recipesApi.ts` | **RETIREMENT CANDIDATE #91** | no supported caller established | Production Direction client; frontend lint/build/browser proof required |
| recipe-backed public `POST /api/uv/projects` | **RETIREMENT CANDIDATE #91** | old compatibility tests formerly used it for fixture setup | `POST /api/uv/projects/studio` for modern users; ProjectStore-only test fixtures for historical compatibility evidence |
| generic PATCH `recipe_id` switch | **RETIREMENT CANDIDATE #91** | obsolete recipe rebinding surface | immutable modern Studio identity / explicit migrations only |
| `projectsApi#createUVProject` / `CreateProjectInput` | **RETIREMENT CANDIDATE #91** | compatibility-only client, no supported caller | `createStudioProject()` + Production Direction discovery |
| `/api/uv/projects/{id}/execution-plan` | **DELETE LATER** | legacy execution readiness/tests | direct Production/Generation/Capability readiness; next accepted slice `execution-plan-retirement` |
| `projectsApi#getProjectExecutionPlan` | **DELETE LATER** | compatibility client retained with endpoint | migrate exact callers or delete with `/execution-plan`; preserve unrelated live `projectsApi.ts` functions |
| `orchestration/project_workflow.py` and product projections | **ADAPT → DELETE LATER** | legacy `/projects/{id}` route and domain workflow tests | direct domain commands/contextual APIs + modern Studio |
| `api/project_workflow.py` / `productWorkflowApi.ts` | **ADAPT → DELETE LATER** | live legacy project page compatibility | specialized domain clients / Studio APIs after legacy route migration |
| legacy `/projects/{id}` UI route | **LEGACY** | explicit old/imported project compatibility and recovery | `/projects/{id}/studio` after safe project/direction migration |
| modern `/projects/{id}/studio` | **KEEP** | canonical Studio workspace | none |
| Stage8 workspace state/API | **LEGACY** | legacy panels/tests plus remaining General/Narrated render and Product Orchestrator consumers | canonical direction/input documents; migrate every runtime caller before retirement |
| Stage8 composition/media panels | **LEGACY** | live legacy route only | modern Studio/direction/contextual tools after route migration |
| `/api/stages` compatibility metadata | **DELETE LATER** | backend compatibility endpoint; donor frontend caller already gone | exact route/test/reference proof |
| donor Workflow/Pipeline/Sandbox/stages frontend roots | **RETIRED** | removed in PR #82 | canonical Projects/Studio surfaces |
| donor `workflowApi.ts` | **RETIRED / EXTRACTED** | `/api/models` seam moved to `modelsApi.ts`; remainder deleted in PR #82 | focused modern clients |
| write-capable donor frontend restoration | **RETIRED** | removed/redirected in PR #82 | Git checkout restoration + read-only provenance verification |
| vendor pipeline/session/sandbox backend | **DELETE LATER / VENDOR COMPAT** | pinned donor remains compile/provenance input; full donor route table is not mounted | remove only after adapter/package/import proof |
| VideoClaw backend `sys.path` injection | **DELETE LATER** | exact compatibility imports from pinned vendor tree | normal package/adapters after bootstrap/import proof |

## 5. Stage6 / Stage8 rule

D-070 historical language mentions Stage6/8, but retirement is by concrete caller and responsibility, not by number. Stage8 has live code and runtime consumers today; it therefore cannot be deleted as UI residue. No dedicated Stage6 module is assumed merely because the old architecture used that label.

Any later slice encountering a surviving Stage6-named path must classify its actual authority before changing it.

## 6. Legacy identity destination map

| Legacy identity / mode | Destination | Type |
| --- | --- | --- |
| `story_video` | `micro_drama` | Production Direction |
| `commercial_product` | `commercial` | Production Direction |
| `music_video` | `music_video` | Production Direction + Music domain tools |
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

PR #89 completed the first identity gate: schema v2 is canonical and schema-v1 compatibility remains explicit. Later retirement still requires:

1. preserve schema-v1 archive import, including known-but-uncreatable and historically unknown IDs;
2. never silently guess a Production Direction for imported compatibility state;
3. provide an explicit migration path when a later slice needs physical conversion;
4. keep source/media/artifact identities and canonical Timeline data stable;
5. retain export/import and Undo/Redo/recovery proof across compatibility state;
6. remove the legacy discriminator only after every supported compatibility reader has migrated; the v1 reader may retain it indefinitely if needed.

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

PR #91 does not remove the legacy route, `/execution-plan`, Product Orchestrator or Stage8. It removes only recipe-backed **creation/catalog/rebinding entrypoints** that no supported modern user path needs.

## 10. Compatibility evidence after PR #91 migration

Permanent CI still exercises old-project behavior, but fixtures must not resurrect retired public entrypoints.

Current pattern:

- API/real-media compatibility tests create exact historical identity directly through `ProjectStore`;
- browser compatibility tests use `e2e/legacy_project_fixture.py`, which writes the same canonical Project Store root used by the backend process;
- after fixture seeding, browser tests continue through real frontend/backend user controls and APIs;
- Class-C cold-start creation remains fully user-visible through Production Directions and does not use fixture seeding;
- browser reconciliation verifies preserved-only recipe identities are absent from the modern Production Direction catalog while an already-existing unsupported compatibility project remains readable and fail-closed.

Representative remaining compatibility test families include Project Store/archive/v1 transactions, Project Workflow, Stage8 workspace, execution-plan, dubbing/general/narrated/music/targeted-edit/commercial APIs and browser legacy workspace outcomes.

Tests must migrate with authority. Deleting a test is not proof of safe removal, and a test must not call a route that product code has intentionally retired merely to construct fixture state.

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

If Agent participates, it must use the same Production Semantic / Timeline / Generation / Capability authorities as GUI and scripts; it may not write canonical files directly or create private registries. The final accepted Take and export must be visible in canonical project/Timeline state.

PR #91 does not claim this separate gate complete.

## 12. Bounded retirement sequence

1. **`donor-ui-retirement` — COMPLETE, PR #82.**
2. **`project-identity-v2-compat-reader` — COMPLETE, PR #89 + closure PR #90.** Schema v2 is canonical; v1 compatibility and exact historical identity are preserved.
3. **`recipe-entrypoint-retirement` — CURRENT PR #91 CANDIDATE.** Retire public recipe catalog, recipe-backed project creation/rebinding and unused frontend recipe/create clients; preserve old-project read/import and internal Registry compatibility required by later slices.
4. **`execution-plan-retirement` — NEXT AFTER #91 MERGE + D-038 CLOSURE.** Replace `/execution-plan` and `getProjectExecutionPlan()` with direct canonical readiness.
5. **legacy direction/tool migration slices.** Move old `/projects/{id}` workflows onto modern Studio/domain commands in bounded responsibility groups.
6. **contextual tool extraction slices.** Finish dubbing, targeted-edit, continuity and music ownership separation where Product Orchestrator still composes them.
7. **`product-orchestrator-retirement`.** Remove final recipe dispatch/projection after supported callers move.
8. **Stage8 runtime dependency migration / compatibility retirement.** Move remaining render/orchestrator consumers, then remove Stage8 only after persisted-project compatibility and exact caller proof.
9. **`micro-drama-golden-vertical`.** Accept one combined GUI project-to-export proof on the canonical spine; may move earlier if independently provable.

A later item may be split further. Independent authorities must not be collapsed into one cleanup merely because they are all legacy.

## 13. Adjacent known issue

A previously observed Windows browser timing race can remount the production form after history refresh and discard in-progress Shot intent. It is not part of recipe-entrypoint retirement. A browser failure must be classified from exact logs rather than dismissed as that race: PR #91 already exposed deterministic stale test setup using retired HTTP entrypoints, which is being migrated in this slice.

## 14. Exit criteria for PR #91 inventory update

Before `recipe-entrypoint-retirement` can be accepted:

- runtime/frontend/docs agree that modern creation is Production Direction -> Studio Project;
- public recipe catalog/create/rebinding surfaces are absent;
- internal Registry remains only where later compatibility slices still require it;
- old/imported projects remain readable/importable without exposing new recipe creation;
- API + real-media + browser fixtures no longer depend on retired public recipe creation/catalog;
- all five permanent CI jobs pass on the frozen exact HEAD;
- a genuinely fresh ordinary-ChatGPT semantic review returns no actionable findings;
- merge is followed by mandatory D-038 lifecycle closure before `execution-plan-retirement` starts.

Acceptance of this update retires only the bounded entrypoint set. It does not imply `/execution-plan`, Product Orchestrator, Stage8, the legacy project route or the legacy identity reader are gone.
