# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-064 + D-065 + D-066 + D-067 + D-068  
**Date:** 2026-08-25

This is the practical migration map for a coherent local-first AI production studio without rewriting proven foundations.

Classifications: **KEEP**, **ADAPT**, **MOVE**, **LEGACY**, **DELETE LATER**.

## 1. Diagnosis

The repository now has a concrete lower production spine:

```text
Project Store
 -> Production Directions
 -> shared Scene / Shot / Take semantics
 -> Studio/Application Commands
 -> ProjectUnitOfWork / durable Undo-Redo
 -> canonical Timeline
 -> Capability execution / MLT / FFmpeg / domain tools
```

Two earlier product-composition errors were corrected:

1. recipe/workspace proliferation — separate recipe orchestration/workspaces pretending to be products;
2. generic-editor overcorrection — one Media/Preview/Timeline shell with insufficient production semantics.

D-064 restored meaningful Production Directions. D-065 prevented six parallel domain models by sharing genuinely common Scene/Shot/Take semantics. Stage 13 has now implemented and tested that shared production-semantic path.

The next missing layer is reliable named-model generation/jobs, followed by an autonomous Agent Harness. D-066 designates JarvisHub as the reference architecture/method donor for that Agent Harness while preserving UV-owned product state.

D-067 adds a permanent Product Truth verification layer so backend, frontend, current docs and E2E evidence cannot silently describe different products. D-068 adds the desktop release update contract: one maintained installation, in-place update UI/Service and N-1 -> N upgrade evidence.

## 2. Target architecture

```text
                              Project
                                 |
                      Production Direction
       micro_drama | commercial | music_video | narrated | dub_battle | free
                                 |
                   organization / policy / navigation
                                 |
                   Shared Production Semantic Core
            Scene | Shot | Take / Accepted Take
          semantic refs | continuity | asset/timeline bindings
                                 |
                      Direction Extensions
      story/characters/locations | product/brand | Music Map | etc.
                                 |
                         Shared Studio Core
        Media/Assets | Preview/Canvas | Inspector/AI/Model Picker
                         Canonical Timeline
                                 |
                    Studio / Application Commands
                 same GUI / Agent / scripts / MCP
                                 |
                       Project Unit of Work
       production docs + direction extensions + assets + timeline
                                 |
                    Model Registry (visible)
                                 |
                   Project Job Manager
          idempotency | attempts | provenance | cancellation
                                 |
                       Capability Registry
                                 |
                  Adapter / Transport Registry
                 MLT / FFmpeg / MCP / local / cloud

Cross-cutting Product Truth verification (D-067)
  current docs <-> feature contracts <-> backend <-> frontend <-> E2E

Later Agent Harness (JarvisHub donor patterns)
  Director runtime
   -> context / memory / compaction
   -> Planner / Tasks / Skills
   -> explore / plan / media / critic
   -> policy / effects / trace
   -> background work via Job Manager
   -> evaluation / dependency-aware repair
  ALL mutations -> same Studio/Application Commands

Desktop release layer (D-068)
  Settings/About Update UI
   -> Update Service
   -> verified release manifest/artifact
   -> out-of-process updater/installer
   -> one maintained UV Studio installation
```

A project instantiates only the semantic/domain state it needs. The Production Semantic Core is not a mandatory giant film schema and is not a second Timeline.

## 3. Production Directions — KEEP + GROW

Primary current paths:

- `uv_studio/production/directions.py`;
- `/api/uv/projects/studio/directions`;
- Studio metadata in `project.json`;
- `/projects` direction cards.

Initial directions:

| direction_id | Organization / specialized extension |
| --- | --- |
| `micro_drama` | story, characters, locations, dramaturgy; shared Scenes/Shots/Takes |
| `commercial` | brief, product, brand, audience, concepts; shared Shots/Takes |
| `music_video` | song, Music Map, sections, visual direction; shared Shots/Takes |
| `narrated_video` | script, narration, semantic segments, subtitles/visual plan |
| `dub_battle` | source scene, dialogue, cast, mix policy; shared Scene/Takes where applicable |
| `free_project` | no mandatory production-semantic structure |

