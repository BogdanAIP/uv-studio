# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: architecture-authority-cleanup -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Active draft chore:

- PR #64 — `chore: consolidate architecture authority`;
- slice `architecture-authority-cleanup`;
- branch `chore/architecture-authority-cleanup`;
- base `main` at `cf0b719540e35fd10ec9a6fac8c3b905500ec35b`;
- previous completed slice: PR #63 `studio-v2-production-directions`, merge `4ff135ecd059acbce0fa8ff428ada8a47f6bc57b`.

This chore changes repository architecture memory and next-slice boundaries, not runtime product behavior.

## Current architecture authority

D-064 is the current product-composition authority. UV Studio is a **local-first AI production studio with multiple Production Directions over one shared Studio Core**.

```text
Project
 -> validated Production Direction identity
 -> direction-specific production state
 -> shared Studio Core
      Media / Assets
      Preview / Canvas
      Inspector / AI Tools
      canonical Timeline
      Studio/Application Commands
      Project Unit of Work / Undo-Redo
      Model Registry / Jobs
      Agent
      Export
 -> Capability / Adapter boundaries
 -> MLT / FFmpeg / MCP / local or optional remote tools
```

## Cleanup findings

The primary architecture documents are aligned, but the deeper audit found stale supporting documentation and four important code-boundary seams that must be addressed before rich domain/AI work:

1. modern Studio API imports neutral project schemas/store dependency from `api/projects.py`, whose import graph still pulls Recipe Registry/Product-Orchestrator catalog;
2. generic project creation and `ProjectStore.create_project()` still encode recipe-era creation, including implicit `general_video` at the lower store boundary;
3. D-064 product identity currently lives in arbitrary `extensions.studio` JSON: creation validates the direction, but generic PATCH/import/load paths do not yet protect it as a typed Studio invariant;
4. the generic frontend project client still exposes recipe creation/execution-plan concepts beside neutral project access, making accidental reuse by new code too easy.

These do **not** invalidate D-064 or require a rewrite. They are strangler-boundary debt and are now mandatory entry work for `studio-v2-application-transactions` before Project Unit of Work is built on top.

## Compatibility assessment

The following may remain while old projects/tests depend on them, but they are not templates for new code:

- Recipe Registry and recipe-create/execution-plan APIs;
- Product Orchestrator and `project_workflow` projections;
- Stage 6/8 workspaces and `/projects/{id}` legacy workspace;
- donor-era frontend/components and `/api/stages` compatibility metadata.

Modern `/projects -> Production Direction -> /projects/{id}/studio` is the product path. Legacy surfaces should be isolated/retired only after caller proof.

## Next authorized product slice

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`, remains next after this cleanup closes. Its first work is Studio identity/dependency-boundary hardening, followed by Project Unit of Work and undo/redo. The first rich domain after that is micro-drama Scenes/Shots/Characters/Locations/Takes.
