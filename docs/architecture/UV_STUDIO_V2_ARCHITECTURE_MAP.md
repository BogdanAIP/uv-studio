# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-063  
**Date:** 2026-08-24

This document answers one practical question: **how to turn the current repository into a coherent professional AI video studio without rewriting the proven foundations.**

The classifications are:

- **KEEP** — correct long-term foundation;
- **ADAPT** — keep the concept/implementation but change its scope or boundary;
- **MOVE** — useful logic belongs at a different product level;
- **LEGACY** — compatibility only; no new product growth should depend on it;
- **DELETE LATER** — remove only after dependency/call-site proof and replacement tests.

## 1. Diagnosis

The repository is not one uniformly bad architecture. It has a strong lower half and an overgrown product-composition layer.

Strong spine already present:

```text
Project Store
   |
UV semantic/domain commands
   |
MLT / FFmpeg / domain tools / Capability execution
   |
local runtimes / MCP / external providers
```

The main architectural debt grew beside that spine:

```text
recipe
 -> recipe-specific orchestration
 -> relevant workspace
 -> recipe-specific state/API
 -> specialized panel
 -> another readiness/action projection
```

This produced truthful individual paths but an incoherent application. The migration therefore keeps the spine and replaces the product center.

## 2. Target architecture

```text
                            Studio UI
      +---------------+-------------------+------------------+
      | Media/Scenes  | Preview / Canvas  | Inspector        |
      | Assets        |                   | AI Tools         |
      | Characters    |                   | Model Picker     |
      +---------------+---------+---------+------------------+
                                |
                         Multitrack Timeline
                                |
                    Studio / Application Commands
             (same actions for GUI / Agent / scripts / MCP)
                                |
                         Project Unit of Work
             +------------------+------------------+
             |                  |                  |
        Project Model       Tool Services      Job Manager
   assets/scenes/shots/    edit/dub/music/AI   async work
    tracks/clips/refs       continuity/etc.    cancel/retry
             |                  |                  |
             +-------------+----+-----------+------+
                           |                |
                    Model Registry     Domain state/reviews
                   (user-visible)            |
                           |                 |
                    Capability Registry -----+
                           |
                 Adapter / Transport Registry
              MLT / FFmpeg / MCP / local / cloud
                           |
                     actual models/tools
```

The Agent sits above Studio/Application Commands. It has no privileged raw-state mutation path.

## 3. Inventory

### 3.1 Canonical Project Store — KEEP

Paths:

- `uv_studio/projects/models.py`
- `uv_studio/projects/store.py`
- project archive/migration/media-integrity modules.

Why keep:

- atomic local persistence;
- strict portable JSON;
- traversal/symlink boundaries;
- project-owned source/artifact references;
- migrations and archive portability;
- directories already include `sources`, `assets`, `tasks`, `artifacts`, `timeline`, `reviews`, `exports`.

Required adaptation:

- `ProjectDocument.recipe_id` is mandatory schema-v1 state. Stop using it as v2 product identity. Preserve it for compatibility until a versioned migration can make the field optional/neutral.
- keep root `project.json` intentionally small; put canonical timeline/scenes/jobs into versioned project-owned documents rather than making the root object a giant film schema.

### 3.2 Project media/reference ownership — KEEP

Existing `ProjectReference`, source media stores, artifact registration, SHA/size verification and project path rules are exactly the right foundation for Media Bin assets and generation outputs.

Do not replace them with provider URLs or arbitrary user filesystem paths as canonical state.

### 3.3 D-033 editor foundation — KEEP + EXPAND

Paths:

- `uv_studio/editor/mlt_adapter.py`
- `uv_studio/editor/commands.py`
- `uv_studio/api/editor_commands.py`
- `frontend/components/editor/ProjectEditor.tsx`
- `frontend/components/editor/RangeTimeline.tsx`
- `docs/architecture/EDITOR_FOUNDATION_CONFORMANCE.md`.

Long-term ownership:

- MLT = reusable timeline/edit engine behind UV adapter;
- OpenCut Classic = selective MIT editor/timeline interaction donor;
- UV Project Store/domain model = canonical;
- UV Command API = mutation authority;
- FFmpeg/MLT render ownership changes only with parity evidence.

