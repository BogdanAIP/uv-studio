# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-064  
**Date:** 2026-08-25

This document is the practical migration map for turning the repository into a coherent local-first AI production studio **without rewriting the proven foundations**.

Classifications:

- **KEEP** — correct long-term foundation;
- **ADAPT** — keep but change scope/boundary;
- **MOVE** — useful logic belongs at another product level;
- **LEGACY** — compatibility only; do not grow new product behavior on it;
- **DELETE LATER** — remove only after dependency/call-site proof and replacement tests.

## 1. Diagnosis

UV Studio has a strong lower technical spine:

```text
Project Store
   |
Studio/Application Commands
   |
MLT / FFmpeg / domain tools / Capability execution
   |
local runtimes / MCP / optional external providers
```

Two opposite product-composition failures have now been observed.

The first was recipe/workspace proliferation:

```text
recipe
 -> recipe-specific orchestration
 -> specialized workspace
 -> recipe-specific state/API
 -> another readiness/action projection
```

D-063 correctly froze that growth and PR #61 established one shared Studio editor spine.

The second was the overcorrection exposed after PR #61:

```text
one generic Studio project
 -> Media Bin
 -> Preview
 -> Timeline
```

That removed the domain value inherited from LocalMiniDrama and related production workflows. A micro-drama, commercial, music video and dub-battle share editor infrastructure, but they do not share the same production organization.

D-064 corrects the composition model without reverting the common Studio Core.

## 2. Target architecture

```text
                              Project
                                 |
                      Production Direction
       +-------------------------+-------------------------+
       |                         |                         |
  micro_drama               commercial                music_video
  narrated_video            dub_battle                free_project
       |                         |                         |
       +------------- direction-owned domain docs --------+
                                 |
                         Shared Studio Core
      +----------------+----------------------+----------------+
      | Production/Nav |   Preview / Canvas   | Inspector      |
      | Media / Assets |                      | AI Tools       |
      | Scenes/Shots*  |                      | Model Picker   |
      +----------------+-----------+----------+----------------+
                                   |
                         Canonical Multitrack Timeline
                                   |
                       Studio / Application Commands
                (same GUI / Agent / scripts / MCP)
                                   |
                         Project Unit of Work
          +------------------------+------------------------+
          |                        |                        |
 direction/domain docs       Project Assets/Refs      Timeline/Generations
          |                        |                        |
          +------------------------+------------------------+
                                   |
                    Tool Services / Project Job Manager
                                   |
                          Model Registry (visible)
                                   |
                          Capability Registry
                                   |
                    Adapter / Transport Registry
                    MLT / FFmpeg / MCP / local / cloud
                                   |
                           actual models/tools
```

`*` Direction-specific entities appear only when that production journey needs them.

The Agent sits above Studio/Application Commands. It has no privileged raw-state mutation path.

## 3. Production Directions — NEW PRODUCT COMPOSITION

Primary paths:

- `uv_studio/production/directions.py`;
- `/api/uv/projects/studio/directions`;
- Studio extension metadata in `project.json`;
- `/projects` direction cards.

Initial first-class directions:

| direction_id | User-facing direction | Core production organization |
| --- | --- | --- |
| `micro_drama` | Микродрама / сюжетное видео | story, characters, locations, scenes, shots, takes, continuity |
| `commercial` | Реклама / продукт | brief, product, brand, audience, concepts, shots, variants |
| `music_video` | Музыкальный клип | song, Music Map, sections, visual direction, shots |
| `narrated_video` | Видео с диктором | brief, script, voice, segments, visual plan, subtitles |
| `dub_battle` | Киноозвучка / Кинобатл | source scene, characters, dialogue, cast, takes, mix |
| `free_project` | Свободный проект | media/assets/timeline with no mandatory production structure |

A Production Direction:

- is **not** a `RecipeDefinition`;
- does not choose a provider or execution engine;
- may define navigation/domain sections, starting inputs, relevant tools and later production policy;
- uses one common Studio shell and canonical project/timeline authority;
- stores richer canonical state in versioned project-owned documents only when required.

