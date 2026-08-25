# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: architecture-authority-cleanup -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Active review chore:

- PR #64 — `chore: consolidate architecture authority`;
- slice `architecture-authority-cleanup`;
- branch `chore/architecture-authority-cleanup`;
- base `main` at `cf0b719540e35fd10ec9a6fac8c3b905500ec35b`;
- previous completed slice: PR #63 `studio-v2-production-directions`, merge `4ff135ecd059acbce0fa8ff428ada8a47f6bc57b`.

This chore changes repository architecture memory/authority and next-slice boundaries, not runtime behavior.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions, so common Scene/Shot/Take/accepted-material semantics are not reimplemented per direction.
- **D-033** — MLT/editor foundation.

```text
Project
 -> validated Production Direction
 -> shared optional production semantics
      Sequence/Scene -> Shot -> Takes/Accepted Take
      semantic refs / continuity / asset/timeline bindings
 -> direction extensions
      story/characters/locations OR product/brand OR Music Map OR ...
 -> shared Studio Core
      Media/Assets / Preview / Inspector/AI / canonical Timeline
      Application Commands / Project Unit of Work / Models / Jobs / Agent / Export
 -> Capability/Adapter boundaries
```

A Shot is production meaning; a Timeline Clip is assembly. Production semantic state is not a second Timeline.

## Cleanup findings

The primary architecture is coherent after D-064/D-065, but the audit found code seams that must be addressed before rich domain/AI work:

1. modern `studio_timeline.py` and `project_media.py` import neutral project schemas/store dependency from recipe-aware `api/projects.py`, whose import graph pulls Recipe Registry/Product-Orchestrator catalog;
2. generic project creation and `ProjectStore.create_project()` retain recipe-era creation, including implicit `general_video` at the lower foundation;
3. modern Studio identity currently lives in arbitrary `extensions.studio` JSON: creation validates direction, but generic PATCH/import/load paths do not protect it as one typed invariant;
4. the initial extension writes `schema_version: 2` without a separate typed metadata-schema contract, conflating Studio-v2 naming with schema version semantics;
5. legacy projects can open the mechanical Studio editor without modern direction identity; future direction-domain commands therefore need explicit modern-vs-compatibility gating/migration;
6. generic frontend `projectsApi.ts` mixes neutral project access with recipe creation/execution-plan concepts;
7. `studio_timeline.py` already owns directions/project creation plus Timeline routes, so application responsibilities should split as UoW/commands grow.

These are strangler-boundary debt, not grounds for a rewrite.

## Compatibility assessment

Recipe Registry, Product Orchestrator, Stage 6/8 workspaces, legacy `/projects/{id}` and donor-era route/UI code may remain while supported old projects/tests need them. They are not templates for new product work and must not leak into modern neutral core dependencies.

Modern path:

```text
/projects -> Production Direction -> /projects/{id}/studio
```

Legacy projects may remain explicitly readable/editable in compatibility mode without being assigned a fake Production Direction.

## Next authorized product slice

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`, remains next after this cleanup closes. It first hardens modern Studio identity/dependency/storage boundaries, then establishes Project Unit of Work + undo/redo across shared production semantics, direction extensions, assets and Timeline.

The first rich direction afterward is micro-drama, used to prove the **shared** Scene/Shot/Take model plus Story/Characters/Locations/continuity extensions. Then Model Registry, Job Manager and named AI generation follow through the same command/transaction authority.
