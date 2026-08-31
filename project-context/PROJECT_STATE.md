# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `87a018abebea1dbcd5959921603b53305b02d5f5` passed exact-head CI run #4150 **5/5**, but its required fresh ordinary-ChatGPT semantic review reported one surviving P2 recovery/concurrency finding. The development context independently classified it **CONFIRMED**: existing media publishers can create UV-owned `art_`/`aud_` bytes inside canonical project roots before their Project-reference transaction acquires the archive snapshot fence. The old export could therefore freeze split metadata/filesystem state, and its separate hash and ZIP reads could observe different live bytes.

That review on `87a018abebea1dbcd5959921603b53305b02d5f5` is stale. PR #89 was returned to draft before material recovery changes. Read-only falsification found the same historical publication pattern beyond the two examples named by the reviewer, including additional render and prepared-audio paths, so Stage 19 hardened the recovery boundary itself rather than expanding into a broad renderer rewrite.

Current implementation head `6890ad79f0598d701881ebe264674d5d5c606891` contains the completed recovery fix and regression coverage. Exact implementation-head CI runs #4161 and #4162 both completed successfully with all five permanent checks green. This context-only transition freezes that implementation for a new exact-head review cycle; no further material changes are permitted while lifecycle state remains `review`.

## Implementation boundary

This slice remains bounded to the D-070 Project identity/schema compatibility and recovery boundary:

- canonical Project schema v2 with schema-v1 project/archive readability;
- explicit legacy recipe compatibility identity rather than fake modern Production Direction identity;
- stable project/source/artifact/media/Timeline identities across migration and archive round trips;
- durable schema-v1 ProjectUnitOfWork undo/redo;
- one recoverable archive state under concurrent Project mutation and media publication;
- fail-closed archive symlink safety with only the ordinary technical task-record lock excluded from portable payload.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain outside this slice.

## Implemented compatibility and recovery boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`; schema v2 keeps legacy recipe information in compatibility state. Current direct compatibility readers use the explicit accessor, while historical v1 bytes remain readable and exact transaction snapshots remain authoritative for undo/redo.

Archive import validates the manifest against the raw archived Project schema before migration. Export holds `ProjectTaskRecordStore.project_lock` while freezing Project metadata and enumerating the project tree. The technical `tasks/.uv-task-records.lock` remains non-portable only when it is an ordinary file; symlink occupancy still fails closed.

Source upload proactively stages incomplete request bytes outside every canonical project directory and publishes final source bytes plus metadata under the shared project fence.

For older publishers that still materialize unique media bytes before metadata registration, export checks enumerated managed media roots against the frozen Project references. A UV-owned UUID publication name beginning `src_`, `art_` or `aud_` that is present under `sources/`, `assets/`, `artifacts/` or `exports/` but absent from frozen Project metadata makes export fail closed and commit no archive. Hidden derivative upload names are covered by the same rule. Ordinary unregistered files with non-managed names remain portable.

Accepted project files are streamed once into the ZIP while size and SHA-256 are computed from that same captured byte stream. The manifest therefore describes the exact bytes written to the archive rather than a prior live-file read.

## Acceptance synchronization

Implementation head `6890ad79f0598d701881ebe264674d5d5c606891` passed required CI twice: runs #4161 and #4162 are both **5/5** green.

Focused regression coverage in `tests/test_project_archive_publication_race.py` proves that arbitrary unregistered project files remain portable while final/hidden UV-owned managed publication names fail closed; export hashes the exact bytes written to ZIP rather than pre-hashing live files; and when export owns the fence while an unfenced legacy publisher creates an artifact before metadata registration, export commits no archive, metadata completes after fence release, and a retry round-trips the registered reference and exact artifact bytes.

## Review and verification

Lifecycle is now `review`. The branch is frozen except for an explicit return to `draft` if new material findings require changes. PR #89 must be non-draft, the new context-only exact head must pass all five declared checks, existing review threads must remain resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0 must report zero surviving findings. Any later material change invalidates that review.