Current gap:

The live adapter and UI are mostly bounded to one-source targeted range editing. This is implementation incompleteness, not a reason to choose another foundation.

Migration:

- generalize `ProjectEditor` into the Studio shell;
- make `RangeTimeline` evolve into a real multitrack timeline while preserving/adapting OpenCut interaction primitives;
- move targeted range editing into an Inspector/AI Tool rather than keeping the whole editor branded as a targeted-edit mode;
- add generic timeline commands and undo/transaction semantics.

### 3.4 Editor/domain command model — KEEP + ADAPT

Existing commands already cover meaningful target-edit and dubbing mutations. This matches the permanent GUI = scripts = AI = MCP rule.

Adaptation:

- add canonical timeline commands: add/move/trim/split/remove clip, track creation/reorder/mute/visibility as product needs prove them;
- add transaction grouping / Project Unit of Work;
- add undo/redo at the command/domain level;
- replace growing HTTP `isinstance`/`if` dispatch with a command-handler registry once command families expand;
- preserve dedicated coherent domain contracts where they own real invariants. “One command model” does not mean one giant endpoint.

### 3.5 Capability Registry — KEEP, REFRAME

Paths:

- `uv_studio/capabilities/models.py`
- `uv_studio/capabilities/registry.py`
- `uv_studio/capabilities/selection.py`
- `uv_studio/api/capability_execution.py`.

It correctly models:

- semantic capability;
- adapter/offer;
- availability;
- local/remote/hybrid;
- free/potentially-paid/paid;
- selection policy;
- D-017 execution authorization.

Do **not** turn it into the entire creative UI. It is the execution layer underneath a user-visible model/tool layer.

Adaptation:

- replace the central adapter execution `if/elif` with a transport/executor registry later;
- expose exact model-backed offers to the Model Registry;
- keep `local_free_first` for automation where explicitly chosen, but do not use it to hide a professional model choice.

### 3.6 Model Registry — NEW TARGET; old implementation LEGACY

Legacy path:

- `frontend/lib/modelRegistry.ts`
- depends on donor-era `frontend/lib/workflowApi.ts` and old `/api/models` semantics.

Old implementation: **LEGACY / DELETE LATER**.

Needed concept: **KEEP AS A NEW BACKEND-OWNED CONTRACT**.

Model descriptor should minimally include:

```text
model_id
display_name
provider_id
capability/tool families
modes (t2i, image-edit, t2v, i2v, start/end frame, ...)
input/output media kinds
option schema and bounds
availability
locality/cost information
underlying offer/adapter identity
```

Model-specific creative parameters belong in the model/tool contract, not in a universal `prompt: string` fiction.

The Studio displays the named model. Settings configure providers/runtimes. Capability Registry executes the selected model through its offer/adapter.

### 3.7 MCP — KEEP

MCP remains one source of capabilities/models/tools, not the product model.

Keep:

- machine-local profile boundary;
- secret references outside portable projects;
- bounded discovery;
- explicit semantic binding;
- locality/cost facts;
- D-017 authorization;
- project-owned file/output handling.

A future Model Registry can project eligible MCP bindings as named models when the binding provides the required model/tool metadata.

### 3.8 `uv_studio/orchestration/*` — MOVE + LEGACY

Current directory contains large recipe-specific projections for targeted edit, dubbing, music, narrated, general, story, commercial and a central project-workflow router/projection.

Useful content:

- readiness facts;
- exact prerequisites;
- domain-specific next-step knowledge;
- safe links to existing execution capabilities.

Long-term problem:

The product grows by adding a new per-recipe projection/workspace/action graph. That makes implementation modes define the application.

Classification:

- recipe-specific Product Orchestrator as product center: **LEGACY**;
- useful domain readiness and tool eligibility logic: **MOVE** into Studio Tool query/services;
- compatibility projections for old projects: **KEEP TEMPORARILY**;
- no new recipe-specific orchestrator modules for v2 product features.

### 3.9 `uv_studio/api/project_workflow.py` — LEGACY + EXTRACT

