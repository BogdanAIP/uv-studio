# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen in `review` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The previous frozen review head `e31f42afe652d7238be99388084a81684626fe08` passed post-Ready CI #4265 **5/5**, but its fresh ordinary-ChatGPT semantic review returned three `CURRENT` findings. All three were independently confirmed, PR #89 returned to Draft, and that review/freeze evidence became stale for merge authority.

The three findings are now materially repaired. Exact Draft repair head `1ad82d4c0475eb4fc05ad79ab45ede375601538d` passed authoritative CI #4293 (`33501919168`) **5/5**: `development-context`, both Ubuntu/Windows bootstrap jobs and both Ubuntu/Windows app-baseline jobs all succeeded, including API integration, pinned real-media verification, frontend lint/audit/build and browser Product Truth. The three corresponding GitHub review threads were answered with exact repair/test/CI evidence and resolved before this context-only `draft -> review` freeze.

## Fresh-review repair now frozen

### P1 — durable Generation artifact vs terminal Job state

Generation Job start/succeed/fail/cancel transitions use the same cross-runtime `ProjectTaskRecordStore.project_lock(project_id)` as final publication and archive export. A second runtime cannot interleave a terminal Job mutation after final publication has entered the consequence-bearing fence.

Once the current attempt has a durable Generation ProjectReference, `fail()` and `cancel()` refuse to terminalize it until reconciliation, and retry of a failed current attempt is refused while durable artifact evidence remains pending recovery. Startup reconciliation handles `RUNNING` and can also repair a legacy current-attempt `FAILED`/`CANCELLED` split left by an older implementation without replaying provider execution.

### P1 — exact Generation byte/provenance verification

Before Take creation/reuse or Job success, Generation recovery verifies the durable Job/Attempt/model/capability/offer/adapter/request digest/contract, attempt-derived canonical path, persisted positive `size_bytes`, persisted SHA-256 and the exact live regular-file size/SHA-256.

Archive export independently validates coherent succeeded Job/current-attempt/output/Take/provenance and compares persisted Generation size/SHA-256 with the size/SHA-256 computed from the exact bytes streamed into the ZIP. Changed, truncated or substituted generated media therefore fails closed.

### P2 — source final-move crash recovery

Startup managed-output reconciliation scans `sources/` as well as `artifacts/` and `exports/`. Unregistered self-identifying `sources/src_<uuid>.*` bytes left by hard process loss after source final move are moved to quarantine at the Project Store root; registered source references are preserved. Archive remains fail-closed before reconciliation and can succeed afterward.

The source boundary itself is unchanged: request streaming/staging remains outside the canonical project tree, while final move, FFprobe validation, portable metadata derivation and source registration remain inside the shared project fence.

## Deterministic regression evidence

`tests/test_stage19_fresh_review_repairs.py` covers the exact review failure boundaries:

1. `GenerationService.run()` with simulated Take persistence failure after durable artifact registration remains recoverable and reconciles to the same artifact/Take/Job success without provider replay;
2. a legacy current-attempt terminal split with durable artifact blocks retry until reconciliation and then recovers to success;
3. cross-runtime cancel blocks behind the Generation publication fence and cannot split a successful publication;
4. same-size changed Generation bytes are rejected by startup recovery;
5. mismatched persisted Generation request provenance is rejected;
6. changed bytes of an already succeeded Generation artifact are rejected during archive export;
7. an unregistered `sources/src_<uuid>` crash orphan blocks archive before recovery, is quarantined on restart and no longer blocks archive afterward.

Existing artifact-only and artifact+Take recovery fixtures carry the same durable size/digest/provenance shape written by `GenerationService`.

## Previously repaired Stage-19 behavior retained

The frozen repair preserves:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejection of raw schema-v1 `project.json`, while historical schema-v1 undo/redo migrates only for validation and restores exact recorded bytes;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exclusion and symlink fail-closed behavior;
- arbitrary-path `timeline.assemble` durable publication markers and crash quarantine;
- WebVTT `sub_<uuid>` orphan quarantine;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair.

## Verification history

- Material repair commits: `11563cac943402c3c3a8df1475083b1eb94ede4e`, `27a672121db2144efc39fe416451f9f6f8dd03d9`, `497f30230fcd061f99d83522c6be7fdd06361776`.
- Focused fresh-review regressions: `c93bac4a02889083d501148fff915fbb957a4c1f`.
- Recovery fixture alignment through `4948ea7d5b8545874e887c2559677092a17a4397`.
- Final Draft runtime/test/docs head `1ad82d4c0475eb4fc05ad79ab45ede375601538d`: CI #4293 (`33501919168`) **5/5 SUCCESS**.
- All inline review threads resolved before refreeze.

## Current review gate

Lifecycle is now `review`; no further material/runtime/test edits are authorized on this frozen branch unless a later confirmed finding first returns the slice to `draft`.

Next required sequence:

1. return PR #89 from Draft to Ready without changing this frozen head;
2. require authoritative post-Ready exact-head CI **5/5**;
3. re-resolve live base/head identity and verify zero unresolved review threads;
4. run a completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved. Lifecycle closure remains a separate follow-up after merge.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
