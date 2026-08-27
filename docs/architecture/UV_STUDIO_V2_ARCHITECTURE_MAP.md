# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-064 + D-065 + D-066 + D-067 + D-068 + D-069  
**Date:** 2026-08-27

Classifications: **KEEP**, **ADAPT**, **MOVE**, **LEGACY**, **DELETE LATER**.

## 1. Current diagnosis

UV Studio now has a concrete shared production, generation and two-layer Agent-orchestration spine:

```text
Project Store
 -> Production Directions
 -> shared Scene / Shot / Take semantics
 -> Studio/Application Commands
 -> ProjectUnitOfWork / durable Undo-Redo
 -> canonical Timeline
 -> visible Model Registry
 -> Generation Job Manager / GenerationContract
 -> Capability Registry / D-017 / adapters
 -> Agent Harness layer 1: Context / Catalog / Policy / Trace       [Stage 15 merged]
 -> Agent Harness layer 2: Planner / durable Tasks / Skills         [Stage 16 merged]
 -> functional Subagents                                             [next D-066 layer 3]
```

The old product-composition errors remain rejected:

1. recipe/workspace proliferation as separate products;
2. one generic editor shell with insufficient production semantics;
3. a parallel Agent project/tool/permission authority.

D-064 owns Production Directions. D-065 owns shared production semantics. D-066 owns the ordered Agent Harness build-out. D-067 verifies current-document/product parity. D-068 owns later desktop in-place updates. D-069 owns provider-neutral sequential-generation lineage.

## 2. Target architecture

```text
                              Project
                                 |
                      Production Direction
       micro_drama | commercial | music_video | narrated | dub_battle | free
                                 |
                   Shared Production Semantic Core
                       Scene | Shot | Take
                                 |
                       Direction Extensions
                                 |
                         Shared Studio Core
       Media / Preview / Inspector / canonical Timeline / Export
                                 |
                    Studio / Application Commands
                                 |
                       ProjectUnitOfWork
                                 |
                    Model Registry + Job Manager
                                 |
                         Agent Harness
       Stage 15: Context -> Catalog -> Policy -> Trace            [merged]
       Stage 16: Planner -> durable Tasks -> Skills                [merged]
       next: functional Subagents
       later: background -> evaluate/repair -> takeover -> autonomy
                                 |
                       Capability Registry
                                 |
                    Adapter / Transport Registry
                 MLT / FFmpeg / MCP / local / cloud
```

All Agent mutations ultimately return to the same Studio/Application Commands or existing GenerationService authority. Agent state coordinates work; it does not redefine project truth.

## 3. Production Directions — KEEP + GROW

Current direction identity is typed Studio metadata. Direction-specific documents organize the workflow while shared concepts reuse shared semantic IDs.

| direction_id | Specialized organization |
| --- | --- |
| `micro_drama` | story, characters, locations, dramaturgy + shared Scenes/Shots/Takes |
| `commercial` | brief, product, brand, audience, concepts + shared Shots/Takes |
| `music_video` | song, Music Map, sections, visual direction + shared Shots/Takes |
| `narrated_video` | script, narration, semantic segments, subtitles/visual plan |
| `dub_battle` | source scene, dialogue, cast, mix policy + shared semantics where appropriate |
| `free_project` | no mandatory production-semantic structure |

A direction is not a provider, recipe execution engine or separate editor.

## 4. Shared Production Semantic Core — KEEP + GROW ONLY WHEN PROVEN

Stage 13 established:

- strict Scene / Shot / Take / accepted-Take contracts;
- multiple candidate Takes per Shot;
- project-owned media/provenance bindings;
- accepted production material -> canonical Timeline projection;
- direction extensions referencing shared identities;
- `ProductionSemanticService` as one shared mutation boundary;
- `ProjectUnitOfWork` across production/project/Timeline mutations;
- durable Undo/Redo;
- cross-direction proof.

Shot remains independent from Timeline Clip. Do not grow a giant film schema without cross-direction evidence.

## 5. Generation foundation — KEEP

Stage 14 implemented:

```text
Shot
 -> named Model
 -> GenerationContract
 -> idempotent Job / Attempt
 -> Capability / Adapter execution
 -> project-owned artifact + provenance
 -> Take candidate
 -> explicit acceptance
 -> canonical Timeline
```

Keep:

- backend-owned meaningful Model Registry;
- project-scoped Job/Attempt lifecycle;
- exact idempotency;
- explicit retry/failure/cancellation history;
- D-017 separation from Job replay;
- provider-neutral GenerationContract;
- D-069 parent media lineage;
- provider-private cache/session/latent state outside Project Store.

