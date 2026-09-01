# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `eaee4f1518638baaf8b4247e25183f2df1d70059` passed authoritative post-Ready CI #4321 (`33515948282`) **5/5**, but two new inline P2 findings appeared before a fresh semantic review was launched. Both were independently confirmed, PR #89 returned to Draft, and that freeze/CI evidence became stale for merge authority.

The third repair is now materially complete. Exact material/test head `fe2afbd7681ae06317941ba988e61c224227a619` passed CI #4331 (`33523018672`) **5/5** on Ubuntu and Windows: `development-context`, both bootstrap unit suites and both app-baseline jobs all succeeded, including API integration, HTTP probe, pinned real-media verification, frontend lint/audit/build and browser Product Truth. `docs/PROJECT_ARCHIVES.md` and `docs/PROJECT_STORE.md` are synchronized after that material gate. A final exact Draft docs/context head CI remains required after canonical PR-body synchronization.

## Third review repair

### P2 — managed publication recovery now matches reference identity

`tasks/pub_<uuid>.json` markers persist both canonical `relative_path` and expected `reference_id`. Recovery now indexes registered Project sources/artifacts by path and treats a marker as already canonical only when the marker's expected identity is present at that exact path.

A dangling or historical ProjectReference that merely reuses the same path can no longer claim new crash-left bytes for a different publication. If the marker identity does not match the registered identity, materialized interrupted bytes are moved to quarantine outside the canonical project tree before the marker is cleared. Matching path + matching identity retains the canonical bytes and clears only the stale marker. Marker records without a reference identity retain the bounded path-only fallback.

### P2 — Generation recovery now preserves explicit Take Undo

Generation recovery now consults durable `ProjectUnitOfWork` transaction/operation journals before creating a missing Take for an artifact-owning non-succeeded attempt.

If no committed `production.register_take` history exists for that exact Shot/artifact, recovery is at the genuine pre-Take crash boundary and may create the missing Take through the normal Production command. If a matching Take was committed and the latest durable operation for that exact transaction is `undo`, recovery preserves the original historical `take_id`, leaves current Production Semantics in the user's undone state, and reconciles the attempt without provider replay or replacement Take creation. If durable registration history exists but the Take is absent without authoritative latest Undo, or history is unsafe/ambiguous/malformed, recovery fails closed rather than inventing another identity.

A live Take must still belong to the exact Shot/artifact, and any already-persisted attempt `take_id` must agree with the resolved Take authority.

## New deterministic regressions

- `tests/test_project_publication_recovery.py::test_recovery_quarantines_bytes_when_same_path_has_different_reference` constructs an old dangling ProjectReference on a reused path plus a new marker with a different identity and crash-left bytes; recovery quarantines the new bytes, preserves the old reference and clears the marker.
- `tests/test_generation_recovery.py::test_restart_preserves_explicit_undo_of_existing_take` creates a running Generation with exact durable artifact and Take, performs a real global `ProjectUnitOfWork.undo()`, restarts recovery and proves the Job succeeds with the original historical `take_id` while the Production Take remains absent and redo remains available.

Both new regressions run in the permanent Ubuntu and Windows unit suites and passed on CI #4331.

## Previous repair behavior retained

The current repair preserves:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejection of raw schema-v1 `project.json`, while historical schema-v1 undo/redo migrates only for validation and restores exact recorded bytes;
- coherent cross-runtime Generation Job/publication fencing;
- attempt-specific Generation recovery/archive authority across historical multi-attempt states;
- exact Generation byte size/SHA-256 and full Job/Attempt/model/execution/request/contract provenance;
- retry/fail/cancel blocking while any attempt owns unreconciled durable materialization;
- current Production Take authority distinguished from immutable Generation Job Take provenance;
- source `src_<uuid>` hard-crash quarantine;
- arbitrary-path `timeline.assemble` durable publication markers;
- WebVTT `sub_<uuid>` orphan quarantine;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exclusion and symlink fail-closed behavior;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair;
- no provider/renderer replay during recovery.

## Verification history

- Frozen `e31f42afe652d7238be99388084a81684626fe08`: post-Ready CI #4265 **5/5**, then three confirmed findings.
- Draft repair `1ad82d4c0475eb4fc05ad79ab45ede375601538d`: CI #4293 **5/5**.
- Frozen `a6324ec9f4113f62e82e19004a1ab82b276f8b3a`: post-Ready CI #4298 **5/5**, then two confirmed P1 findings.
- Second material/test repair `e037d20c773a141dc24f35369179a581d4081e9c`: CI #4311 **5/5**.
- Final second-repair Draft head `4ef9f2f75497467f4b6ac68fb4b0961deef4fa99`: CI #4318 **5/5**.
- Frozen `eaee4f1518638baaf8b4247e25183f2df1d70059`: post-Ready CI #4321 **5/5**, then two confirmed P2 findings.
- `a47100a2c1d72c49a4392d44adcd504a1cbe605d`: publication recovery requires matching marker path/reference identity.
- `af1c198fed8356b6a80a7518eafa432dbe457af9`: Generation recovery preserves explicit durable Take Undo and fails closed on inconsistent missing-Take history.
- `047da06d3090168983cd60a5cf0cdbfb34ecc5bd`: publication identity regression.
- `fe2afbd7681ae06317941ba988e61c224227a619`: explicit Take Undo regression; material/test CI #4331 **5/5 SUCCESS**.
- `b2f494b6598d0d023ef867f14cb3f1507adf4a9e` and `16f06e259acbbc5b29331f63f510720b8edc0450`: archive/Project Store contract synchronization after the material gate.

## Current repair gate

Lifecycle remains `draft`. Runtime/test behavior is materially green on CI #4331 and documentation is synchronized. The two fresh P2 review threads remain unresolved until the final exact Draft docs/context head passes all five permanent jobs after canonical PR-body synchronization.

Next required sequence:

1. synchronize the canonical PR body to this third repair cycle;
2. require the latest exact Draft-head CI **5/5**;
3. reply to both open P2 review threads with exact repair/test/CI evidence and resolve them only after that gate;
4. verify zero unresolved review threads;
5. perform one context-only `draft -> review` refreeze;
6. return PR #89 to Ready without changing the frozen head;
7. require authoritative post-Ready exact-head CI **5/5**;
8. re-resolve exact live base/head/thread identity and run another completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved. Lifecycle closure remains a separate follow-up after merge.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
