# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: project-identity-v2-compat-reader -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` merged through PR #89 as `a0150e1543b8b4c8f5d3ae8d1b701118fcb112d2`. The repository lifecycle is now `idle`; no subsequent product-development slice has started from this merge.

The accepted next handoff is `recipe-entrypoint-retirement` from the D-070 migration sequence. It may start only after this protected-main D-038 closure merges and a fresh bootstrap is run from the resulting lifecycle-closed `main`.

## Accepted Stage-19 result

Canonical Project persistence is schema v2 with exact legacy recipe identity under `compatibility.recipe_id`, while historical schema-v1 project/archive bytes remain readable without read-time rewrite and preserve unknown/uncreatable historical recipe IDs exactly.

Every ProjectReference carrying reserved `metadata.generation` authority must be a direct canonical `artifacts/generated_<attempt_id>[.<ext>]` path. Canonical persistence, Generation archive authority, Redo authority and restart recovery therefore agree on the same root/name shape. The earlier Stage-19 publication, crash recovery, exact-byte Generation authority, Undo/Redo, root-staging and cross-runtime fencing repairs remain part of the merged baseline.

## Final review and verification

The final fresh ordinary-ChatGPT semantic review of exact `52be1939eca51d7147990288cfc6258b023c2cd2..a237be2ff32a7fca280cd4f6b414ba19cd5870e6` returned `CURRENT / PASS / 0 findings / 12 rejected candidates` under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.

Ready CI #4739 (`33862150686`) passed all five permanent jobs on the frozen reviewed HEAD. After the semantic PASS, final merge-authoritative CI #4740 (`33871108872`) again passed all five permanent jobs on that same exact HEAD, including both Ubuntu/Windows full-unit suites, API integration, real-media verification, frontend lint/audit/build and browser Product Truth. The final live PR check found exact BASE/HEAD, `mergeable=true` and zero unresolved inline review threads before merge with `expected_head_sha=a237be2ff32a7fca280cd4f6b414ba19cd5870e6`.

## Handoff

The next bounded slice is `recipe-entrypoint-retirement`: exact-scan remaining modern/creation callers of Recipe Registry and `/api/uv/recipes`, including `frontend/lib/recipesApi.ts` and `projectsApi.createUVProject()`, migrate any real supported caller, and retire recipe-backed creation/metadata entrypoints only where old-project read/import compatibility no longer requires them.

Keep `/execution-plan` retirement, legacy direction/tool migration, Product Orchestrator retirement and Stage8 runtime/compatibility retirement as separate later slices in the accepted D-070 order.
