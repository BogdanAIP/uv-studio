# D-064 — Production Directions over shared Studio Core

**Status:** Accepted  
**Date:** 2026-08-25

## Context

D-063 correctly rejected recipe-by-recipe product engines, Stage-first navigation and multiple competing workspaces. PR #61 then proved the common Studio editor spine: Project Store -> Media Bin -> canonical multitrack Timeline -> shared commands -> derived MLT -> deterministic FFmpeg export.

Product review after that merge exposed an overcorrection. The repository had interpreted "one Studio" as "no meaningful production choice at project creation". The clean path became one generic Studio project and the UI/CI explicitly removed all task cards.

That loses an important part of the original LocalMiniDrama-inspired product idea: different kinds of video production need different domain organization even when they share the same editor, media store, models, jobs and export engine. A micro-drama is organized around story/characters/locations/scenes/shots/takes; a commercial around product/brief/audience/concepts/product shots; a music video around the song/Music Map/sections/visual direction; a dub-battle around scene/roles/dialogue/cast/takes/mix.

The old Recipe Registry cannot simply be restored as product authority because it mixed two different levels:

- production directions such as story, commercial, music video and free project;
- operation-level tools such as photo-to-video, visualizer, action transfer, talking character and lip-sync.

The correction must therefore preserve D-063's common technical spine while restoring product-level production composition.

## Decision

UV Studio is one **shared Studio Core** with multiple **Production Directions**.

A Project remains the primary canonical product object. A Production Direction is project metadata and domain composition that answers **how this kind of production is organized**, not **which execution pipeline/provider runs it**.

```text
Project
  |
  +-- Production Direction
  |     micro_drama | commercial | music_video
  |     narrated_video | dub_battle | free_project
  |
  +-- Direction-specific production documents
  |     scenes/characters/locations | commercial brief | Music Map | cast/takes | ...
  |
  +-- Shared Studio Core
        Assets / Media
        Preview / Canvas
        Inspector / AI Tools / Model Picker
        Canonical Timeline
        Project Unit of Work / Undo-Redo
        Jobs / Generations
        Agent / Commands
        Export
```

### 1. Production Direction is not RecipeDefinition

New v2 directions MUST NOT be implemented as new `RecipeDefinition` entries and MUST NOT revive recipe-specific execution plans, Product Orchestrator graphs, Stage workspaces or separate canonical project engines.

A direction may declare product-composition metadata such as:

- `direction_id`;
- title/description;
- primary starting input;
- workspace/domain sections;
- default relevant tools;
- later, direction-specific production policies and domain document schemas.

Execution continues through common application commands, Tool Services, Model Registry, Job Manager, Capability Registry and adapters.

### 2. Initial top-level Production Directions

The initial product catalog is:

1. `micro_drama` — **Микродрама / сюжетное видео**;
2. `commercial` — **Реклама / продукт**;
3. `music_video` — **Музыкальный клип**;
4. `narrated_video` — **Видео с диктором**;
5. `dub_battle` — **Киноозвучка / Кинобатл**;
6. `free_project` — **Свободный проект**.

These are product journeys because each can require distinct production entities, navigation, planning/review policy and Agent context.

`general_video` is not a separate initial direction; its unconstrained role is covered by `free_project` unless a later user journey proves a meaningful separate production model.

### 3. Tools are not top-level project identities

The following remain contextual Studio tools/quick actions rather than Production Directions:

- targeted/range edit;
- ordinary dubbing/translation;
- photo-to-video/slideshow;
- visualizer;
- action transfer;
- talking character/digital human;
- performance/lip-sync;
- background removal and similar transforms;
- future image/video/audio generation operations.

A tool may be especially relevant to one direction without becoming that direction's engine.

### 4. Shared Studio shell, composable direction navigation

All directions open the same Studio shell and share the same project/timeline authority. Direction selection may alter the production navigation and contextual panels.

Examples:

```text
micro_drama:
  Story / Characters / Locations / Scenes / Shots / Assets

commercial:
  Brief / Product / Brand / Audience / Concepts / Shots / Assets

music_video:
  Song / Music Map / Sections / Visual Direction / Shots / Assets

dub_battle:
  Source Scene / Characters / Dialogue / Cast / Takes / Mix

free_project:
  Media / Assets / Timeline
```

This is composition inside one application, not six separate React applications or backend runtimes.

### 5. Canonical project identity

Project schema v1 still requires `recipe_id`. New Studio projects continue to use neutral compatibility value `studio_v2` until a later migration makes that field optional.

New product identity is stored in Studio extension metadata:

```json
{
  "studio": {
    "schema_version": 2,
    "product_model": "production_directions",
    "direction_id": "micro_drama"
  }
}
```

No v2 execution path may branch on the compatibility `recipe_id` to choose its engine.

Direction-specific canonical state should live in versioned project-owned documents rather than expanding `project.json` into one universal film schema. Projects only carry the production documents their direction/user journey actually needs.

### 6. Project Unit of Work must span production state

The next transaction/undo slice must not be timeline-only. `ProjectUnitOfWork` or equivalent must be capable of atomically coordinating direction/domain documents, project references/assets, generation records and timeline changes.

Representative future operation:

```text
AcceptTake(shot_12_3, take_4)
  -> mark take accepted
  -> update Shot state
  -> register project asset
  -> replace/add timeline clip
  -> record undo transaction
```

A failure during the composed operation must not leave split project state.

### 7. Agent shares the same direction-aware project model

The Agent may use direction metadata and domain documents to understand the production task, but it still invokes the same Studio/Application Commands and Tool Services as the GUI/scripts/MCP. No direction creates a privileged Agent-only mutation path.

### 8. Local-first scope remains unchanged

This decision does not introduce cloud hosting, collaboration, public content libraries, marketplaces or server-side media ownership. The maintained target remains a local-first desktop product; optional providers remain replaceable capabilities.

## Consequences

- The new-project screen again asks what the user wants to create, but the choice is a Production Direction rather than a Recipe/pipeline.
- Common Studio/editor work from PR #61 is retained, not reverted.
- Product-specific domain entities can grow where they create real value without forcing them on every project.
- Class-C product truth must verify direction discovery/selection while continuing to prove shared Studio editing/export.
- Legacy recipe definitions remain compatibility/reference material only.

## Supersession / compatibility

- **D-063 remains accepted for the shared Studio Core, Project-first authority, contextual tools, Model/Capability separation, common command model, Job Manager direction and strangler migration.**
- **D-064 supersedes the D-063 statements that prohibit normal top-level production-direction taxonomy or require story/commercial/music concepts to be only templates/tools.** Distinct Production Directions are now first-class product composition over the shared core.
- **D-042 recipe-first execution/product identity remains superseded.** D-064 does not restore recipes as canonical product engines.
- D-033, D-017, D-009 and other lower-layer decisions remain unchanged.

## Rejected alternatives

### Revert PR #61 and restore the old Recipe UI

Rejected. The old UI mixed production directions and operations and coupled project identity to recipe-era orchestration. The new editor spine is the correct common foundation.

### Keep one generic Studio project and make all directions prompt templates

Rejected. Micro-drama, commercial, music and dub-battle require materially different production entities/navigation/policies; reducing them to prompts loses the product's domain value.

### Create a separate application/workspace engine per direction

Rejected. Direction-specific product composition must stay above one Project Store, one Studio shell, one command authority and one canonical timeline.
