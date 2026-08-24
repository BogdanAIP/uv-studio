# D-063 — Studio-first product architecture

**Status:** Accepted  
**Date:** 2026-08-24

## Context

The Product Truth Recovery work correctly exposed stale VideoClaw runtime surfaces, false readiness and hidden workflow prerequisites. It also recovered many useful domain paths behind UV-owned boundaries. However, the recovery strategy then drifted toward making `RecipeDefinition -> Product Orchestrator -> relevant workspaces -> next actions` the main product composition model.

Installed-app review and a second repository-wide architecture audit show that this is the wrong long-term product center. The result is technically truthful but still shaped by implementation-era concepts: General Video, Story, Dubbing, Music, Stage 6/8 workspaces and other specialized flows compete to define the project instead of behaving as tools inside one professional studio.

The repository already contains a stronger foundation that should become the product spine:

- D-009 Project Store is a portable UV-owned canonical authority;
- D-033 already selected MLT behind a UV adapter plus selective OpenCut Classic editor-UX reuse;
- UV-owned Editor/Domain Commands already provide the intended GUI = scripts = AI = MCP mutation boundary;
- Capability Registry, D-017 authorization and MCP execution already separate semantic operations from replaceable transports;
- targeted edit, dubbing, continuity, music analysis/review and deterministic media operations contain valuable domain logic that can be surfaced as contextual Studio tools.

The architecture problem is therefore composition, not absence of useful foundations. A rewrite would discard proven work. Continuing recipe-by-recipe product growth would deepen the wrong coupling.

## Decision

UV Studio becomes a **Studio-first professional video/AI editing workspace**. A project is the primary product object. Recipes, stages and specialized workflows are not allowed to remain the normal top-level product taxonomy for new work.

The target composition is:

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

### 1. The user sees and chooses models

Provider/model abstraction must not hide meaningful creative choice. AI tools expose a visible model picker when multiple models are available. A user may explicitly select `Veo`, `Kling`, `Seedance`, a local model or another installed model. `Auto` may later be offered as an optional policy, never as the only path.

Settings own connections, credentials, runtimes and MCP/profile configuration. The Studio tool owns the model choice and model-specific creative parameters for the current operation.

Capability Registry remains underneath this UI. It answers what operation an implementation can execute, where, at what cost class and under what authorization. It does not replace the user-visible Model Registry.

### 2. The project model, not a recipe, is canonical

New projects are not created as `general_video`, `story_video`, `dubbing`, `music_video` or another product mode. They are UV Studio projects containing media, scenes/shots where useful, a canonical timeline and generated/derived artifacts.

The first bounded v2 project domain is:

```text
Project
  +-- Assets
  +-- Scenes
  |    +-- Shots
  +-- Timeline
  |    +-- Tracks
  |         +-- Clips
  +-- Generation records
```

Characters, locations, voices and richer production entities are added only when a proven user journey requires them.

The existing small `project.json`, ProjectReference ownership, archive/path/integrity rules and Project Store remain. Dedicated project files may live under existing or deliberately versioned project roots. MLT/XML remains a derived engine representation, never the public canonical project state.

`recipe_id` remains only as schema-v1 compatibility metadata until a migration can safely make it optional or neutral. No new v2 feature may rely on it as project identity.

### 3. D-033 is reaffirmed as the editor foundation

D-033 is not replaced. MLT remains the selected timeline/editing engine behind a UV adapter. OpenCut Classic remains a selective MIT UI/interaction donor. UV owns the canonical project/timeline contracts, semantic commands, security and provenance.

The existing `ProjectEditor` / `RangeTimeline` implementation is treated as the seed of the real Studio shell rather than a separate “targeted edit mode”. Its Media Bin, preview, timeline interaction and inspector layout are generalized while targeted editing becomes one contextual tool.

No second bespoke timeline engine is authorized.

### 4. Existing specialized workflows become contextual tools

Valuable work is preserved but moved to the correct product level:

- targeted edit -> selected Clip/Range **AI Edit** tool;
- dubbing/translation -> selected Clip/Audio **Dubbing** tool;
- Music Map/analysis -> selected audio/timeline **Analyze Music / Sync** tools;
- continuity -> Scene/Shot/Character **Consistency** tool;
- photo-to-video -> selected images **Add/Arrange on Timeline / Slideshow** tool;
- visualizer -> selected audio **Visualizer** tool;
- lip-sync/digital human -> media/character contextual tool;
- story, narrated, commercial and music-video concepts -> optional project templates, agent-assisted setup or production policies, not separate project engines.

Durable Brief/Plan/Candidate/Review records remain where they protect quality and provenance. They no longer justify a separate top-level workspace.

### 5. One command model remains mandatory

GUI, Agent, scripts and MCP operate through the same UV-owned application/domain commands. The Agent is not a privileged second product. It reads project state, proposes or invokes the same actions the user can invoke manually.

The command/application layer must grow toward:

- timeline commands (`add_clip`, `move_clip`, `trim_clip`, `split_clip`, `remove_clip`, track operations);
- Project Unit of Work / transaction grouping;
- product-level undo/redo;
- tool services that compose existing domain and capability operations;
- handler registries rather than growing central `if/elif` dispatch switches.

