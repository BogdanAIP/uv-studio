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
- durable project transaction journals and undo/redo history;
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
  production/
  timeline/
  history/
    index.json
    transactions/
    operations/
  reviews/
  exports/
```

Direction-specific documents should use deliberate versioned project-owned files rather than turning `project.json` into one universal film schema.

## Project identity and Production Direction

Schema v1 still requires `recipe_id`; modern Studio projects use neutral compatibility value `studio_v2`. Under D-064, the meaningful product composition is Studio metadata containing `product_model=production_directions` and a known `direction_id`.

Modern Studio identity is validated as a typed invariant on load, update and archive-import boundaries. Generic mutation cannot silently replace a valid Production Direction or convert compatibility identity into modern identity. Legacy and invalid projects remain explicit compatibility/recovery states rather than receiving a guessed direction.

The exact schema-v2 Production Direction shape created by PR #63 remains a valid modern direction and is normalized to the current typed identity view without rewriting project bytes. New projects write the independent typed identity schema v1.

Changing Production Direction in the future, if supported, should be an explicit semantic migration operation rather than an arbitrary `extensions` patch.

## Atomicity and transactions

Individual writes use atomic replacement under an in-process re-entrant lock. Cross-document application commands use `ProjectUnitOfWork`: it validates prospective canonical state, writes a prepared journal before canonical files, restores exact byte snapshots on failure/interruption and publishes the committed marker as the final commit point.

History is project-owned and portable. Undo/redo verifies that current canonical bytes still match the expected transaction snapshot, fails closed on out-of-band mutation, survives process restart/archive round-trip and truncates a stale redo branch when a new command commits. The bounded transaction document set is `project.json` plus strict JSON under `production/`, `timeline/`, `tasks/` and `reviews/`; large media bytes remain project files referenced by canonical metadata rather than being copied into undo journals. MLT remains derived.

Timeline commands, source-media registration and Studio export registration use this authority. New semantic production commands must commit all related production/reference/timeline changes in one unit of work rather than composing independent stores.

## Compatibility debt

Generic compatibility APIs still accept explicit recipe identity, but lower Project Store creation no longer supplies an implicit `general_video` default. Modern Studio creation uses the dedicated Production Direction path.

Legacy projects/imports remain readable until migration/caller proof supports removal.

## Portability and security

`ProjectReference.path` is canonical project-relative data. Absolute paths, traversal and symlink escape are rejected; file-consuming operations additionally restrict allowed roots. Project archives use staged validation/integrity checks before atomic import. See `docs/PROJECT_ARCHIVES.md`.
