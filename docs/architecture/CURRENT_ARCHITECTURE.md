# UV Studio — Current Architecture

**Status:** CURRENT AUTHORITY  
**Product-composition decision:** D-064  
**Editor foundation:** D-033

This document is the primary architecture entry point for new development. Historical recovery documents, Recipe Registry flows, Product Orchestrator projections and numbered Stage workspaces are not competing target architectures.

## Product definition

UV Studio is a **local-first AI production studio with multiple Production Directions over one shared Studio Core**.

A Production Direction describes how a kind of production is organized. It may define domain documents, navigation, production policy, review rules and Agent context. It does not create a separate editor engine, project store, timeline authority or execution stack.

Initial directions:

- `micro_drama` — micro-drama / story production;
- `commercial` — advertising / product video;
- `music_video` — music-video production;
- `narrated_video` — narrated/explainer video;
- `dub_battle` — cinematic revoicing / dub battle;
- `free_project` — free-form Studio project.

## Canonical shape

```text
Project
  -> Production Direction
  -> direction-specific production state
       scenes / shots / characters / locations / takes
       OR brief / product / audience / concepts
       OR song / Music Map / sections / shots
       OR source scene / dialogue / cast / takes
       OR other direction-owned documents
  -> Shared Studio Core
       Media / Assets
       Preview / Canvas
       Inspector / AI Tools
       canonical Timeline
       Studio/Application Commands
       Project Unit of Work / Undo-Redo
       Model Registry
       Job Manager
       Agent
       Export
  -> Capability / Adapter boundaries
  -> MLT / FFmpeg / MCP / local models / optional remote tools
```

## Canonical authorities

- **Project Store** owns portable project state and project-owned references.
- **Production Direction state** lives in UV-owned versioned project documents, not RecipeDefinition execution graphs.
- **Canonical Timeline** is UV-owned; MLT is derived behind the D-033 adapter.
- **Studio/Application Commands** are the shared semantic mutation boundary for GUI, Agent, scripts and MCP.
- **Project Unit of Work** will own atomic multi-document mutations and undo/redo.
- **Model Registry** will expose meaningful model choice to the user.
- **Job Manager** will own long-running generation lifecycle and provenance.
- **Capability Registry / D-017 / adapters** own execution availability, authorization and transport, not product identity.

## Direction versus tool

A direction answers **what kind of production is being organized**. A tool answers **what operation should be performed inside a project**.

Examples of directions: micro-drama, commercial, music video, narrated video, dub battle, free project.

Examples of tools: targeted edit, ordinary dubbing/translation, photo-to-video/slideshow, visualizer, action transfer, talking character, lip-sync, background replacement, image-to-video.

A tool may be especially useful in one direction without becoming a separate project identity.

## Rules for new work

1. Do not add a `RecipeDefinition` to ship a new product direction or feature.
2. Do not grow Product Orchestrator recipe-by-recipe as the target application architecture.
3. Do not add a numbered Stage workspace as normal product navigation.
4. Do not create a second canonical project/timeline state.
5. Do not create a direction-specific editor engine when the shared Studio Core can host its domain state and tools.
6. Do not hide user-significant model choice behind capability selection.
7. GUI, Agent, scripts and MCP must converge on the same application/domain commands.
8. Reuse mature media/editor/model components behind UV-owned boundaries rather than copying their application model.
9. Keep compatibility paths until call-site/dependency proof permits deletion.

## Compatibility layer

The repository still contains old recipe, Product Orchestrator, Stage 8 and donor-era paths. They exist because supported historical projects or domain implementations may still depend on them.

They are classified as **compatibility/migration code** unless a later accepted decision explicitly promotes something back into current architecture. In particular:

- schema-v1 `recipe_id` is compatibility metadata;
- Recipe Registry is not the v2 product taxonomy;
- Product Orchestrator is not the long-term product center;
- legacy `/execution-plan` is not current application truth;
- Stage 6/8 workspaces are not the template for new direction UI;
- useful targeted-edit, dubbing, music, continuity and media adapters should be extracted/reused rather than discarded.

See `docs/architecture/README.md` for the document authority map and D-064 for the accepted decision rationale.