A real InfinityEdit/Helios continuation provider/UI remains later capability/product work, not Agent Harness scope.

## 6. Agent Harness layer 1 — Stage 15 IMPLEMENTED

PR #69 supplies the first internal foundation:

### Context Builder — KEEP

Bounded deterministic observation over canonical Project / Production / Timeline / Model / Job state. Nested collections use explicit limits/omitted counts. No project clone, secrets, host paths, raw provider prompts or private caches.

### Existing-authority action catalog — KEEP + GROW CAREFULLY

Current action metadata resolves only to existing UV services:

- ProductionSemanticService;
- TimelineCommandService;
- GenerationService.

The catalog exposes stable action ID, purpose/input fields, effects, authority, model requirement, Job Manager usage and possible D-017 routing. Unknown actions fail closed.

### Policy — KEEP

Policy consumes existing `CapabilityEffects`, availability, locality, cost and D-017 preparation facts. It cannot self-authorize.

### Trace — KEEP

Append-only project-scoped inspection records under the existing `tasks/` authority bind context digest, action/policy/effects, canonical identities, result refs and sanitized failures. Trace is not canonical production state.

### Bounded execution — KEEP

`AgentHarness` dispatches only through existing UV services. There is no generic file-write, shell or Python action.

## 7. Agent Harness layer 2 — Stage 16 IMPLEMENTED

PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2` after final exact-head CI #3442 passed all five permanent jobs and the fresh Codex review reported no major issues.

The merged implementation adds:

```text
bounded goal
 -> Stage-15 context/catalog/policy
 -> validated structured Planner proposal
 -> append-only AgentPlanRecord
 -> durable AgentTaskRecord dependency/state graph
 -> bounded Skill expansion
 -> foreground task execution through AgentHarness
 -> existing canonical transaction/Job result
 -> Stage-15 trace linked from durable task state
```

### Planner — KEEP UV-OWNED CONTRACT

Planning output is UV-validated structured data rather than a JarvisHub Canvas/node graph.

Validation includes:

- bounded plan/task counts;
- stable IDs;
- portable input payloads;
- action/Skill catalog membership;
- input-field/domain command contracts;
- dependency existence/cycle checks;
- Stage-15 context digest;
- policy availability;
- canonical reference/prerequisite checks against current state and dependency closure;
- exclusive Shot acceptance and valid video-track prerequisites.

A future model may propose this structure; deterministic UV validation remains authoritative.

### Durable Agent Tasks — KEEP AS ORCHESTRATION STATE

Task state lives under the existing project `tasks/` root. It does not replace Generation Jobs or ProjectUnitOfWork history.

Current bounded lifecycle:

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

Dependencies unlock only after success. Terminal tasks do not silently replay. Cross-runtime CAS and project task locking protect durable transitions.

### Skills — BOUNDED PROCEDURES, NOT NEW PERMISSIONS

A Skill expands into approved Agent catalog actions/tasks. It derives effects and authority from those actions.

First proof Skill:

- `production.scene_with_shot` -> create Scene -> dependent create Shot.

No Skill may introduce shell, Python, arbitrary filesystem/provider execution or D-017 bypass.

### Foreground coordinator — MERGED BOUNDARY

Stage 16 executes ready tasks in the foreground, binds execution-time context/policy/correlation evidence, links durable task state to existing Stage-15 trace and canonical result identities, and reconciles committed work on reopen without silent replay.

Functional subagents and background execution are not part of Stage 16.

## 8. D-066 remaining order

With Stage 16 merged and lifecycle-closed, the one declared next handoff is:

1. **Layer 3 — functional subagents:** bounded `explore / plan / media / critic` roles consuming the Planner/Task/Skill contracts.

Then:

2. **Layer 4 — background Agent work:** coordinated through existing Job Manager boundaries without hiding external replay/cost;
3. **Layer 5 — evaluation + dependency-aware local repair**;
4. **Layer 6 — human takeover/edit/resume**;
5. **Layer 7 — long-form autonomous production**.

Do not jump directly to long-form autonomy.

## 9. Product Truth — KEEP

D-067 keeps current docs, machine-readable feature contracts, backend/API/frontend and user-outcome evidence consistent.

The first visible record remains named generation -> Take. Stages 15–16 are internal Agent infrastructure; they do not claim a visible autonomous Agent product without a separate Studio surface and browser proof.

## 10. Desktop update layer — ACCEPTED TARGET, DEFERRED HERE

D-068 target:

```text
Settings / About
 -> current version
 -> Check for updates
 -> verified manifest/artifact
 -> controlled replacement
 -> restart / supported migrations
 -> healthy N+1 application
