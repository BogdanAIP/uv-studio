# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The accepted material implementation head is `6f348633c7091c747062c1e3b18b05fbfeb83e1b`. Exact-head CI #4191 (run `33414854256`) passed all five required checks: `development-context`, Ubuntu/Windows bootstrap, and Ubuntu/Windows app-baseline. Both app-baseline jobs passed API integration, real-media verification, frontend lint/audit/build and the permanent Stage 4C + Stage 5 browser Product Truth suite.

The earlier frozen head `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` passed CI #4165 but its required fresh ordinary-ChatGPT review returned two surviving P2 findings. The development context independently classified both findings **CONFIRMED**, returned lifecycle/PR to Draft, and repaired them materially. That old review is stale and cannot authorize merge.

This context-only freeze moves lifecycle `draft -> review` after the repaired material head passed exact-head CI. PR #89 must become GitHub Ready without changing this frozen head; the final frozen head then requires authoritative **5/5** CI and a new fresh ordinary-ChatGPT semantic review under the BASE `code-review` v1.0 policy before merge.

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

The regression `test_timeline_assemble_stages_arbitrary_output_until_archive_fence_releases` freezes an export while it owns the project fence, lets `timeline.assemble` finish FFmpeg staging, proves `artifacts/joined.mp4` is still absent from the canonical project while assembly is blocked, then releases export. The first archive contains neither the arbitrary output nor its future ProjectReference; assembly then publishes both, and a retry archive/import preserves the same `art_<uuid>` identity, canonical path and bytes.

## Production-form acceptance repair

The confirmed browser finding exposed a real same-project form race rather than a test-only synchronization issue. `ProductionWorkspacePanel` previously keyed `ProductionSemanticsPanel` by `${projectId}:${history.cursor}`, forcing a React remount whenever history advanced. The permanent browser tests had been waiting for that remount before entering the next field, which masked the actual user-visible race.

The panel is now keyed only by `projectId`, and both Product Truth tests again perform the immediate visible user sequence without waiting for an internal stale DOM node to disconnect.

Removing the remount exposed a second real race: after an internal production command, `ProductionSemanticsPanel.mutate()` reloaded canonical state while the form was busy, but the parent then performed a second delayed history-driven reload after the form became editable. That duplicate reload could overwrite newly entered unsaved fields such as micro-drama story title. The parent now calls `refresh(false)` for an internal production mutation: it refreshes Project/Timeline/History and records the observed durable history cursor without re-signalling the child, because the child has already reloaded its own command result.

A third acceptance edge appeared on Undo. Using the numeric durable history cursor itself as the child refresh signal was insufficient because Undo can return to an older cursor value the child has already seen. `ProductionWorkspacePanel` therefore uses a monotonic `semanticsRefreshRevision` as the child effect token while keeping `observedHistoryCursor` only for durable change detection. Internal production commands update the observed cursor without incrementing the token; a genuinely different external history transition such as Undo/Redo increments the token even when history returns to an old numeric cursor. This preserves unsaved local input across same-project command refreshes while reliably reloading canonical production semantics after external history operations.

CI #4191 proves the repaired behavior on both operating systems. The named-generation outcome creates Scene -> Shot -> generated Take, accepts it into Timeline, performs visible Undo, observes the accepted badge disappear, confirms `accepted_take_id` is cleared while the generated Take/job remains durable, and keeps the generation result visible. The micro-drama outcome also passes its immediate Scene/Shot/Take and story/continuity workflow without remount synchronization.

## Repair sequence and verification

Material repair sequence after the confirmed review findings includes:

- `39611853545ddd7a09b36a1335bd34b1d1d9e00c` — scope the production-form repair path;
- `2e7382c2d1edb59bd4c6b00a47912c9f71c91a8e` — preserve Production form input across history refresh;
- `9f571ec464b043399ce6b205753aebc8a1b2eab0` — restore immediate named-generation user outcome;
- `1fa7433ad78a3582bea6c0bdf70757d9e17dd543` — restore immediate micro-drama user outcome;
- `3d58f2c4c239b241371ac388c9cacecc8de1d088` — stage arbitrary timeline assembly output and publish bytes/reference under the shared project fence;
- `8d3ccf0f212c3b1bf6c2ecbab5cbd19744dfb694` — deterministic archive-versus-`timeline.assemble` regression;
- `9d5a069c5018a452e2e5d3b2ce1c7a3c36bfe55e` — synchronize archive recovery documentation with the two publication mechanisms;
- `64883907a4fbe6cb2f0dd5f129cb69a541be4e56` — remove the history-cursor remount from the Production workspace;
- `ab871417ba2f386b3731eab2d6de2ae5a3184abf` — suppress the duplicate delayed child reload after internal production mutations;
- `6f348633c7091c747062c1e3b18b05fbfeb83e1b` — use a monotonic semantics refresh revision so external Undo/Redo cannot be lost when history returns to an old cursor value.

CI #4189 on `ab871417ba2f386b3731eab2d6de2ae5a3184abf` was intentionally treated as a failed acceptance cycle: both operating systems reproduced the same named-generation Undo UI failure while the micro-drama outcome already passed. The final material fix at `6f348633c7091c747062c1e3b18b05fbfeb83e1b` then passed exact-head CI #4191 **5/5**, including the browser suite on Ubuntu and Windows.

## Review and verification

Lifecycle is now `review`. Both P2 findings from the stale review at `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` are materially repaired and exact-head hosted CI is green on the accepted implementation head. No earlier semantic review may be reused. The final context-only frozen head must remain unchanged while PR #89 becomes Ready, pass authoritative exact-head CI **5/5**, and receive a new fresh ordinary-ChatGPT semantic review with no surviving findings before merge.