The route currently owns a very large request union, recipe/action validation switch and execution dispatch coordination.

Migration:

- old recipe projects may continue to use it during compatibility period;
- extract reusable domain/tool actions into application services/command handlers;
- v2 Studio must not call it as its primary authority;
- delete/retire only after supported callers and tests move.

### 3.10 `/execution-plan` and `uv_studio/recipes/execution.py` — LEGACY

This is a second independently maintained execution truth. It already conflicts conceptually with Product Orchestrator and will conflict even more with Studio v2.

Action:

- inventory all real consumers;
- derive a compatibility response from modern state if required;
- otherwise retire endpoint + implementation + obsolete tests together.

### 3.11 Recipe Registry and Stage 8 workspaces — COMPATIBILITY LEGACY

Recipes were useful for proving heterogeneous workflows without creating a new engine each time. They should no longer define new-project identity.

Classification:

- recipe definitions for old projects/import: **KEEP TEMPORARILY**;
- new feature delivery via new recipe: **FROZEN**;
- Stage 8 workspace as v2 state: **LEGACY**;
- useful source-order/brief validation: **MOVE/ADAPT** into Timeline/Tool services;
- `recipe_id` as user-facing mode: **RETIRE**.

### 3.12 Intent-first `CreativeProjectService` — ADAPT + REPLACE PLAN

Path:

- `uv_studio/application/creative_projects.py`.

Useful proof:

- one project can start from a goal without recipe cards;
- application layer can coordinate multiple lower-level projections in one Project Store update;
- `ProjectDocument.extensions` can carry versioned UV-owned product metadata without breaking archives.

Wrong long-term direction:

- hardcodes internal `general_video` recipe;
- builds its central plan from `project_workflow_state`;
- persists Stage 8 assembly projection;
- treats a linear production-plan wizard as the Studio.

Classification:

- application layer: **KEEP**;
- project brief/goal metadata: **KEEP/ADAPT**;
- `CreativeProjectService.plan()` as main UI authority: **LEGACY/REPLACE**;
- Stage 8/general-video bridge: **TEMPORARY COMPATIBILITY**.

### 3.13 Current `/studio` and `CreativeProjectWorkspace` — ROUTE KEEP, UI REPLACE

Paths:

- `frontend/app/projects/[projectId]/studio/page.tsx`
- `frontend/components/creative/CreativeProjectWorkspace.tsx`.

Keep:

- stable `/studio` concept;
- project loading/error/archive basics;
- one-project entry instead of recipe catalog.

Replace:

- wizard-like phase cards as the primary application;
- direct dependency on both `CreativePlan` and `ProjectWorkflowState`;
- `GeneralVideoPanel` as a product-level special case.

The replacement should compose the generalized D-033 editor shell.

### 3.14 Existing `ProjectEditor` — MOVE TO CENTER

The current `ProjectEditor` is closer to the desired product than the newer wizard:

- left Media Bin;
- central preview;
- timeline/playhead/selection;
- right AI/task inspector;
- project-owned media import;
- existing shared command boundary.

Action:

- remove Stage 4C/targeted-edit branding from the shell;
- make the shell generic;
- keep targeted edit as one contextual tool;
- add scene/shot navigation only after a real story/short-drama vertical requires it.

### 3.15 Targeted edit — MOVE TO TOOL

Keep all proven range identity, continuity brief, replacement plan/candidate/review/accept and non-destructive edit logic.

Move UX from “project mode” to:

```text
select clip/range -> AI Edit -> prepare/review/accept -> timeline update
```

### 3.16 Dubbing / translation — MOVE TO TOOL

Keep ASR, translation, PreparedSpeech, alignment, loudness/review/accept/subtitle/render logic and local/remote capability boundaries.

Move UX to selected clip/audio:

```text
Dubbing -> language -> voice/model -> transcript/review -> accepted audio/subtitles
```

### 3.17 Continuity — MOVE TO SCENE/SHOT TOOL

Keep optional linked-shot continuity state and evidence/review concepts.

Do not expose “Stage 6”. Use it only where selected shots/scenes/characters require consistency.

### 3.18 Music Map / Music Video domain — MOVE TO AUDIO/TIMELINE TOOL

