# UV Studio — Current Architecture

**Status:** CURRENT AUTHORITY  
**Product-composition decision:** D-064  
**Shared production-semantics decision:** D-065  
**Editor foundation:** D-033

This document is the primary architecture entry point for new development. Historical recovery documents, Recipe Registry flows, Product Orchestrator projections and numbered Stage workspaces are not competing target architectures.

## Product definition

UV Studio is a **local-first AI production studio with multiple Production Directions over one shared production/application core**.

A Production Direction describes how a kind of production is organized: navigation, policies, specialized domain documents and Agent context. It does not create a separate editor engine, project store, timeline authority, execution stack or duplicate common Scene/Shot/Take semantics.

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
       organization / navigation / policy / Agent context
  -> Shared Production Semantic Core (optional per project)
       Sequence / Scene
       Shot
       Take / Candidate / Accepted Take
       semantic references / continuity / canon
       production-to-asset and production-to-timeline bindings
  -> Direction Extensions
       micro-drama: story / characters / locations / dramaturgy
       commercial: brief / product / brand / audience / concepts
       music-video: song / Music Map / sections / visual direction
       narrated: script / narration / semantic segments
       dub-battle: source scene / dialogue / cast / mix policy
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

Not every project must instantiate every production-semantic entity. `free_project` may remain Media/Assets/Timeline-only; a commercial may use Shots/Takes without a Story; a music video can group shared Shots under Music Map sections.

## Canonical authorities

- **Project Store** owns portable project state and project-owned references.
- **Production Direction identity** is typed Studio metadata and selects organization/policy, not execution engine.
- **Shared Production Semantic Core** owns reusable Scene/Shot/Take/accepted-material identities where needed.
- **Direction Extensions** own genuinely direction-specific data while referencing shared identities for common concepts.
- **Canonical Timeline** is UV-owned assembly state; MLT is derived behind the D-033 adapter.
- **Studio/Application Commands** are the shared semantic mutation boundary for GUI, Agent, scripts and MCP.
- **Project Unit of Work** owns atomic multi-document mutations and durable undo/redo across production semantics, project references/assets and Timeline.
- **Model Registry** will expose meaningful model choice to the user.
- **Job Manager** will own long-running generation lifecycle and provenance.
- **Capability Registry / D-017 / adapters** own execution availability, authorization and transport, not product identity.

## Production semantics versus Timeline

A Shot is not a Timeline Clip.

```text
Shot
  -> intent / references / continuity
  -> generated/imported candidate Takes
  -> accepted Take
  -> project-owned asset
  -> one or more Timeline clips for assembly
```

This gives the Agent/UI a production-level model without creating a second canonical timeline.

## Direction versus tool

A direction answers **what kind of production is being organized**. A tool answers **what operation should be performed inside a project**.

Directions: micro-drama, commercial, music video, narrated video, dub battle, free project.

Contextual tools: targeted edit, ordinary dubbing/translation, photo-to-video/slideshow, visualizer, action transfer, talking character, lip-sync, background replacement, image/video/audio generation.

A tool may be especially useful in one direction without becoming a separate project identity.

## Rules for new work

1. Do not add a `RecipeDefinition` to ship a new product direction or feature.
2. Do not grow Product Orchestrator recipe-by-recipe as the target application architecture.
3. Do not add a numbered Stage workspace as normal product navigation.
4. Do not create a second canonical project/timeline state.
5. Do not create a direction-specific editor engine.
6. Do not create parallel direction-specific Scene/Shot/Take schemas when the semantic concept is shared.
7. Do not hide user-significant model choice behind capability selection.
8. GUI, Agent, scripts and MCP must converge on the same application/domain commands.
9. Reuse mature media/editor/model components behind UV-owned boundaries rather than copying their application model.
10. Keep compatibility paths until call-site/dependency proof permits deletion.
11. Modern Studio identity must be validated independently from compatibility `recipe_id` and generic extensions mutation.

## Current implementation boundary before rich direction work

Stage 12 repairs the application seams identified after PR #63:

- modern Studio/project-media APIs use recipe-free common project contracts;
- modern Production Direction identity has a typed load/update/import gate with explicit compatibility and recovery projections;
- core project creation has no implicit recipe-era default;
- bounded `production/` storage is available for shared semantic documents;
- `ProjectUnitOfWork` coordinates strict canonical JSON with prepared journals, exact rollback/recovery and durable project-level undo/redo;
- timeline commands plus source/export reference registration use the shared transaction authority;
- HTTP and Studio UI expose the same canonical history rather than creating a frontend-only undo stack.

The next rich-direction slice may add shared Scene/Shot/Take contracts, but must route cross-document mutations through this unit of work. It must not widen the transaction journal to large media blobs or introduce a second state/undo authority.

## Compatibility layer

The repository still contains old recipe, Product Orchestrator, Stage 8 and donor-era paths because supported historical projects/domain implementations may depend on them.

They are **compatibility/migration code** unless a later accepted decision explicitly promotes something back into current architecture:

- schema-v1 `recipe_id` is compatibility metadata;
- Recipe Registry is not the v2 product taxonomy;
- Product Orchestrator is not the long-term product center;
- legacy `/execution-plan` is not current application truth;
- Stage 6/8 workspaces are not the template for new direction UI;
- useful targeted-edit, dubbing, music, continuity and media adapters should be extracted/reused rather than discarded;
- legacy projects may remain readable/editable in an explicit compatibility mode without being assigned a fake Production Direction.

See `docs/architecture/README.md`, D-064 and D-065.
