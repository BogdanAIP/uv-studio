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

Fresh `ProjectUnitOfWork.commit()` input that includes `project.json` must declare the current raw Project schema before it can become canonical. Migration-before-validation is reserved for historical undo/redo snapshots. This keeps exact legacy v1 history restorable without allowing a new transaction to downgrade canonical storage back to schema v1.

Modern Studio projects use the neutral compatibility recipe value `studio_v2`. Under D-064, meaningful product composition is typed Studio metadata containing `product_model=production_directions` and a known `direction_id`; the compatibility recipe value is not the Production Direction.

Modern Studio identity is validated as a typed invariant on load, update and archive-import boundaries. Generic mutation cannot silently replace a valid Production Direction or convert compatibility identity into modern identity. Legacy and invalid projects remain explicit compatibility/recovery states rather than receiving a guessed direction.

The Production Direction shape created by PR #63 remains a valid modern direction and is normalized to the current typed identity view without rewriting project bytes. New modern projects write Project schema v2 plus the independent typed Studio identity schema v1.

Changing Production Direction in the future, if supported, should be an explicit semantic migration operation rather than an arbitrary `extensions` patch.

## Atomicity and transactions

Individual writes use atomic replacement under an in-process re-entrant lock. Cross-document application commands use `ProjectUnitOfWork`: it validates prospective canonical state, writes a prepared journal before canonical files, restores exact byte snapshots on failure/interruption and publishes the committed marker as the final commit point.

History is project-owned and portable. Undo/redo verifies that current canonical bytes still match the expected transaction snapshot, fails closed on out-of-band mutation, survives process restart/archive round-trip and truncates a stale redo branch when a new command commits. Historical schema-v1 `project.json` snapshots are migrated only for current-schema validation during undo/redo; the snapshot bytes themselves remain authoritative for restoration, so undo can restore the exact original v1 bytes and redo can restore the exact later v2 bytes. Fresh commit input is stricter: raw `project.json` must already declare schema v2. The bounded transaction document set is `project.json` plus strict JSON under `production/`, `timeline/`, `tasks/` and `reviews/`; large media bytes remain project files referenced by canonical metadata rather than being copied into undo journals. MLT remains derived.

Timeline commands, source-media registration and Studio export registration use this authority. New semantic production commands must commit all related production/reference/timeline changes in one unit of work rather than composing independent stores.

Generation Job records remain durable execution/provenance history outside user Undo/Redo. A successful attempt's stored `output_reference_id` and `take_id` therefore remain historical facts even if a later user Undo removes the corresponding current Production Take. Current Production authority is still the Production Semantics document: consumers that require a live Take must resolve it there rather than treating the Job's historical `take_id` string as current state.

Because ProjectUnitOfWork snapshots canonical JSON rather than binary media, Undo of `generation.register_output` deliberately leaves the already-published generated bytes in place while that transaction remains reachable through the current Redo suffix. That temporary binary preservation is not pathname authority. The validated redo `project.json` snapshots retain the full historical Generation ProjectReference, and its durable Job/Attempt/provenance plus persisted `size_bytes` and SHA-256 remain mandatory. Archive export, startup recovery and direct Redo all fail closed if redo-owned Generation bytes no longer match that historical authority. A later canonical commit truncates the redo suffix and removes the protection, after which the same unregistered managed bytes become ordinary orphan candidates again.

## Media publication and crash recovery

Canonical media bytes and their owning Project/Production/Generation identities form one recoverable publication state even though large media bytes are not copied into transaction journals. Long render/provider work is staged at the Project Store root, outside every canonical project directory. The shared cross-runtime project fence still serializes the short consequence-bearing publication step against archive export and other canonical writers, but that live lock is not itself crash durability.

Current crash recovery therefore uses three bounded mechanisms without introducing a second project authority:

