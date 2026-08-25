# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-production-directions -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Active draft slice:

- PR #63 — `stage 11: restore Studio production directions`;
- branch `stage-11/studio-v2-production-directions`;
- base `main` at `44b5483a956a72b4532839b8f4222c1433bed8e4`;
- previous completed slice: PR #61 `studio-v2-editor-spine`, merge `5be716ed44ac00f7d13cafb8b4ed038ddc24878b`.

The current slice corrects product composition before `studio-v2-application-transactions` begins.

## Architecture conclusion

D-064 is the current long-term product-composition authority. D-063 remains accepted for the shared Studio Core it established, but its prohibition on meaningful top-level production-direction choice is superseded.

UV Studio is being developed as a **local-first AI production studio with multiple Production Directions over one shared Studio Core**.

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

The initial Production Directions are:

- `micro_drama` — Микродрама / сюжетное видео;
- `commercial` — Реклама / продукт;
- `music_video` — Музыкальный клип;
- `narrated_video` — Видео с диктором;
- `dub_battle` — Киноозвучка / Кинобатл;
- `free_project` — Свободный проект.

These directions are not recipes or execution engines. They organize domain state, navigation, production policy and Agent context while sharing Project Store, Timeline, models/jobs, commands and export infrastructure.

Operation-level features such as targeted edit, ordinary dubbing/translation, photo-to-video, visualizer, action transfer, digital human and lip-sync remain contextual Studio tools rather than top-level project identities.

## What remains good and retained

PR #61 remains the correct lower product spine and is not being reverted:

- Project Store, project-owned paths/references, archive/migrations and integrity checks;
- canonical `timeline/main.json`;
- D-033 editor foundation;
- MLT behind a UV adapter and FFmpeg deterministic media/export paths;
- `TimelineCommandService` and the GUI = Agent = scripts = MCP command rule;
- Capability Registry, D-017 authorization and MCP boundaries;
- existing targeted-edit, dubbing/translation, continuity and music domain/review logic where it protects real invariants;
- Windows packaging/native-host engineering preserved as reference from archived #59.

The Studio shell remains common. Production Directions compose around it instead of creating separate editor applications.

## Current implementation in PR #63

The draft slice currently establishes:

- new `uv_studio.production` layer independent of legacy recipes;
- backend Production Direction catalog with six first-class directions;
- Studio project creation requiring a `direction_id` while retaining neutral schema-v1 `recipe_id=studio_v2` compatibility metadata;
- Studio extension schema v2 with `product_model=production_directions` and the selected `direction_id`;
- task-oriented cards on `/projects`;
- Class-C expectations that direction cards are visible while operation-level tool cards stay absent;
- D-064 and durable architecture instructions so future work does not collapse back to one generic editor-only project.

Full direction-specific production entities are intentionally not implemented in this slice. Micro-drama characters/locations/scenes/shots/takes, commercial brief/product/concepts, Music Map composition and dub-battle dialogue/cast/takes remain subsequent domain work over the shared core.

## Compatibility / legacy

Do not grow these as long-term product authority:

- `recipe_id` as v2 project identity;
- new `RecipeDefinition` entries for product features;
- recipe-by-recipe Product Orchestrator growth;
- Stage 6/Stage 8 product navigation;
- separate project workspaces/engines per direction;
- legacy `/execution-plan` as modern truth;
- donor-era VideoClaw frontend/API model taxonomy.

Compatibility code remains until callers are proven migrated; this is still a strangler migration.

## Verification status

PR #63 is still draft. Exact-head CI and final review evidence are not yet claimed. Before review, the implementation, context, tests and PR body must agree and all five permanent checks must pass on the exact review head.

## Next authorized slice

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`.

That slice must make Project Unit of Work / undo-redo span production-domain documents, project assets/references and canonical timeline state rather than hardening only timeline mutations.
