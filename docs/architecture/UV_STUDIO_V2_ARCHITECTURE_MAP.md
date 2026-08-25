# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-064 + D-065  
**Date:** 2026-08-25

This is the practical migration map for a coherent local-first AI production studio without rewriting proven foundations.

Classifications: **KEEP**, **ADAPT**, **MOVE**, **LEGACY**, **DELETE LATER**.

## 1. Diagnosis

The repository has a strong lower spine:

```text
Project Store
 -> Studio/Application Commands
 -> MLT / FFmpeg / domain tools / Capability execution
 -> local runtimes / MCP / optional external providers
```

Two product-composition errors were corrected:

1. recipe/workspace proliferation — separate recipe orchestration/workspaces pretending to be products;
2. generic-editor overcorrection — one Media/Preview/Timeline shell with insufficient production semantics.

D-064 restores meaningful Production Directions. D-065 prevents the correction from creating six parallel domain models by sharing genuinely common Scene/Shot/Take semantics.

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
            Sequence/Scene | Shot | Take/Accepted Take
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
                  Tool Services / Project Job Manager
                                 |
                       Model Registry (visible)
                                 |
                       Capability Registry
                                 |
                  Adapter / Transport Registry
                 MLT / FFmpeg / MCP / local / cloud
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

## 4. Shared Production Semantic Core — NEW TARGET (D-065)

Common concepts that appear across directions must have one UV-owned contract. First bounded primitives:

- optional Sequence/Scene grouping;
- Shot independent from Timeline Clip;
- Take/candidate + accepted-take identity;
- project asset/generation bindings;
- optional continuity/canon relationships;
- accepted-production-material -> canonical Timeline binding/projection.

Direction extensions reference these identities instead of defining private duplicate Shot/Take systems.

Preferred first proof is micro-drama, but the contracts are shared infrastructure.

## 5. Contextual tools — NOT DIRECTIONS

Targeted edit, ordinary dubbing/translation, slideshow/photo-to-video, visualizer, action transfer, talking character, lip-sync, background transforms and image/video/audio generation are contextual tools. They may be prominent in a direction without becoming its product engine.

## 6. Foundation inventory

### Project Store — KEEP + ADAPT

Keep atomic file persistence, strict portable JSON, path/symlink protection, project-owned refs and archive integrity.

Required adaptation before rich domain work:

- typed Studio/Production Direction identity;
- explicit legacy compatibility mode rather than fake modern direction;
- no implicit `general_video` default in core creation;
- deliberate bounded production/domain storage root or equivalent;
- Project Unit of Work for multi-document transactions.

### Project references/media — KEEP

Remain the base for Media Bin, generated assets and production bindings. Provider URLs/host paths never become canonical identity.

### D-033 editor foundation — KEEP + EXPAND

MLT stays behind UV adapter; OpenCut is a selective UI/interaction donor; UV owns canonical Timeline/commands; FFmpeg remains deterministic export substrate where used.

### Studio/Application commands — KEEP + ADAPT

Current timeline commands are a valid first family. Grow shared handler registries, direction/domain commands, transaction identity and undo/redo. No Agent-only mutation path.

### Project Unit of Work — NEXT FOUNDATION

Must coordinate Studio identity/project metadata, shared production semantics, direction extensions, refs/assets, generation/take records, Timeline and undo history.

```text
AcceptTake(shot_12_3, take_4)
 -> accepted Take
 -> Shot state
 -> asset/reference
 -> Timeline binding/update
 -> one transaction / reversible undo
```

### Capability Registry — KEEP, REFRAME

Execution semantics/availability/locality/cost/authorization only. Below visible Model Registry and below production composition.

### Model Registry — NEW TARGET

Backend-owned and user-visible for meaningful model selection; maps named models/modes onto capabilities/offers/adapters.

### Job Manager — NEW TARGET

Project-scoped queued/running/succeeded/failed/cancelled generation lifecycle, cancellation/retry and exact provenance.

### MCP — KEEP

Optional capability/model/tool source. Discovery and execution are implemented behind explicit bindings and D-017 where required. MCP is not product state.

## 7. Modern/legacy boundary findings from 2026-08-25 audit