### 6. Long-running AI work requires a Job Manager

Normal image/video/audio generation must not be represented as a blocking form action. Before broad provider integration, UV Studio needs project-scoped jobs with at least queued/running/succeeded/failed/cancelled states, progress, cancellation, retry policy and exact input/model/output provenance.

Generation output is registered as project-owned media/artifact, receives a generation record, appears in the Media Bin, and is added to the timeline only through the normal command model.

### 7. Open-source reuse remains a core strategy, but donors do not define the product

The reuse-first strategy is reaffirmed. The correct integration sequence is:

```text
candidate -> license/evidence spike -> pin -> UV adapter/command boundary
          -> use the needed primitive -> tests -> Studio tool
```

The prohibited sequence is:

```text
donor -> copy donor application/workflow/project concepts -> expose them as UV mode
```

MLT, OpenCut, FFmpeg, Whisper-family tools, local model runtimes, MCP servers and future open-source components are parts/providers/donors. None becomes the canonical UV Studio application model merely because it supplies useful code.

## Freeze rules

Until a later decision explicitly changes them:

1. Do not add a new product `RecipeDefinition` to ship a feature.
2. Do not add a new numbered Stage UI as normal product navigation.
3. Do not add another specialized project workspace when the feature can be a Studio tool/state projection.
4. Do not expose provider-specific frontend execution branches when the Model/Capability/Adapter boundary can represent them.
5. Do not hide a user-significant model choice behind automatic capability selection.
6. Do not create an Agent-only mutation path.
7. Do not build a second canonical timeline or import raw MLT/OpenCut state as project authority.
8. Do not delete compatibility code until call-site/dependency proof exists.

## Migration strategy

This is a strangler migration, not a rewrite.

1. Freeze recipe/stage product expansion.
2. Generalize the existing D-033 editor into the Studio shell.
3. Introduce canonical multitrack Timeline/Track/Clip plus minimal Scene/Shot state in Project Store.
4. Add timeline/application commands and transaction/undo foundations.
5. Add a backend-owned user-visible Model Registry mapped onto Capability/Offer/Adapter execution.
6. Add a Job Manager.
7. Prove one named Image AI model from Inspector -> execution -> project-owned result -> Media Bin -> timeline.
8. Prove one named Video AI model with the same lifecycle.
9. Move targeted edit, dubbing, music and continuity into contextual Studio tools one by one.
10. Retire recipe Product Orchestrator, Stage 8 workspace and legacy `/execution-plan` only after their supported callers have moved.
11. Delete dead donor-era frontend/API clients after dependency proof.
12. Reduce VideoClaw toward donor/provenance-only status after proving no supported runtime path needs its backend injection.

## First v2 implementation proof

The first implementation slice after the architecture map is deliberately **not a cloud-provider integration**. It proves the editor spine:

```text
open project
 -> Media Bin
 -> import existing image/video
 -> add clip through UV command
 -> canonical multitrack timeline save
 -> close/reopen
 -> preview/playhead
 -> derived MLT projection
 -> deterministic export
```

Required proof:

- no recipe choice is involved;
- no Stage 8 workspace is involved;
- UI and programmatic callers use the same timeline commands;
- canonical timeline reloads from Project Store;
- MLT remains derived;
- old projects remain readable through explicit compatibility boundaries.

Only after this spine is green should the next vertical add Model Registry + one real AI generator.

## Supersession / compatibility

- **D-033 remains accepted and is strengthened.**
- **D-062 remains accepted for Product Truth, cold-start evidence and legacy-runtime isolation**, but its statement that Product Orchestrator must remain the long-term product center is superseded by this decision. Product Orchestrator becomes a migration/compatibility projection while Studio/Application Commands become the target product boundary.
- **D-042 is superseded at the product-composition level.** Its good invariants — Project Store authority, shared engines, truthful capability gating and no hidden paid execution — remain. Its recipe-first user-facing mode strategy does not.
- Earlier recipe definitions and Stage 8 workspaces remain compatibility state until migration evidence permits retirement.

## Rejected alternatives

### Rewrite UV Studio from scratch

Rejected. Project Store, D-017, Capability/MCP execution, D-033, deterministic media, editor/domain commands, specialized editing/dubbing/music/continuity logic and Windows packaging are substantial reusable assets.

### Continue recipe-by-recipe Product Orchestrator recovery

Rejected as the long-term architecture. It can make individual modes truthful, but it preserves the wrong top-level product taxonomy and multiplies orchestration code around implementation-era modes.

### Hide all models behind automatic semantic capabilities

Rejected. Provider-neutral execution is valuable internally, but model choice is a professional creative decision and must remain visible where relevant.

### Make ComfyUI/node graphs the default product UI

Rejected. Node graphs may be an expert/provider execution source, but the normal UV Studio product remains a scene/media/timeline editor with contextual AI tools.

### Copy an entire open-source editor or AI application

Rejected. UV Studio deliberately composes proven components behind UV-owned contracts instead of inheriting another application's storage, account, workflow and product assumptions.