New Studio projects keep schema-v1 `recipe_id=studio_v2` only as compatibility metadata. Product identity is `extensions.studio.direction_id`.

## 4. Contextual tools — NOT PROJECT DIRECTIONS

These remain tools/quick actions inside Studio:

- targeted range edit;
- ordinary dubbing/translation;
- photo-to-video/slideshow;
- visualizer;
- action transfer;
- talking character/digital human;
- performance/lip-sync;
- background removal and other transforms;
- image/video/audio generation operations.

They may be surfaced more prominently inside a relevant Production Direction without becoming separate canonical project engines.

## 5. Foundation inventory

### 5.1 Project Store — KEEP

Primary paths:

- `uv_studio/projects/models.py`;
- `uv_studio/projects/store.py`;
- archive/migration/media-integrity modules.

Keep:

- atomic local persistence;
- strict portable JSON;
- traversal/symlink protection;
- project-owned source/artifact references;
- migrations/archive portability.

Adapt:

- `recipe_id` remains schema-v1 compatibility only;
- keep `project.json` small;
- direction/domain state belongs in dedicated versioned project files.

### 5.2 Project references/media ownership — KEEP

`ProjectReference`, source-media registration, artifact registration, SHA/size verification and project-relative path rules remain the base for Media Bin and generated media.

Do not replace them with provider URLs or arbitrary host filesystem paths as canonical state.

### 5.3 D-033 editor foundation — KEEP + EXPAND

- MLT = reusable timeline/edit engine behind UV adapter;
- OpenCut Classic = selective MIT editor/timeline interaction donor;
- UV Project Store/domain state = canonical;
- UV Command API = mutation authority;
- FFmpeg = first deterministic export path.

PR #61's Studio editor spine is retained. It is a common work surface, not the complete product taxonomy.

### 5.4 Studio/Application commands — KEEP + ADAPT

The command model remains the permanent GUI = scripts = AI = MCP boundary.

Current timeline commands are a valid first family. Grow toward:

- more timeline operations as required;
- direction/domain commands;
- transaction grouping / Project Unit of Work;
- product-level undo/redo;
- handler registries/services instead of central dispatch switches.

### 5.5 Project Unit of Work — NEXT FOUNDATION

It must coordinate all canonical state touched by one semantic production operation, including:

- direction/domain documents;
- project references/assets;
- generation/take records;
- timeline changes;
- undo/redo identity.

Representative future operation:

```text
AcceptTake(shot_12_3, take_4)
 -> update take/shot state
 -> register asset
 -> update timeline
 -> commit as one transaction
```

Rollback must leave no split state.

### 5.6 Capability Registry — KEEP, REFRAME

It owns semantic capability, adapter/offer, availability, locality, cost class and D-017 execution authorization.

It remains below the user-visible Model Registry and below Production Directions. A direction/tool may ask for a semantic capability, but it does not hard-code transport/provider execution branches.

### 5.7 Model Registry — NEW TARGET

Backend-owned, user-visible. It should expose named models, modes, supported inputs/outputs, model-specific options, availability/locality/cost facts and underlying offer/adapter identity.

Model choice remains visible when creatively significant.

### 5.8 Job Manager — NEW TARGET

Project-scoped long-running generation with queued/running/succeeded/failed/cancelled, progress, cancellation, retry and exact input/model/output provenance.

Generation output becomes a project-owned asset and is added to timeline/domain state through normal application commands.

### 5.9 MCP — KEEP

MCP is a capability/model/tool source, not the product model. Preserve local profile boundaries, bounded discovery, semantic binding, D-017 authorization and project-owned I/O.

## 6. Legacy/migration inventory

### 6.1 Recipe Registry — COMPATIBILITY LEGACY

Existing recipe definitions remain for old projects/imports and as production-knowledge reference. Do not add new v2 product features by adding a recipe.

Useful knowledge may migrate into:

- Production Direction metadata/domain schemas;
- Studio Tool services;
- production-policy checks;
- Agent-assisted setup.

### 6.2 Product Orchestrator / `uv_studio/orchestration/*` — MOVE + LEGACY