These are mandatory preconditions for `studio-v2-application-transactions`:

1. `studio_timeline.py` and `project_media.py` import neutral `ProjectPayload`/`ProjectReferencePayload`/`get_project_store` from recipe-aware `api/projects.py`; extract a recipe-free project API/core dependency boundary.
2. Generic project POST and `ProjectStore.create_project()` retain recipe-era creation semantics/defaults; modern application code must not inherit them accidentally.
3. Studio identity is currently arbitrary `extensions.studio` JSON; generic PATCH/import can corrupt it and Studio endpoints do not have one typed identity gate.
4. The initial extension uses `schema_version: 2`; define an actual Studio-metadata schema version rather than treating “Studio v2” as schema semantics.
5. Legacy projects can open the mechanical Studio editor without modern direction identity. Keep that only as explicit compatibility; direction-specific semantic commands require valid modern identity or migration.
6. Generic frontend `projectsApi.ts` still mixes neutral project access with recipe creation/execution-plan types; split modern/core vs legacy clients before new callers grow.
7. `studio_timeline.py` already owns direction catalog/project creation in addition to Timeline routes; split application responsibilities as the command/UoW layer grows rather than allowing a timeline API module to become the Studio god-module.

None requires a rewrite; they are strangler-boundary debt.

## 8. Legacy/migration inventory

- Recipe Registry — **LEGACY**; old project/import vocabulary only.
- Product Orchestrator / `uv_studio/orchestration/*` — **MOVE + LEGACY**; extract useful readiness/domain logic into modern tool/direction query services.
- `api/project_workflow.py` — **LEGACY + EXTRACT**.
- `/execution-plan` and recipe execution — **LEGACY**.
- Stage 6/8 workspaces and `/projects/{id}` specialized page — **LEGACY UI**.
- donor-era pipeline/session/task/model frontend clients — **DELETE LATER** after caller proof.
- VideoClaw backend path injection — **DELETE LATER** after runtime/test/package proof.
- archived Windows packaging/runtime work — **KEEP AS ENGINEERING REFERENCE**.

## 9. Direction-domain growth

### Micro-drama — first rich proof

Direction extensions: Story, Characters, Locations, dramaturgy. Reuse shared Scene -> Shot -> Take -> accepted Take contracts and optional continuity.

### Commercial

Brief/Product/Brand/Audience/Concept extensions + shared Shot/Take lifecycle.

### Music video

Song/Music Map/Sections/Visual Direction extensions + shared Shot/Take lifecycle + rhythm-aware Timeline assembly.

### Narrated video

Script/Narration/semantic-segment extensions; visual Shots may reuse shared contracts when the journey needs shot-level production.

### Dub battle

Source-scene/dialogue/cast/mix extensions; reuse shared Scene/Take semantics where they are truly the same concept. Ordinary dubbing remains a contextual tool.

## 10. Studio UI target

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
```

## 11. Migration order

1. Production Directions — D-064 (done at first metadata/UI spine).
2. Architecture authority cleanup + D-065 shared production semantics (current PR #64).
3. Modern Studio identity/dependency boundary + Project Unit of Work + undo/redo.
4. First rich micro-drama vertical proving **shared** Scene/Shot/Take semantics plus its direction extensions.
5. Backend-owned visible Model Registry.
6. Project Job Manager.
7. First named AI generation -> candidate Take/asset -> explicit acceptance -> Timeline through normal commands.
8. Extend commercial/music/dub-battle direction extensions reusing shared semantics.
9. Move useful legacy targeted-edit/dubbing/music/continuity logic into modern direction/tool surfaces.
10. Retire compatibility code only after caller proof and reconcile proven Windows packaging onto accepted product shell.

## 12. Invariants

- one Project Store authority;
- one canonical Timeline;
- shared production semantic identities where concepts truly overlap;
- no RecipeDefinition as new v2 identity;
- no separate engine/workspace per direction;
- no Agent-only mutation path;
- visible meaningful model choice;
- remote/non-free work remains explicit/authorized;
- local-first desktop baseline;
- reuse mature components behind UV-owned contracts;
- compatibility remains isolated, not silently imported into new boundaries.