A direction is not a `RecipeDefinition`, provider or execution engine.

## 4. Shared Production Semantic Core — KEEP + GROW (Stage 13 implemented)

Stage 13 implemented the first bounded shared primitives and the rich micro-drama proof:

- strict shared Scene / Shot / Take / accepted-Take contracts;
- multiple candidate Takes per Shot;
- project-owned asset/provenance bindings;
- accepted-production-material -> canonical Timeline projection;
- micro-drama Story / Characters / Locations / continuity/canon extensions referencing shared identities;
- cross-direction reuse of the shared contracts from commercial;
- application-service mutation boundary through `ProductionSemanticService`;
- Stage-12 `ProjectUnitOfWork` across acceptance, media provenance and Timeline;
- durable project-level Undo/Redo of acceptance projection;
- visible Studio/browser proof with real media.

Shot remains independent from Timeline Clip. Direction extensions reference shared identities instead of defining private duplicate Shot/Take systems.

The semantic core should now grow only when new directions prove a genuinely shared production concept.

## 5. Contextual tools — NOT DIRECTIONS

Targeted edit, ordinary dubbing/translation, slideshow/photo-to-video, visualizer, action transfer, talking character, lip-sync, background transforms and image/video/audio generation are contextual tools. They may be prominent in a direction without becoming its product engine.

## 6. Foundation inventory

### Project Store — KEEP + ADAPT

Keep atomic file persistence, strict portable JSON, path/symlink protection, project-owned refs and archive integrity.

Delivered foundation includes typed Studio/Production Direction identity, explicit legacy compatibility mode, bounded production/domain storage and Project Unit of Work for multi-document transactions.

### Project references/media — KEEP

Remain the base for Media Bin, generated assets and production bindings. Provider URLs/host paths never become canonical identity.

### D-033 editor foundation — KEEP + EXPAND

MLT stays behind UV adapter; OpenCut is a selective UI/interaction donor; UV owns canonical Timeline/commands; FFmpeg remains deterministic export/media substrate where used.

### Studio/Application Commands — KEEP + GROW

Timeline and production semantic commands are shared authority. GUI, Agent, scripts and MCP converge here. No Agent-only mutation path.

### Project Unit of Work — CURRENT FOUNDATION

Coordinates Studio identity/project metadata, shared production documents, refs/assets, Timeline and undo history.

```text
AcceptTake(shot_12_3, take_4)
 -> accepted Take
 -> asset/reference binding
 -> Timeline projection/update
 -> one transaction / reversible undo
```

### Capability Registry — KEEP + EXTEND EFFECT VISIBILITY

Execution semantics/availability/locality/cost/authorization only. It remains below visible Model Registry and below production composition.

D-066 adapts JarvisHub's useful action-effect pattern into the existing UV boundary rather than creating a second tool registry. Relevant future metadata may include project mutation, Timeline mutation, media generation, destructive behavior, long-running behavior, reversibility and cost-bearing execution.

### Model Registry — NEXT TARGET

Backend-owned and user-visible for meaningful model selection; maps named models/modes onto capabilities/offers/adapters without making provider transport product identity.

### Job Manager — NEXT TARGET

Project-scoped queued/running/succeeded/failed/cancelled generation lifecycle, cancellation/retry, attempts and exact provenance.

D-066 adds a non-negotiable reliability requirement: long-running/cost-bearing/external execution is idempotent. Equivalent replay must not execute twice; same idempotency key with materially different normalized context fails closed.

### Generation Contract — NEXT TARGET

Provider-neutral constraints for a generation request/attempt associated with production intent. Initial concepts:

- fixed constraints;
- editable variables;
- forbidden semantic changes;
- approved project reference/keyframe identity where applicable.

Adapters render the contract into provider prompts/options. Provider prompt text is not canonical production truth.

### Product Truth Contracts — NEW VERIFICATION TARGET

D-067 adds machine-readable verification metadata for user-visible features. A Product Truth Contract connects feature identity to the canonical command/query, backend/API surface, frontend entry, canonical state/dependencies and end-to-end proof.

