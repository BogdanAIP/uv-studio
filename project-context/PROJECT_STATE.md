# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-store-portable-json-hardening -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **draft** on `project-store-portable-json-hardening` in PR #50, branched from idle `main` commit `dd5871ad787cc14897de2dee8eb6af4292b7c1ed` after repository-hygiene PR #49 merged and its lifecycle closed.

This slice hardens the existing canonical Project Store boundary before Narrated recovery. It does not introduce a new store, change Product Orchestrator ownership, or resume Stage 9 packaging.

## Contract being hardened

Canonical project state must be portable JSON at every persistence seam:

- `ProjectDocument.settings` and `ProjectDocument.extensions` are recursively validated;
- `ProjectReference.metadata` is recursively validated and revalidated when references are carried through a document;
- JSON objects require string keys and arrays require JSON array values rather than arbitrary Python containers;
- `NaN`, `Infinity` and `-Infinity` are invalid;
- non-JSON Python objects and recursive containers are invalid;
- `project.json` reads reject non-standard non-finite constants and writes use strict serialization;
- archive import must pass the same canonical `load_project()` validation before commit;
- `list_projects()` must keep healthy projects visible when another project is malformed or invalid;
- damaged project bytes are preserved for diagnosis/recovery rather than deleted or silently rewritten.

The public `/api/uv/projects` listing remains a list of healthy `ProjectPayload` values. Store callers that need recovery detail can use bounded per-project listing diagnostics without changing the stable API response shape.

## Verification target

Before Review, the exact Draft head must prove:

- create/update/save paths cannot persist nested non-portable values;
- reopening rejects non-finite/non-standard JSON constants;
- archive import with a valid manifest/hash still rejects non-portable `project.json` before canonical commit;
- a corrupt project does not prevent healthy-project discovery and its bytes remain untouched;
- existing path/symlink, migration, atomic-write, archive and API behavior remains intact;
- all five permanent Ubuntu/Windows CI checks pass.

This slice does not claim repair of corrupt projects, Narrated recovery, Class C cold-start usability, installed Windows human acceptance or Stage 9 release readiness.

## Next authorized slice

`project-store-portable-json-hardening` is active in PR #50. After it is reviewed, merged and lifecycle returns to idle, the next authorized slice is `product-recovery-narrated-orchestration` as defined by `project-context/NEXT_TASK.md`.