Keep useful readiness/prerequisite/domain eligibility logic, but move it into direction/tool query services. Do not grow recipe-specific workspace/action graphs.

### 6.3 `uv_studio/api/project_workflow.py` — LEGACY + EXTRACT

Keep for compatibility while required. Extract useful semantic operations into application services/handlers. New direction execution must not depend on this as primary authority.

### 6.4 `/execution-plan` and recipe execution — LEGACY

Do not maintain a second modern execution truth. Retire after caller proof or derive compatibility output from modern state where still required.

### 6.5 Stage 6/8 UI — LEGACY

No numbered Stage is normal product navigation. Continuity, photo/video utilities and other useful behavior move to direction/domain state or contextual tools.

### 6.6 Old VideoClaw frontend/API clients — DELETE LATER

Old `/api/pipelines`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/project/*` clients and donor-era taxonomy remain deletion candidates after import/caller proof.

### 6.7 VideoClaw backend path injection — DELETE LATER AFTER PROOF

Remove runtime injection only after supported server/tests/package paths prove independence. Preserve provenance/license material where useful.

### 6.8 Windows host / packaging / update / integrity — KEEP AS REFERENCE

Archived PR #59 / Release #395 remains reusable engineering evidence for Rust/WebView2 host, packaged runtime, installer/uninstaller, integrity, update/rollback and legal gates. Product UI rejection does not invalidate the packaging architecture.

## 7. Direction-domain growth

Do not model every possible production entity globally.

### Micro-drama preferred first rich domain

Expected bounded growth:

```text
Story
Characters
Locations
Scenes
  -> Shots
      -> Takes / generations
      -> accepted take
Continuity state where required
```

### Commercial

```text
Brief
Product references
Brand constraints
Audience / offer
Concepts
Shots / variants
Delivery variants
```

### Music video

Reuse existing Music Map/music analysis/review logic behind the direction:

```text
Song
Music Map
Sections / beats
Visual Direction
Shots
Rhythm-aware assembly
```

### Dub battle

Distinct from ordinary dubbing/translation tool:

```text
Source Scene
Characters
Dialogue Lines
Cast
Recording Sessions
Takes
Final Mix
```

## 8. Studio UI target

```text
+--------------------------------------------------------------------+
| Project / Direction                      Agent        Export       |
+--------------------+---------------------------+-------------------+
| Production / Media |                           | Inspector         |
|                    |          Preview          |                   |
| direction sections |                           | Properties        |
| Media / Assets     |                           | AI Tools          |
| Generations        |                           | Model Picker      |
+--------------------+---------------------------+-------------------+
|                                                                    |
|                         Multitrack Timeline                         |
|                                                                    |
+--------------------------------------------------------------------+
```

Left-side production navigation is composable by direction; Preview, Inspector, Timeline, models/jobs and commands remain common.

## 9. Migration order

1. **Production Directions** — D-064, backend registry, project metadata, cards, Class-C truth.
2. **Project Unit of Work + undo/redo** spanning production docs/assets/timeline.
3. **First rich direction domain** — preferred: micro-drama Scenes/Shots/Characters/Locations/Takes.
4. **Backend-owned Model Registry**.
5. **Project Job Manager**.
6. **First named AI generation** -> project-owned result -> direction state/Media Bin -> Timeline through normal commands.
7. Extend commercial/music/dub-battle direction-specific domain services as real user journeys require them.
8. Move legacy targeted edit/dubbing/music/continuity logic into modern direction/tool surfaces.
9. Retire Product Orchestrator/Stage 8/execution-plan and dead donor clients only after caller evidence.
10. Reconcile and port proven Windows packaging/runtime work onto the accepted product shell.

## 10. Invariants

- one Project Store authority;
- one canonical Timeline;
- no RecipeDefinition as new v2 product identity;
- no separate engine/workspace per Production Direction;
- no Agent-only mutation path;
- visible meaningful model choice;
- remote/non-free execution remains explicit and authorized;
- local-first desktop target remains the maintained baseline;
- reuse mature components behind UV-owned contracts;
- tests must protect user-visible Production Direction discovery while distinguishing directions from contextual tools.