It is not runtime product authority. Its job is to catch:

- current-documentation drift;
- backend features advertised as ready without required UI;
- frontend controls without canonical backend behavior;
- missing user-outcome proof.

The next named-model generation slice is the first required consumer.

### Desktop Update Service — STAGE-9 TARGET

D-068 requires a visible Update UI/Service and one maintained installed application identity. Initial distribution may use GitHub Releases plus bounded machine-readable update metadata and verified artifacts.

Release proof includes clean installation and a separate N-1 -> N in-place upgrade scenario with representative project/settings state.

### MCP — KEEP

Optional capability/model/tool source. Discovery and execution are implemented behind explicit bindings and D-017 where required. MCP is not product state.

## 7. Agent Harness — JARVISHUB DONOR, UV-OWNED IMPLEMENTATION

JarvisHub (`LYL1015/JarvisHub`, pinned research commit in `UPSTREAM.md`) is the concrete professional reference for the autonomous layer UV does not yet have.

### Borrow/adapt

- persistent Agent runtime / turn loop;
- Planner + durable Task graph;
- Skills;
- context pipeline and compaction;
- memory for durable agent decisions not already canonical project facts;
- small functional subagent set: explore / plan / media / critic;
- policy/effects inspection;
- trace linking plans/actions/observations/artifacts/evaluations/repair to canonical project entities;
- background work coordinated through Job Manager;
- evaluate -> repair and dependency-aware local regeneration.

### Do not import as product authority

- JarvisHub Canvas as source of truth;
- generic node graph as the UV project model;
- PostgreSQL/Hono application shape as a new UV foundation;
- a parallel Protocol Bridge/tool registry that duplicates Capability Registry + commands;
- Agent memory/trace as a second canonical project state.

### Target Agent data/control flow

```text
Director Agent
 -> Context Builder
 -> Planner / Tasks / Skills
 -> explore / plan / media / critic
 -> Studio/Application Commands + Model/Job/Capability services
 -> ProjectUnitOfWork where canonical mutation is required
 -> Production Semantics / Project Store / Timeline
```

The Agent may observe broadly but mutates canonically only through the same application boundary as the GUI.

## 8. Generation lifecycle and provenance

Target path for generated production material:

```text
Shot
 -> choose named Model
 -> GenerationContract
 -> create idempotent Job / Attempt
 -> Capability/Provider/Adapter execution
 -> generated project-owned asset + provenance
 -> Take candidate
 -> optional evaluation / critic record
 -> explicit AcceptTake
 -> canonical Timeline
```

Job history and semantic acceptance are different histories. Undoing Take acceptance does not delete the generation Job/Attempt/provenance.

## 9. Product Truth verification flow

D-067 adds the cross-layer gate:

```text
Current docs / lifecycle markers
            |
     Product Truth Contract
       /       |        \
 command/API frontend   E2E
       \       |        /
        user-visible outcome
```

Merge-time readiness is truthful only when the declared references exist and the user-visible feature has no unresolved backend/frontend parity gap.

Do not attempt broad natural-language semantic linting. Use explicit contract fields, markers and deterministic repository-reference checks.

## 10. Desktop update flow

D-068 keeps application replacement separate from user project data:

```text
installed version N
 -> Check for updates
 -> verified manifest/artifact for N+1
 -> explicit user update action
 -> out-of-process replacement / rollback-safe handoff
 -> restart N+1
 -> supported migrations
 -> healthy project open
```

Normal stable updates replace the maintained installation rather than create a new side-by-side copy. Historical/dev copies are not destructively merged automatically.

## 11. Legacy/migration inventory

- Recipe Registry — **LEGACY**; old project/import vocabulary only.
- Product Orchestrator / `uv_studio/orchestration/*` — **MOVE + LEGACY**; extract useful readiness/domain logic into modern tool/direction query services.
- `api/project_workflow.py` — **LEGACY + EXTRACT**.
- `/execution-plan` and recipe execution — **LEGACY**.
- Stage 6/8 workspaces and `/projects/{id}` specialized page — **LEGACY UI**.
- donor-era pipeline/session/task/model frontend clients — **DELETE LATER** after caller proof.
- VideoClaw backend path injection — **DELETE LATER** after runtime/test/package proof.
- archived Windows packaging/runtime work — **KEEP AS ENGINEERING REFERENCE**.

