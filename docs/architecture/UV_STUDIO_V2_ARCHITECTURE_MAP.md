# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-063  
**Date:** 2026-08-24

This document is the practical migration map for turning the current repository into a coherent professional AI video studio **without rewriting the proven foundations**.

Classifications:

- **KEEP** — correct long-term foundation;
- **ADAPT** — keep but change scope/boundary;
- **MOVE** — useful logic belongs at another product level;
- **LEGACY** — compatibility only; do not grow new product behavior on it;
- **DELETE LATER** — remove only after dependency/call-site proof and replacement tests.

## 1. Diagnosis

UV Studio is not one uniformly bad architecture. The lower half is strong; the product-composition layer is overgrown.

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

The architectural swamp grew beside that spine:

```text
recipe
 -> recipe-specific orchestration
 -> relevant workspace
 -> recipe-specific state/API
 -> specialized panel
 -> another readiness/action projection
```

That structure made individual flows more truthful, but not one coherent application. Studio v2 keeps the spine and replaces the product center.

## 2. Target architecture

```text
                            Studio UI
      +---------------+-------------------+------------------+
      | Media/Scenes  | Preview / Canvas  | Inspector        |
      | Assets        |                   | AI Tools         |
      | Characters*   |                   | Model Picker     |
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

`Characters`, locations and other production entities appear only when the project needs them; they are not mandatory clutter.

The Agent sits above Studio/Application Commands. It has no privileged raw-state mutation path.

## 3. Inventory

### 3.1 Project Store — KEEP

Primary paths:

- `uv_studio/projects/models.py`
- `uv_studio/projects/store.py`
- archive/migration/media-integrity modules.

Why keep:

- atomic local persistence;
- strict portable JSON;
- traversal/symlink protection;
- project-owned source/artifact references;
- migrations and archive portability;
- existing project roots already include `sources`, `assets`, `tasks`, `artifacts`, `timeline`, `reviews`, `exports`.

Adaptation:

- `ProjectDocument.recipe_id` is mandatory schema-v1 state. Stop using it as v2 product identity. Preserve it only for compatibility until a versioned migration can make it optional or neutral.
- keep `project.json` intentionally small; canonical timeline/scenes/jobs live in versioned project-owned documents rather than one giant root schema.

### 3.2 Project references/media ownership — KEEP

`ProjectReference`, source-media registration, artifact registration, SHA/size verification and project-relative path rules are the correct base for Media Bin assets and generated media.

Do not replace them with provider URLs or arbitrary user filesystem paths as canonical project state.

### 3.3 D-033 editor foundation — KEEP + EXPAND

Primary paths:

- `uv_studio/editor/mlt_adapter.py`
- `uv_studio/editor/commands.py`
- `uv_studio/api/editor_commands.py`
- `frontend/components/editor/ProjectEditor.tsx`
- `frontend/components/editor/RangeTimeline.tsx`
- `docs/architecture/EDITOR_FOUNDATION_CONFORMANCE.md`.

Long-term ownership:

- MLT = reusable timeline/edit engine behind UV adapter;
- OpenCut Classic = selective MIT editor/timeline interaction donor;
- UV Project Store/domain state = canonical;
- UV Command API = mutation authority;
- FFmpeg/MLT export ownership changes only with parity evidence.

Current limitation: the live editor/MLT path is mostly bounded to one-source targeted range editing. This is **incomplete implementation**, not evidence that the foundation is wrong.

Migration:

- generalize `ProjectEditor` into the Studio shell;
- evolve `RangeTimeline` into a multitrack timeline while reusing proven OpenCut interaction primitives;
- move targeted editing into an Inspector/AI Tool;
- add generic timeline commands and undo/transaction semantics;
- do not create another timeline engine.

### 3.4 Editor/domain commands — KEEP + ADAPT

The command concept already matches the permanent GUI = scripts = AI = MCP rule.

Add:

- `add_clip`;
- `move_clip`;
- `trim_clip`;
- `split_clip`;
- `remove_clip`;
- bounded track operations as needed;
- transaction grouping / Project Unit of Work;
- product-level undo/redo.

As command families grow, replace central HTTP `isinstance`/`if` dispatch with handler registries/services. Dedicated coherent domain APIs may remain where they own real invariants; “one command model” does not mean one giant endpoint.

### 3.5 Capability Registry — KEEP, REFRAME

Primary paths:

- `uv_studio/capabilities/models.py`
- `uv_studio/capabilities/registry.py`
- `uv_studio/capabilities/selection.py`
- `uv_studio/api/capability_execution.py`.

It correctly owns:

- semantic capability;
- adapter/offer;
- availability;
- locality;
- cost class;
- selection policy;
- D-017 execution authorization.

It must **not** become the entire creative UI. Capability Registry is execution infrastructure below a user-visible Model Registry.

Later adaptation:

- replace adapter execution `if/elif` with an executor/transport registry;
- project exact model-backed offers into the Model Registry;
- retain `local_free_first` for explicit automation policies, not to hide creative model choice.

### 3.6 Model Registry — NEW TARGET; old implementation LEGACY

Legacy frontend paths:

- `frontend/lib/modelRegistry.ts`
- `frontend/lib/workflowApi.ts`.

The old implementation depends on donor-era `/api/models` contracts and hard-coded provider/model classes. It is **LEGACY / DELETE LATER**.

The new backend-owned Model Registry should expose at least:

```text
model_id
display_name
provider_id
tool/capability families
modes: t2i, image-edit, t2v, i2v, start/end frame, ...
input/output media kinds
model-specific option schema and bounds
availability
locality / cost information
underlying offer/adapter identity
```

The user sees and chooses the named model in the relevant tool. Settings configure providers/runtimes/accounts. Capability Registry executes the chosen model through its offer/adapter.

### 3.7 MCP — KEEP

MCP remains a capability/model/tool source, not the product model.

Keep:

- machine-local profile boundary;
- secrets outside portable projects;
- bounded discovery;
- explicit semantic binding;
- locality/cost facts;
- D-017 authorization;
- project-owned input/output handling.

A future Model Registry may expose eligible MCP bindings as named models when they provide sufficient model/tool metadata.

### 3.8 `uv_studio/orchestration/*` — MOVE + LEGACY

Current modules include large recipe-specific projections for targeted edit, dubbing, music, narrated, general, story, commercial and the central project workflow.

Useful content to preserve:

- readiness facts;
- exact prerequisites;
- domain-specific eligibility;
- safe links to real capability/domain execution.

Long-term problem: the product grows by adding another per-recipe projection/workspace/action graph.

Classification:

- recipe-specific Product Orchestrator as product center: **LEGACY**;
- useful domain readiness/eligibility logic: **MOVE** into Studio Tool query/services;
- compatibility projection for old projects: **KEEP TEMPORARILY**;
- no new recipe-specific orchestrator modules for v2 features.

### 3.9 `uv_studio/api/project_workflow.py` — LEGACY + EXTRACT

The API owns a large request union, recipe/action validation switch and execution coordination.

Migration:

- keep for old recipe-project compatibility while required;
- extract reusable tool/domain actions into application services/command handlers;
- v2 Studio must not use it as primary authority;
- retire only after callers/tests move.

### 3.10 `/execution-plan` + `uv_studio/recipes/execution.py` — LEGACY

This is a separate maintained execution truth and already duplicates Product Orchestrator concepts.

Action:

- inventory real consumers;
- derive compatibility response from modern state if still required;
- otherwise retire endpoint, implementation and obsolete tests together.

### 3.11 Recipe Registry + Stage 8 workspaces — COMPATIBILITY LEGACY

Recipes were useful for proving heterogeneous workflows without new engines, but they should no longer define project identity.

Classification:

- existing recipe definitions for old projects/imports: **KEEP TEMPORARILY**;
- new feature delivery by adding a recipe: **FROZEN**;
- Stage 8 workspace as v2 state: **LEGACY**;
- useful brief/source-order validation: **MOVE/ADAPT** into Timeline/Tool services;
- `recipe_id` as user-facing mode: **RETIRE**.

### 3.12 Intent-first `CreativeProjectService` experiment — REFERENCE ONLY

The archived PR #59 added `uv_studio/application/creative_projects.py` and a wizard-like `/studio`. That code is **not on main** and will not be merged through #59.

Useful lesson:

- one project can start without recipe cards;
- an application layer can coordinate multiple lower states in one Project Store write;
- namespaced project extensions can carry versioned product metadata.

Rejected direction:

- hard-coded internal `general_video` recipe;
- central plan built from `project_workflow_state`;
- Stage 8 assembly projection;
- linear production-plan wizard as the main Studio.

Do not port this code wholesale. Reuse only the proven concepts that fit D-063.

### 3.13 Current `ProjectEditor` — MOVE TO PRODUCT CENTER

`frontend/components/editor/ProjectEditor.tsx` is already closer to the target Studio than the later wizard experiment:

- left Media Bin;
- central preview;
- timeline/playhead/selection;
- right AI/task inspector;
- project-owned media import;
- shared command boundary.

Action:

- remove Stage 4C/targeted-edit branding from the shell;
- make shell generic;
- keep targeted edit as one contextual tool;
- add scenes/shots only after an actual story/micro-drama vertical requires them.

### 3.14 Targeted edit — MOVE TO TOOL

Keep range identity, Continuity Brief, Replacement Plan/Candidate/Review/Accept and non-destructive edit logic.

Target UX:

```text
select clip/range -> AI Edit -> prepare/review/accept -> timeline update
```

### 3.15 Dubbing / translation — MOVE TO TOOL

Keep ASR, translation, prepared speech, alignment, loudness/review/accept/subtitle/render logic and local/remote capability boundaries.

Target UX:

```text
select clip/audio -> Dubbing -> language -> voice/model -> review -> accepted audio/subtitles
```

### 3.16 Continuity — MOVE TO SCENE/SHOT TOOL

Keep optional linked-shot state and evidence/review concepts. Do not expose “Stage 6”. Use continuity only when selected shots/scenes/characters need consistency.

### 3.17 Music Map / Music domain — MOVE TO AUDIO/TIMELINE TOOL

Keep music analysis, exact-song identity, timing markers, direction/review and master-audio guarantees.

Target UX:

```text
select audio -> Analyze Music -> beat/section markers -> timeline sync/edit tools
```

“Music video” may be a template/agent setup, not another project engine.

### 3.18 Photo-to-video / Visualizer — MOVE TO SMALL TOOLS

- selected images -> arrange/add to timeline/slideshow;
- selected audio -> visualizer.

Keep deterministic FFmpeg capabilities and provenance. Retire their product-mode status after v2 equivalents are proven.

### 3.19 Narrated / Story / Commercial — TEMPLATES + TOOLS

Useful production knowledge remains:

- narrated: script/voice-led planning;
- story: scenes/shots/continuity;
- commercial: exact product references, direction, sample/review policy.

Express these as optional starting templates, Agent-assisted setup, production-policy checks and contextual tools. Do not create another canonical project engine.

### 3.20 Old VideoClaw frontend/API client — DELETE LATER

Examples:

- `frontend/lib/workflowApi.ts`;
- old `frontend/lib/modelRegistry.ts`;
- HomePage / WorkflowPanel / pipeline / stage / sandbox donor-era surfaces.

They refer to old `/api/pipelines`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/project/*` families and donor-era model taxonomy.

Action: prove imports/callers, then remove dead surfaces rather than translating or modernizing them. Retain only useful adapted UI primitives with proper provenance.

### 3.21 VideoClaw backend `sys.path` injection — DELETE LATER AFTER PROOF

The UV server still prepends the vendored VideoClaw backend directory even though supported routes are UV-owned.

Action:

- prove supported server/tests/package run without it;
- remove if no supported import requires it;
- keep pinned vendor/provenance/license material where useful.

### 3.22 Windows host / packaging / update / integrity — KEEP AS REFERENCE

Archived PR #59 / Release #395 proved a strong Windows delivery stack even though its product UI was rejected.

Preserve and later selectively port:

- Rust/WebView2 host;
- packaged backend/frontend/runtime;
- immutable payload/integrity checks;
- installer/uninstaller;
- user-data preservation;
- update/rollback;
- legal/provenance gates.

Do not rebuild packaging architecture merely because Studio UI changes.

## 4. Minimal v2 Project Model

Do not model the entire film industry before the first vertical works.

### Root project

Keep `project.json` as identity, timestamps, settings, portable references, extensions and compatibility metadata.

### Assets

Continue registered project-owned sources/artifacts. Enrich metadata only when Studio needs it.

### Canonical timeline

Introduce one versioned UV timeline document under the existing `timeline/` project root, conceptually:

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

Exact schema is implementation work for the first v2 slice. Ownership is already fixed: **UV canonical, MLT derived**.

### Scenes / shots

Add only the minimum required for story/micro-drama workflows. A first version may be a lightweight versioned document referencing assets and timeline clips.

### Generation record

Every AI generation should retain:

- job/generation id;
- selected tool/model id;
- provider/offer provenance where safe;
- project input/reference identities;
- normalized prompt/settings;
- output reference IDs;
- timestamps/status/cost facts when available;
- never raw secrets.

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

## 6. Model/tool boundary

Image AI example:

```text
Model: [named model v]
Mode: text-to-image / edit / reference
Prompt
References
Aspect ratio
Quality / seed / model-specific options
Known/estimated cost information
Generate
```

Video AI example:

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

The model is visible. Internally it maps to capability offer/adapter execution. Provider-specific code does not branch across unrelated Studio components.

## 7. Job Manager requirement

Before normal image/video generation, add a project-scoped Job Manager.

Minimum lifecycle:

```text
queued -> running -> succeeded | failed | cancelled
```

Minimum behavior:

- durable identity;
- progress/message when available;
- cancellation;
- safe retry semantics;
- exact model/input/output provenance;
- Project Store result registration;
- no ad-hoc background process as a competing state authority.

## 8. Ordered migration

### V2-A — architecture freeze/map

- accept D-063;
- archive mixed PR #59 without merge;
- freeze recipe/stage product expansion;
- synchronize context/roadmap/backlog.

### V2-B — Studio/editor spine

Prove:

```text
project -> Media Bin -> import media -> AddClip command
 -> canonical timeline -> reload -> preview -> MLT projection -> deterministic export
```

No recipe selection, Stage 8 workspace or Product Orchestrator in the v2 path.

### V2-C — application/transaction boundary

- Project Unit of Work;
- timeline command handlers;
- undo/redo transaction identity;
- handler registry.

### V2-D — user-visible Model Registry

- backend contract;
- named model/provider metadata;
- supported modes/options;
- explicit model picker;
- mapping to Capability Registry/Offer.

### V2-E — Job Manager

- project-scoped jobs;
- cancel/retry/progress;
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
5. slideshow/visualizer;
6. story/narrated/commercial templates/agent flows.

### V2-I — retire parallel truths

After caller migration:

- `/execution-plan`;
- recipe Product Orchestrator as modern authority;
- Stage 8 workspaces;
- mandatory recipe identity;
- donor-era frontend/API clients.

### V2-J — selectively restore release stack

Port proven packaging/native-host/integrity/update/rollback pieces from archived #59 onto the accepted Studio product, re-running exact-head evidence rather than assuming old artifacts prove new product acceptance.

## 9. First v2 acceptance gate

The Studio spine is accepted only when:

1. user creates/opens a normal project without choosing a recipe;
2. Studio shows Media Bin, Preview, Inspector and Timeline;
3. image/video can be imported into Project Store;
4. user can perform bounded clip add/move/trim/remove through UV commands;
5. same mutation contracts are callable programmatically;
6. timeline survives close/reopen;
7. MLT projection is derived from canonical UV timeline state;
8. deterministic export produces a registered result;
9. no Stage 6/8 or Product Orchestrator terminology appears in the v2 path;
10. schema-v1/recipe projects remain readable through compatibility paths.

## 10. Explicitly not part of the first migration

- a complete DaVinci-class NLE;
- every AI provider;
- a full micro-drama character/location system;
- node graph as default UI;
- hidden mandatory “best model” selection;
- wholesale deletion of old domain/recipe code;
- a new render engine replacing MLT/FFmpeg without evidence.

The migration is successful when every transferred capability makes the old product-specific path smaller while one Studio becomes more capable.
