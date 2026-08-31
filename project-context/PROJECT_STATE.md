# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is in implementation/draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Implementation head `6890ad79f0598d701881ebe264674d5d5c606891` passed required CI runs #4161 and #4162 **5/5**. Context-only frozen head `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` then passed exact-head post-Ready CI #4165, but its required fresh ordinary-ChatGPT semantic review returned `FINDINGS` with two surviving P2 findings. The development context independently classified both findings **CONFIRMED**, returned durable lifecycle state to `draft`, and the repository owner converted PR #89 back to GitHub Draft before material repair began. The review on `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` is therefore stale and cannot authorize merge.

Confirmed finding 1: archive recovery hardening recognized incomplete UV-managed publication only from `src_` / `art_` / `aud_` UUID-style basenames. `timeline.assemble` is a supported counterexample because callers may choose an arbitrary canonical output such as `artifacts/joined.mp4`; the old adapter wrote that path before creating its separate `art_<uuid>` ProjectReference and before `update_project()` acquired the shared project fence.

Confirmed finding 2: the permanent browser user-outcome tests in `e2e/test_micro_drama_production_outcome.py` and `e2e/test_named_generation_outcome.py` had been changed only on the test side to wait for an old Shot-intent DOM element to disconnect after Scene creation. That stale-element synchronization deliberately advanced past the known production-form remount window instead of proving the immediate next-user action safe.

Both repairs are now implemented in draft. The current repair series includes the production-form fix, restored immediate-action E2E acceptance, fenced arbitrary-path timeline assembly publication, a deterministic archive/assembly concurrency regression, and synchronized archive documentation. Required hosted CI on the resulting exact implementation head is still pending and must pass before the next review freeze.

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

The archive guard remains a recovery fallback for historical UUID-named UV-owned media publishers: unregistered `src_` / `art_` / `aud_` managed publication names fail closed, while ordinary unregistered files with non-managed names remain portable. Accepted archive files are streamed once into ZIP while manifest size/SHA-256 are computed from the same captured bytes.

`timeline.assemble` no longer relies on that basename heuristic. FFconcat manifest and completed FFmpeg output are staged at the Project Store root, outside every canonical project directory. After FFmpeg succeeds, the adapter acquires the shared project fence, revalidates that the caller-selected destination is absent, atomically moves the staged output to that exact canonical path, and registers the separately allocated `art_<uuid>` ProjectReference before releasing the fence. Rollback removes published bytes when metadata definitely did not commit, while preserving bytes if durable metadata cannot be read after a possible commit.

The concurrency regression `test_timeline_assemble_stages_arbitrary_output_until_archive_fence_releases` freezes an export while it owns the project fence, lets `timeline.assemble` finish FFmpeg staging, proves `artifacts/joined.mp4` is still absent from the canonical project while assembly is blocked, then releases export. The first archive contains neither the arbitrary output nor its future ProjectReference; assembly then publishes both, and a retry archive/import preserves the same `art_<uuid>` identity, canonical path and bytes.

## Production-form acceptance repair

`ProductionWorkspacePanel` previously keyed `ProductionSemanticsPanel` by `${projectId}:${history.cursor}`, forcing a React remount whenever history advanced. The child already observes `historyCursor` and reloads durable production data without requiring a remount, so the changing key unnecessarily destroyed local draft fields such as Shot intent.

The production panel is now keyed only by `projectId`, preserving local input across same-project history refreshes while still allowing the child to reload canonical data through its existing `historyCursor` effect. Both permanent browser user-outcome tests removed the stale DOM disconnect wait and again proceed directly from visible Scene creation to selecting the Scene and entering Shot intent. The acceptance gate therefore exercises the user-visible race window rather than synchronizing around it.

## Repair commits and verification state

Material repair sequence after the confirmed review findings:

- `39611853545ddd7a09b36a1335bd34b1d1d9e00c` — scope the production-form repair path;
- `2e7382c2d1edb59bd4c6b00a47912c9f71c91a8e` — preserve Production form input across history refresh;
- `9f571ec464b043399ce6b205753aebc8a1b2eab0` — restore immediate named-generation user outcome;
- `1fa7433ad78a3582bea6c0bdf70757d9e17dd543` — restore immediate micro-drama user outcome;
- `3d58f2c4c239b241371ac388c9cacecc8de1d088` — stage arbitrary timeline assembly output and publish bytes/reference under the shared project fence;
- `8d3ccf0f212c3b1bf6c2ecbab5cbd19744dfb694` — deterministic archive-versus-`timeline.assemble` regression;
- `9d5a069c5018a452e2e5d3b2ce1c7a3c36bfe55e` — synchronize archive recovery documentation with the two publication mechanisms.

The current draft head after this context update must pass all five required hosted CI checks. Any CI-driven material repair remains draft and invalidates earlier runs. Only after green implementation CI may context transition to `review`; the PR must then become Ready without changing the frozen head, exact-head CI must be **5/5**, and a new fresh ordinary-ChatGPT semantic review under the BASE `code-review` v1.0 policy must return no findings before merge.

## Review and verification

Lifecycle is `draft`. Both P2 findings from the fresh review at `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` are CONFIRMED and have implementation repairs in the current draft series. Those repairs are not accepted until exact-head hosted CI passes and the later frozen head receives a new fresh semantic review. The old semantic review remains evidence for the defects only and cannot be reused for merge.