## 12. Direction-domain growth

### Micro-drama — first rich proof complete

Story, Characters, Locations and continuity/canon extensions now reuse shared Scene -> Shot -> Take -> accepted Take contracts.

### Commercial

Brief/Product/Brand/Audience/Concept extensions + shared Shot/Take lifecycle.

### Music video

Song/Music Map/Sections/Visual Direction extensions + shared Shot/Take lifecycle + rhythm-aware Timeline assembly.

### Narrated video

Script/Narration/semantic-segment extensions; visual Shots may reuse shared contracts when the journey needs shot-level production.

### Dub battle

Source-scene/dialogue/cast/mix extensions; reuse shared Scene/Take semantics where they are truly the same concept. Ordinary dubbing remains a contextual tool.

## 13. Studio UI target

```text
+--------------------------------------------------------------------+
| Project / Direction                      Agent        Export        |
+--------------------+---------------------------+-------------------+
| Production / Media |                           | Inspector         |
| direction sections |          Preview          | Properties        |
| shared semantic    |                           | AI Tools          |
| entities / Assets  |                           | Model Picker      |
+--------------------+---------------------------+-------------------+
|                         Multitrack Timeline                         |
+--------------------------------------------------------------------+

Settings / About
  -> current version
  -> Check for updates
  -> release notes / progress
  -> Restart and update
```

## 14. Migration order

Completed/current foundation:

1. Production Directions — D-064.
2. Architecture authority cleanup + D-065 shared production semantics.
3. Modern Studio identity/dependency boundary + Project Unit of Work + undo/redo.
4. Rich micro-drama vertical proving shared Scene/Shot/Take semantics and direction extensions — Stage 13 complete.

Next:

5. Backend-owned visible Model Registry.
6. Project Job Manager with idempotency + attempts + durable provenance.
7. Provider-neutral GenerationContract.
8. First named AI generation -> project-owned asset -> Take candidate -> explicit acceptance -> Timeline through normal commands.
9. Product Truth Contract + deterministic parity/reference checks for that user-visible generation path.

Then:

10. Agent Harness foundation from D-066/JarvisHub patterns: context, command/tool catalog, effects/policy, trace.
11. Planner + Tasks + Skills + functional subagents.
12. Critic/evaluation + dependency-aware local repair.
13. Human takeover/edit/resume and then long-form autonomous production.
14. Extend commercial/music/dub-battle direction extensions reusing shared semantics.
15. Move useful legacy targeted-edit/dubbing/music/continuity logic into modern direction/tool surfaces.
16. Retire compatibility code only after caller proof.
17. Reconcile proven Windows packaging onto the accepted product shell and implement D-068 Update Service/UI, signed/verified artifacts and N-1 -> N upgrade proof before maintained desktop release.

## 15. Invariants

- one Project Store authority;
- one canonical Timeline;
- shared production semantic identities where concepts truly overlap;
- no RecipeDefinition as new v2 identity;
- no separate engine/workspace per direction;
- no Agent-only mutation path;
- no JarvisHub Canvas/node graph as UV canonical state;
- visible meaningful model choice;
- remote/non-free work remains explicit/authorized;
- retry-safe long-running/cost-bearing generation;
- provider-neutral semantic Generation Contract above prompt rendering;
- durable Job/Attempt provenance survives acceptance Undo;
- user-visible ready features require Product Truth backend/frontend/evidence agreement;
- current project/architecture docs distinguish as-built from future and agree on machine-checkable facts;
- stable desktop update defaults to one maintained installation identity;
- clean install and N-1 -> N upgrade are separate release proofs;
- local-first desktop baseline;
- reuse mature components behind UV-owned contracts;
- compatibility remains isolated, not silently imported into new boundaries.