Keep music analysis, exact-song identity, timing markers, direction/review and master-audio guarantees.

Move to:

```text
select audio -> Analyze Music -> beat/section markers -> timeline sync/edit tools
```

A “music video” may later be a template/agent setup, not another project engine.

### 3.19 Photo-to-video / Visualizer — MOVE TO SMALL TOOLS

- images selected -> arrange/add to timeline/slideshow;
- audio selected -> visualizer tool.

Keep deterministic FFmpeg capabilities and exact provenance. Retire product-mode status after v2 equivalents are proven.

### 3.20 Narrated / Story / Commercial — TEMPLATES + TOOLS, NOT ENGINES

The production knowledge remains useful:

- narrated: script/voice-led planning;
- story: scenes/shots/continuity;
- commercial: product references, direction, review/sample-first policy.

Express these as:

- optional starting templates;
- Agent-assisted project setup;
- production-policy checks;
- contextual tools.

Do not create another canonical project/workspace type.

### 3.21 Old VideoClaw frontend/API client — DELETE LATER

Examples:

- `frontend/lib/workflowApi.ts`
- old `frontend/lib/modelRegistry.ts`
- HomePage / WorkflowPanel / pipeline / stage / sandbox donor-era surfaces.

These still refer to old `/api/pipelines`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/project/*` families and donor-era model taxonomy.

Action:

- prove actual imports/callers;
- remove dead surfaces rather than translate/modernize them;
- retain only useful adapted UI primitives with provenance/attribution.

### 3.22 VideoClaw runtime injection — DELETE LATER AFTER PROOF

The UV server still prepends the vendored VideoClaw backend directory to `sys.path` even though supported routes are UV-owned.

Action:

- prove supported server/tests/package run without this injection;
- remove if no supported import requires it;
- keep pinned vendor/provenance/license material only where still useful.

### 3.23 Windows host / packaging / update / integrity — KEEP

The Release #395-era evidence proved a strong Windows delivery stack even though that product UI was rejected.

Keep the engineering:

- Rust/WebView2 native host;
- packaged backend/frontend/runtime;
- immutable payload/integrity checks;
- installer/uninstaller;
- safe user-data preservation;
- update/rollback;
- legal/provenance gates.

Do not rebuild packaging architecture merely because the Studio UI changes.

## 4. Minimal v2 Project Model

Do not attempt to model a full film studio before the first vertical works.

### Root project

Keep `project.json` as identity, timestamps, settings, portable references, extensions and compatibility metadata.

### Assets

Continue using registered project-owned source/artifact references. Add richer typed asset metadata only where Studio needs it.

### Timeline

Introduce one canonical, versioned timeline document, for example under `timeline/main.json`:

```text
Timeline
  timeline_id
  timebase / frame-rate policy
  tracks[]

Track
  track_id
  kind: video | audio | subtitle
  clips[]

Clip
  clip_id
  asset/reference id
  source in/out
  timeline start/duration
  enabled/muted state
  bounded transform metadata where needed
```

Exact schema is an implementation decision for the first v2 slice; the ownership rule is already fixed: UV canonical, MLT derived.

### Scenes / shots

Add only the minimum required for story/micro-drama workflows. A first version may be a lightweight versioned project document referencing assets and timeline clips.

### Generation record

Every AI generation should retain:

- generation/job id;
- tool/model id;
- provider/offer provenance where safe;
- input project/reference identities;
- normalized prompt/settings used;
- output reference IDs;
- status/timestamps/cost facts available from the provider;
- no raw secret values.

## 5. Studio UI target

```text
+--------------------------------------------------------------------+
| Project / scene                         Agent        Export         |
+----------------+--------------------------------+------------------+
| Media / Scenes |                                | Inspector        |
|                |            Preview             |                  |
| Assets         |                                | Properties       |
| Generations    |                                | Image AI         |
| Characters*    |                                | Video AI         |
| Audio          |                                | Audio AI         |
|                |                                | Edit/Dub/etc.    |
+----------------+--------------------------------+------------------+
|                                                                    |
|                         Multitrack Timeline                         |
|                                                                    |
+--------------------------------------------------------------------+
```

`Characters`/`Locations` are conditional domains, not mandatory clutter for every project.

## 6. Model/tool UI boundary

Example Image AI tool:

```text
Model: [named model v]
Mode: text-to-image / edit / reference
Prompt
References
Aspect ratio
Quality / seed / model-specific options
Estimated/known cost information
Generate
```

Example Video AI tool:

```text
Model: [named model v]
Mode: text-to-video / image-to-video / start-end / edit
Prompt
Start frame / end frame / references
Duration
Camera/motion/model-specific options
Cost/authorization state
Generate
```

A model is visible. Internally it maps to a capability offer/adapter. Provider-specific details do not leak into unrelated Studio code.

## 7. Job Manager requirement

Before normal image/video generation, add a project-scoped Job Manager.

Minimum state:

```text
queued
running
succeeded
failed
cancelled
```

Minimum behavior:

- durable identity;
- progress/message when available;
- cancel;
- safe retry semantics;
- exact model/input/output provenance;
- result registration into Project Store;
- no arbitrary background thread as a new canonical state store.

## 8. Ordered migration plan

### V2-A — architecture freeze and map

- accept D-063;
- mark recipe/stage product expansion frozen;
- synchronize lifecycle/backlog/roadmap/PR.

### V2-B — Studio/editor spine

Prove:

```text
project -> Media Bin -> import media -> AddClip command
 -> canonical timeline -> reload -> preview -> MLT projection -> export
```

No Recipe selection, Stage 8 workspace or Product Orchestrator is involved in the v2 path.

### V2-C — application/transaction boundary

- Project Unit of Work;
- timeline command handlers;
- undo/redo transaction identity;
- command-handler registry.

### V2-D — user-visible Model Registry

- backend contract;
- model/provider metadata;
- supported modes/options;
- explicit model picker;
- mapping to Capability Registry/Offer.

### V2-E — Job Manager

- durable project-scoped job lifecycle;
- cancellation/retry/progress;
- provenance.

### V2-F — first Image AI vertical

```text
Inspector -> choose named model -> prompt/reference/options
 -> D-017 if required -> job -> generated project asset
 -> Media Bin -> AddClip command -> timeline
```

### V2-G — first Video AI vertical

Same lifecycle with model-supported video modes and asynchronous execution.

### V2-H — migrate proven specialized tools

Recommended order:

1. targeted edit;
2. dubbing/translation;
3. music analysis/sync;
4. continuity/consistency;
5. photo/slideshow and visualizer;
6. story/narrated/commercial templates/agent flows.

### V2-I — retire parallel truths

After caller migration:

- `/execution-plan`;
- recipe Product Orchestrator as modern authority;
- Stage 8 workspaces;
- mandatory recipe identity;
- donor-era frontend/API clients.

### V2-J — VideoClaw/runtime reduction and release

- remove unnecessary vendor backend runtime dependency;
- preserve provenance/licensing;
- rerun Windows packaged/integrity/update/rollback evidence on the accepted Studio product.

## 9. First v2 acceptance gate

The first Studio spine is accepted only when all of these are true:

1. A user creates/opens a normal project without choosing a recipe.
2. The Studio shows Media Bin, Preview, Inspector and Timeline.
3. An image/video can be imported into Project Store.
4. The user can add, move, trim and remove at least the bounded clips required by the slice through UV commands.
5. The same mutation contracts are callable programmatically.
6. Timeline state survives close/reopen.
7. MLT projection is derived from canonical UV timeline state.
8. Deterministic render/export produces a registered result.
9. No Stage 6/8 or Product Orchestrator terminology appears in the v2 path.
10. Existing schema-v1/recipe projects remain readable through compatibility paths.

## 10. What is explicitly not part of the first migration

- a complete DaVinci-class NLE;
- every AI provider;
- a full micro-drama character/location database;
- a node-graph UI;
- automatic “best model” selection as the only mode;
- wholesale deletion of old recipe/domain code;
- a new render engine replacing MLT/FFmpeg without evidence.

The architecture succeeds if each migrated function makes the old product-specific path smaller while the single Studio becomes more capable.
