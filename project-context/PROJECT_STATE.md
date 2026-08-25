# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: architecture-authority-cleanup -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Active draft chore:

- slice `architecture-authority-cleanup`;
- branch `chore/architecture-authority-cleanup`;
- base `main` at `cf0b719540e35fd10ec9a6fac8c3b905500ec35b`;
- previous completed slice: PR #63 `studio-v2-production-directions`, merge `4ff135ecd059acbce0fa8ff428ada8a47f6bc57b`.

This chore runs before the next product slice and changes architecture memory, not the runtime product model.

## Current architecture authority

D-064 is the current product-composition authority. UV Studio is a **local-first AI production studio with multiple Production Directions over one shared Studio Core**.

The cleanup must make that authority unambiguous without deleting useful historical evidence or compatibility code.

Current shape:

```text
Project
 -> Production Direction
 -> direction-specific production state
 -> shared Studio Core
      Media / Assets
      Preview / Canvas
      Inspector / AI Tools
      canonical Timeline
      Commands / Project Unit of Work
      Model Registry / Jobs
      Agent
      Export
 -> Capability / Adapter boundaries
 -> MLT / FFmpeg / MCP / local or remote tools
```

## Cleanup scope

The chore will:

- add one current architecture entry point/index;
- clearly separate current, foundational, compatibility and historical architecture documents;
- mark D-042 as superseded at product-composition level;
- mark D-063 as partially superseded by D-064 while preserving its shared-Studio-Core decisions;
- clarify D-062 so Product Orchestrator is historical recovery infrastructure, not the long-term product center;
- reclassify Product Orchestrator, Recipe Registry, recipe execution and Product Truth Recovery documents as historical/compatibility snapshots where appropriate;
- add a bounded regression test so stale documents cannot silently become competing current authority again.

The chore will not remove working recipe/orchestrator/domain runtime code, `recipe_id` compatibility metadata, or useful targeted-edit/dubbing/music/continuity implementations without dependency proof.

## Next authorized product slice

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`, remains next after this cleanup closes.
