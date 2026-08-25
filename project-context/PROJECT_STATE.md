# Project State

<!-- uv-context-state: idle -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

No development slice is active. `main` is the integration authority.

Last completed slice:

- PR #63 — `studio-v2-production-directions`;
- merge commit `4ff135ecd059acbce0fa8ff428ada8a47f6bc57b`;
- review head `9ddd2d6df78c09160f140bb21e7bfce7fe881bb6` passed all five permanent CI jobs before merge.

## Architecture conclusion

D-064 is the current product-composition authority. UV Studio is a **local-first AI production studio with multiple Production Directions over one shared Studio Core**.

Canonical composition:

```text
Project
 -> Production Direction
 -> direction-specific production documents where needed
 -> shared Studio Core
      Media / Assets
      Preview / Canvas
      Inspector / AI Tools
      canonical Timeline
      Project Unit of Work / Undo-Redo
      Model Registry / Jobs
      Agent / Commands
      Export
```

Current first-class Production Directions:

- `micro_drama` — Микродрама / сюжетное видео;
- `commercial` — Реклама / продукт;
- `music_video` — Музыкальный клип;
- `narrated_video` — Видео с диктором;
- `dub_battle` — Киноозвучка / Кинобатл;
- `free_project` — Свободный проект.

Production Directions are not recipes or execution engines. Operation-level features such as targeted edit, ordinary dubbing/translation, photo-to-video, visualizer, action transfer, digital human and lip-sync remain contextual Studio tools.

## Retained foundations

- Project Store and project-owned portable state;
- canonical `timeline/main.json`;
- D-033 editor foundation;
- MLT behind a UV adapter and FFmpeg deterministic media/export paths;
- shared GUI = Agent = scripts = MCP command semantics;
- Capability Registry, D-017 authorization and MCP boundaries;
- existing targeted-edit, dubbing/translation, continuity and music domain/review logic where it protects real invariants;
- compatibility code until caller/dependency proof permits retirement.

## Compatibility / legacy

Do not grow these as long-term product authority:

- `recipe_id` as v2 project identity;
- new `RecipeDefinition` entries for product features;
- recipe-by-recipe Product Orchestrator growth;
- Stage 6/Stage 8 product navigation;
- separate project workspaces/engines per direction;
- legacy `/execution-plan` as modern truth;
- donor-era VideoClaw frontend/API taxonomy.

## Next authorized product slice

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`.

Before that product slice begins, architecture-memory cleanup may run as a bounded chore so superseded recipe/Product Orchestrator documents cannot be mistaken for current authority. Such cleanup must preserve useful historical evidence and runtime compatibility until dependency proof supports deletion.