1. `timeline.assemble` can publish to an arbitrary caller-selected `artifacts/` or `exports/` path. Immediately before its canonical `os.replace`, while already holding the shared project fence, it writes a small `pub_<uuid>` managed-publication marker under `tasks/` containing both the canonical path and expected ProjectReference identity. Normal completion removes the marker only after that exact ProjectReference is durable. If the process dies, archive export refuses the project while the marker remains; startup clears a stale marker only when the registered reference matches both marker path and `reference_id`. A different dangling reference that merely names the same path cannot claim new crash-left bytes, which are quarantined outside the canonical project before the marker is cleared.
2. Source upload `src_<uuid>.*`, WebVTT `sub_<uuid>.vtt` and named Generation `generated_attempt_<uuid>.*` outputs are self-identifying UV-owned publications. If hard process loss leaves those canonical bytes without a ProjectReference, startup reconciliation moves them to quarantine at the Project Store root and archive export fails closed until that split state is resolved. Registered references are left untouched. Ordinary unregistered project files with unrelated names remain portable.
3. Generation has additional durable boundaries after the artifact ProjectReference is committed. Every consequence-bearing Generation Job transition participates in the same cross-runtime project fence, so cancel/fail/retry cannot interleave with final publication. Retry/fail/cancel are blocked while any attempt in that Job owns a durable artifact that has not yet been reconciled as that attempt's success. Recovery is attempt-specific rather than current-attempt-only: a historical artifact created by `attempt0` remains owned by `attempt0` even if an older runtime later appended `attempt1`. Recovery validates and completes the artifact-owning attempt in place; it never rewrites identity to make an old artifact appear to belong to the newest attempt. Repairing an older attempt does not overwrite the newer attempt or the Job's current overall status. No provider work is replayed.

Before creating or reusing a Take for an interrupted attempt, Generation recovery verifies the artifact's exact persisted size, SHA-256 and Job/Attempt/model/execution-mapping/request/contract provenance against the live canonical file and durable Job. It also consults durable `ProjectUnitOfWork` history for any exact `production.register_take` transaction on that Shot/artifact. If no durable Take registration ever committed, recovery may create the genuinely missing Take. If the original Take committed and the latest durable operation for that transaction is user Undo, recovery preserves that historical `take_id` while leaving current Production Semantics undone; it does not silently create a replacement Take. If registration history says the Take should still exist but it is absent, or the history is ambiguous/malformed, recovery fails closed. If no durable artifact reference exists, orphan generated bytes are quarantined and an abandoned running Job becomes failed/retryable.

Archive export independently validates each Generation ProjectReference against the exact attempt named by that artifact, not blindly against `attempts[-1]`. That artifact-owning attempt must itself be a durable success with the same `output_reference_id` and historical `take_id`. The current Production Semantics must either contain that exact Take bound to the Job's Shot and artifact, or durable ProjectUnitOfWork transaction/operation history must prove that the exact Take was created by `production.register_take` and later intentionally removed by a committed user Undo. This preserves Undo semantics without turning missing/corrupt Production state into a portable success: an out-of-band missing Take, wrong Shot, wrong reference, ambiguous history or later Redo fails closed.

Archive also compares the SHA-256 and size computed from the exact bytes streamed into the ZIP with the persisted Generation artifact digest/size. A changed, truncated or substituted generated file therefore cannot become a successful recovery result or a portable archive merely because it remains non-empty. The same comparison applies when the Generation artifact is absent from current `project.json` only because `generation.register_output` is in the validated Redo suffix: export reconstructs the historical reference from redo snapshots instead of accepting the output by path alone.

`ProjectUnitOfWork` recovery runs before publication reconciliation on application startup so a half-applied prepared Project transaction is rolled back to its exact snapshot before artifact/Take/Job crash state is classified.

Source upload keeps its established execution boundary: request-body streaming/staging remains outside the fence, while final move, FFprobe validation, portable metadata derivation and source registration remain inside it. Because a hard process loss can bypass ordinary exception cleanup after the final move, startup explicitly quarantines an unregistered canonical `sources/src_<uuid>.*` before archive retry. The historical archive-side managed-name detector remains a fail-closed fallback before reconciliation.

These recovery records and quarantine files are coordination/recovery evidence, not a second Project/Production/Generation authority and not user Undo/Redo history. Quarantined crash outputs live at the Project Store root outside canonical project directories and are never silently archived as project state.

## Compatibility debt

Generic compatibility APIs still accept explicit recipe identity and may expose a compatibility `recipe_id` field, but they derive it from the schema-v2 compatibility boundary. Lower Project Store creation no longer supplies an implicit `general_video` default. Modern Studio creation uses the dedicated Production Direction path.

Legacy projects/imports remain readable until migration/caller proof supports removal.

## Portability and security

`ProjectReference.path` is canonical project-relative data. Absolute paths, traversal and symlink escape are rejected; file-consuming operations additionally restrict allowed roots. Project archives use staged validation/integrity checks before atomic import. See `docs/PROJECT_ARCHIVES.md`.
