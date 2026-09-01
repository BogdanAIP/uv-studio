# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The previously accepted material implementation head `6f348633c7091c747062c1e3b18b05fbfeb83e1b` passed CI #4191 5/5. Its context-only frozen head `2740c00b953d2a816bec3dfb52572289b221c4fa` also passed authoritative post-Ready CI #4195 5/5. Those green runs no longer authorize review or merge: inspection of unresolved review threads on the frozen head found another reachable P2 archive/publication race. The development context independently classified that thread **CONFIRMED**, and lifecycle/PR returned to Draft before any further material repair.

The surviving P2 is concrete on two supported publishers. `WebVTTSubtitleAdapter` writes `artifacts/sub_<uuid>.vtt` before registering its `ProjectReference`, while `GenerationService.run` gives its executor the canonical `artifacts/generated_<attempt>.*` destination and registers the generated artifact only after the executor returns. Neither publisher participates in the shared archive project fence during byte publication. The archive fallback currently recognizes only unregistered UUID-like `src_`, `art_` and `aud_` names, so `sub_` and `generated_` can be captured with frozen metadata that does not yet contain their canonical identities.

This Draft repair is intentionally narrow. Current supported subtitle/generation publishers will be staged outside every canonical project directory and will publish final bytes plus metadata under the shared project fence, rather than broadening basename heuristics and continuing to rely on filename conventions.

## Implementation boundary

This slice remains bounded to the D-070 Project identity/schema compatibility and recovery boundary:

- canonical Project schema v2 with schema-v1 project/archive readability;
- explicit legacy recipe compatibility identity rather than fake modern Production Direction identity;
- stable project/source/artifact/media/Timeline identities across migration and archive round trips;
- durable schema-v1 ProjectUnitOfWork undo/redo;
- one recoverable archive state under concurrent Project mutation and media publication;
- fail-closed archive symlink safety with only the ordinary technical task-record lock excluded from portable payload.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain outside this slice.

## Existing compatibility and recovery work

`ProjectStore` routes loaded JSON through `migrate_project_data`; schema v2 keeps legacy recipe information in compatibility state. Current direct compatibility readers use the explicit accessor, while historical v1 bytes remain readable and exact transaction snapshots remain authoritative for undo/redo.

Archive import validates the manifest against the raw archived Project schema before migration. Export holds `ProjectTaskRecordStore.project_lock` while freezing Project metadata and enumerating the project tree. The technical `tasks/.uv-task-records.lock` remains non-portable only when it is an ordinary file; symlink occupancy fails closed.

Source upload stages incomplete request bytes outside every canonical project directory and publishes final source bytes plus metadata under the shared project fence. Accepted archive files are streamed once into ZIP while manifest size/SHA-256 are computed from the exact bytes written into the archive.

The archive UUID-name guard remains only a fallback for historical publishers: unregistered managed `src_` / `art_` / `aud_` names under managed roots fail closed, while ordinary user/unmanaged files remain portable. It is not sufficient authority for current publishers whose canonical filenames use other conventions.

`timeline.assemble` already follows the stronger current-publisher pattern: ffconcat manifest and completed FFmpeg output are staged at the Project Store root outside every canonical project directory. After FFmpeg succeeds, the adapter acquires the shared project fence, revalidates the caller-selected destination, atomically moves staged output to the canonical path, and registers the separately allocated `art_<uuid>` reference before releasing the fence. Its deterministic archive-concurrency regression proves the first archive sees neither bytes nor reference while publication is waiting on the fence, and a later archive/import preserves both exact bytes and identity.

## Production-form acceptance repair

The earlier fresh semantic review at `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` returned two P2 findings; both remain materially repaired.

The first exposed arbitrary `timeline.assemble` publication outside the archive fence and led to the staged/fenced publication path above. The second found that permanent browser tests waited for a stale DOM element to disconnect, masking a real user-visible Production form remount race. Production UI was fixed instead of weakening acceptance: the Production panel no longer remounts on history cursor changes, internal command refreshes no longer trigger a duplicate delayed child reload that can erase unsaved form input, and external Undo/Redo uses a monotonic semantics refresh revision so returning to an old numeric history cursor still reloads canonical state.

The permanent Product Truth tests again perform the immediate visible user sequence without internal DOM synchronization. CI #4191 passed the repaired named-generation Undo and micro-drama workflows on Ubuntu and Windows.

## Current repair target

The new confirmed P2 broadens the publication audit from `timeline.assemble` to two additional current supported publishers:

1. `WebVTTSubtitleAdapter`: render bytes may be prepared freely, but canonical `artifacts/sub_<uuid>.vtt` must not appear until the publisher owns the shared project fence; final move and reference registration must complete inside that fence with fail-safe cleanup.
2. `GenerationService.run`: long-running executor work must occur against a staging path outside the canonical project tree; after successful validation, canonical `artifacts/generated_<attempt>.*` publication, artifact registration, Take registration and durable job success must remain coherent with the shared project fence and existing transaction semantics.

Focused regressions must reproduce archive overlap deterministically, proving an archive holding the fence cannot capture staged bytes without their metadata, while a later archive/import preserves the exact published identity/path/bytes. Existing generation recovery, cancellation, idempotency, authorization and Product Truth behavior must remain intact.

## Review and verification

Lifecycle is `draft`. All reviews and CI evidence tied to earlier frozen heads are stale for merge authority after this confirmed material defect. After the subtitle/generation publication repair, focused tests and a new exact material-head CI 5/5 are required. Only then may the context be frozen `draft -> review`, the PR returned to Ready, authoritative frozen-head CI rerun, unresolved threads cleared, and a new fresh ordinary-ChatGPT semantic review under the BASE `code-review` v1.0 policy be requested.
