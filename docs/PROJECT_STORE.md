# UV Studio Project Store

**Status:** CURRENT FOUNDATIONAL CONTRACT  
**Product authority:** D-064 / `docs/architecture/CURRENT_ARCHITECTURE.md`

UV Studio owns canonical project state independently of chat sessions, VideoClaw sessions and editor-engine files.

## Current role

Project Store owns:

- versioned `project.json` metadata;
- project-owned source/asset/artifact references;
- versioned production/domain documents;
- canonical timeline and review state;
- portable `.uvproj.zip` archive import/export;
- strict project-relative path/integrity boundaries and atomic single-file persistence.

MLT state, FFmpeg commands, provider credentials and machine runtime configuration are not canonical project state.

## Layout

```text
projects/prj_<id>/
  project.json
  sources/
  assets/
  tasks/
  artifacts/
  timeline/
  reviews/
  exports/
```

Direction-specific documents should use deliberate versioned project-owned files rather than turning `project.json` into one universal film schema.

## Project identity and Production Direction

Schema v1 still requires `recipe_id`; modern Studio projects use neutral compatibility value `studio_v2`. Under D-064, the meaningful product composition is Studio metadata containing `product_model=production_directions` and a known `direction_id`.

**Current debt:** the v1 `extensions` mapping is generic JSON and the generic project update API can replace it. Creation validates `direction_id`, but the Project Store does not yet enforce Studio identity as a typed invariant on every modern load/update/import path. Before rich direction-domain/Agent work relies on it, the next application-foundation slice must introduce a validated Studio identity boundary and prevent arbitrary generic mutation from silently changing/corrupting it.

Changing Production Direction in the future, if supported, should be an explicit semantic migration operation rather than an arbitrary `extensions` patch.

## Atomicity and transactions

Current Project Store writes use atomic replacement and an in-process re-entrant lock, preventing partial individual JSON writes. This is **not** a multi-document transaction.

The next `ProjectUnitOfWork` foundation must coordinate one semantic operation across production/domain documents, references/assets, generation/take state, timeline and undo history with rollback on failure. MLT remains derived.

## Compatibility debt

`ProjectStore.create_project()` and generic project APIs still carry recipe-era creation semantics/defaults. Modern Studio creation uses the dedicated Production Direction path, but the lower foundation should stop making `general_video` the implicit default so new backend/application code cannot accidentally create legacy identity.

Legacy projects/imports remain readable until migration/caller proof supports removal.

## Portability and security

`ProjectReference.path` is canonical project-relative data. Absolute paths, traversal and symlink escape are rejected; file-consuming operations additionally restrict allowed roots. Project archives use staged validation/integrity checks before atomic import. See `docs/PROJECT_ARCHIVES.md`.
