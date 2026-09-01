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

Canonical Project persistence is schema v2. Legacy recipe identity is retained exactly as compatibility state under `compatibility` rather than as top-level canonical product identity:

```json
{
  "schema_version": 2,
  "compatibility": {
    "schema_version": 1,
    "recipe_id": "studio_v2"
  }
}
```

Historical schema-v1 Project files still carry top-level `recipe_id`. They remain readable through the Project migration boundary and are upgraded to the current schema in memory without rewriting the historical bytes merely because the project was read. A later deliberate canonical Project write persists schema v2.

Modern Studio projects use the neutral compatibility recipe value `studio_v2`. Under D-064, meaningful product composition is typed Studio metadata containing `product_model=production_directions` and a known `direction_id`; the compatibility recipe value is not the Production Direction.

Modern Studio identity is validated as a typed invariant on load, update and archive-import boundaries. Generic mutation cannot silently replace a valid Production Direction or convert compatibility identity into modern identity. Legacy and invalid projects remain explicit compatibility/recovery states rather than receiving a guessed direction.

The Production Direction shape created by PR #63 remains a valid modern direction and is normalized to the current typed identity view without rewriting project bytes. New modern projects write Project schema v2 plus the independent typed Studio identity schema v1.

Changing Production Direction in the future, if supported, should be an explicit semantic migration operation rather than an arbitrary `extensions` patch.

## Atomicity and transactions

Individual writes use atomic replacement under an in-process re-entrant lock. Cross-document application commands use `ProjectUnitOfWork`: it validates prospective canonical state, writes a prepared journal before canonical files, restores exact byte snapshots on failure/interruption and publishes the committed marker as the final commit point.

History is project-owned and portable. Undo/redo verifies that current canonical bytes still match the expected transaction snapshot, fails closed on out-of-band mutation, survives process restart/archive round-trip and truncates a stale redo branch when a new command commits. Historical schema-v1 `project.json` snapshots are migrated only for current-schema validation during undo/redo; the snapshot bytes themselves remain authoritative for restoration, so undo can restore the exact original v1 bytes and redo can restore the exact later v2 bytes. The bounded transaction document set is `project.json` plus strict JSON under `production/`, `timeline/`, `tasks/` and `reviews/`; large media bytes remain project files referenced by canonical metadata rather than being copied into undo journals. MLT remains derived.

Timeline commands, source-media registration and Studio export registration use this authority. New semantic production commands must commit all related production/reference/timeline changes in one unit of work rather than composing independent stores.

## Media publication and recovery fencing

Canonical media bytes and their Project identities form one recoverable publication state even though large media bytes are not copied into transaction journals. Current publishers that may perform long-running work prepare incomplete or provider-produced bytes at the Project Store root, outside every canonical project directory. Only the short consequence-bearing publication step enters the shared cross-runtime project fence, moves complete bytes to the canonical project-relative path and registers the matching Project/Production/Job metadata before releasing that fence.

Source upload, `timeline.assemble`, WebVTT subtitle export and named Generation use this proactive staging pattern. A concurrent portable archive therefore observes either the complete pre-publication project or the complete registered publication; it must not recover canonical bytes without the identity/provenance that makes those bytes part of the project.

The archive-side UUID-name detector for unregistered `src_` / `art_` / `aud_` files is a fail-closed compatibility fallback for historical publishers, not the authority for current publication. Current publishers must participate in the shared staging/fence protocol even when their canonical filenames use other conventions such as `sub_`, `generated_` or caller-selected output names.

## Compatibility debt

Generic compatibility APIs still accept explicit recipe identity and may expose a compatibility `recipe_id` field, but they derive it from the schema-v2 compatibility boundary. Lower Project Store creation no longer supplies an implicit `general_video` default. Modern Studio creation uses the dedicated Production Direction path.

Legacy projects/imports remain readable until migration/caller proof supports removal.

## Portability and security

`ProjectReference.path` is canonical project-relative data. Absolute paths, traversal and symlink escape are rejected; file-consuming operations additionally restrict allowed roots. Project archives use staged validation/integrity checks before atomic import. See `docs/PROJECT_ARCHIVES.md`.