```

Release proof must include N-1 -> N in-place upgrade, not only clean install. Keep this separate from Agent implementation slices.

## 11. Contextual tools — NOT DIRECTIONS

Targeted edit, ordinary dubbing/translation, slideshow/photo-to-video, visualizer, action transfer, talking character, lip-sync, background transforms and image/video/audio generation are tools/capabilities inside a project, not new project identities.

## 12. Foundation inventory

| Area | Classification | Current meaning |
| --- | --- | --- |
| Project Store | **KEEP** | one portable project authority |
| Project refs/media | **KEEP** | canonical project-owned asset identity/provenance |
| Production Directions | **KEEP + GROW** | product organization/policy |
| Shared Scene/Shot/Take | **KEEP + GROW CAREFULLY** | common production semantics |
| Canonical Timeline / D-033 | **KEEP** | UV-owned assembly state, MLT derived |
| Studio/Application Commands | **KEEP + GROW** | shared GUI/Agent/scripts/MCP mutation authority |
| ProjectUnitOfWork | **KEEP** | transaction + Undo/Redo authority |
| Capability Registry / D-017 | **KEEP** | execution semantics/effects/auth |
| Model Registry | **KEEP** | meaningful model identity |
| Generation Job Manager | **KEEP** | execution provenance/idempotency/retry |
| GenerationContract | **KEEP** | provider-neutral semantic generation constraints |
| Stage-15 Agent foundation | **KEEP** | Context/Catalog/Policy/Trace/AgentHarness |
| Stage-16 Planner/Tasks/Skills | **KEEP** | merged D-066 layer 2 orchestration |
| Functional subagents | **NEXT** | bounded role specialization over merged Agent contracts |
| Product Truth | **KEEP** | cross-layer verification metadata |
| MCP | **KEEP** | optional capability/tool transport, not product state |
| Desktop Update Service | **FUTURE ACCEPTED** | D-068 maintained installation lifecycle |

## 13. Legacy / migration inventory

- Recipe Registry — **LEGACY**; compatibility/import vocabulary only.
- Product Orchestrator / `uv_studio/orchestration/*` — **MOVE + LEGACY**; extract useful logic into modern authorities.
- `api/project_workflow.py` — **LEGACY + EXTRACT**.
- `/execution-plan` and recipe execution — **LEGACY**.
- Stage 6/8 workspaces and specialized legacy project pages — **LEGACY UI**.
- donor-era pipeline/session/task/model frontend clients — **DELETE LATER** after caller proof.
- VideoClaw backend path injection — **DELETE LATER** after dependency/package proof.
- archived Windows packaging/runtime work — **KEEP AS ENGINEERING REFERENCE**.

Do not confuse legacy `uv_studio/orchestration/*` Product-Orchestrator-era code with the new bounded Agent orchestration under `uv_studio/agent/`.

## 14. Migration order

Completed:

1. D-064 Production Directions.
2. D-065 shared production semantics authority.
3. Modern Studio identity + ProjectUnitOfWork + Undo/Redo.
4. Stage 13 rich shared Scene/Shot/Take vertical.
5. Stage 14 Model Registry.
6. Stage 14 Job Manager/idempotency/attempts/provenance.
7. Stage 14 GenerationContract + D-069 lineage seam.
8. Stage 14 named generation -> project artifact -> Take -> acceptance -> Timeline.
9. Stage 14 first Product Truth record/proof.
10. **Stage 15 Context Builder + Action Catalog + Policy + Trace + bounded Agent execution.**
11. **Stage 16 Planner + durable Tasks + Skills.**

Next, in D-066 order:

12. functional subagents;
13. background Agent work;
14. evaluation/dependency-aware repair;
15. human takeover/edit/resume;
16. long-form autonomous production;
17. direction-domain growth/extraction of useful legacy tools as required;
18. compatibility retirement after caller proof;
19. D-068 maintained desktop update implementation/release proof when selected as its own slice.

## 15. Invariants

- one Project Store authority;
- one canonical Timeline;
- shared production identities where concepts truly overlap;
- no RecipeDefinition as new v2 product identity;
- no separate engine/workspace per direction;
- no Agent-only mutation path;
- no JarvisHub Canvas/node graph as canonical UV state;
- no duplicate Agent tool/protocol/permission authority;
- meaningful named model choice remains visible;
- remote/non-free execution remains explicit and authorized;
- external/cost-bearing generation is retry/idempotency safe;
- provider-private continuation state is not Project Store truth;
- Agent context/plan/tasks/skills/trace/role outputs are bounded orchestration/inspection state over canonical identities;
- Agent Task history does not replace Generation Job/Attempt provenance;
- current docs distinguish merged, active and future work;
- user-visible readiness requires D-067 parity/evidence, not implementation claims alone.
