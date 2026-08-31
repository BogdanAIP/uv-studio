# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in implementation/draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `87a018abebea1dbcd5959921603b53305b02d5f5` passed exact-head CI run #4150 **5/5**, but its required fresh ordinary-ChatGPT semantic review reported one surviving P2 recovery/concurrency finding. The development context independently classified it **CONFIRMED**: existing media publishers can create UV-owned `art_`/`aud_` bytes inside canonical project roots before their Project-reference transaction acquires the archive snapshot fence. The old export could therefore freeze split metadata/filesystem state, and its separate hash and ZIP reads could observe different live bytes.

The review on `87a018abebea1dbcd5959921603b53305b02d5f5` is stale. PR #89 is draft. Read-only falsification found the same historical publication pattern beyond the two examples named by the reviewer, including additional render and prepared-audio paths. Stage 19 therefore hardens the recovery boundary itself rather than expanding into a broad renderer rewrite.

Current implementation head `f7a598af298e9a61b21a72b7262b630c0ef9c6d2` makes archive export fail closed around incomplete UV-owned media publication and computes manifest size/SHA from the exact bytes streamed into the ZIP. Focused hosted verification is now required before another review freeze.

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

For older publishers that still materialize unique media bytes before metadata registration, export now checks enumerated managed media roots against the frozen Project references. A UV-owned UUID publication name beginning `src_`, `art_` or `aud_` that is present under `sources/`, `assets/`, `artifacts/` or `exports/` but absent from frozen Project metadata makes export fail closed and commit no archive. Hidden derivative upload names are covered by the same rule. Ordinary unregistered files with non-managed names remain portable.

Accepted project files are now streamed once into the ZIP while size and SHA-256 are computed from that same stream. The manifest therefore describes the exact captured ZIP bytes rather than a prior live-file read.

## Acceptance synchronization

The previous frozen head `87a018abebea1dbcd5959921603b53305b02d5f5` passed CI #4150 **5/5**, but that evidence is stale for merge after the material recovery fix.

The new focused regression test pauses export after the snapshot fence is acquired, lets an unfenced legacy publisher create a UV-owned artifact and block on metadata registration, requires export to fail without committing a ZIP, then verifies publication completes after fence release and a retry round-trips both the artifact reference and exact bytes. It also proves arbitrary unregistered files remain portable while final/hidden UV-owned managed publication names fail closed.

## Review and verification

This material recovery/concurrency change remains in `draft` until the new implementation head passes required CI. Then context must return to `review`, the PR must be non-draft, the new exact head must pass all five declared checks, existing review threads must remain resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0 must report zero surviving findings. Any later material change invalidates that review.
