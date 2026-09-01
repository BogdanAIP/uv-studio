# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen review head `e31f42afe652d7238be99388084a81684626fe08` passed post-Ready CI #4265 **5/5**, but a fresh ordinary-ChatGPT semantic review returned three `CURRENT` findings. Development-context independently confirmed all three. That review/freeze evidence is stale for merge authority. The three findings have now been materially repaired in Draft; another exact-head Draft CI, refreeze, post-Ready CI and completely fresh semantic review are still required.

## Fresh-review repair now implemented

### P1 — durable Generation artifact vs terminal Job state

Generation Job start/succeed/fail/cancel transitions now use the same cross-runtime `ProjectTaskRecordStore.project_lock(project_id)` as final publication and archive export. A second runtime can still cancel/fail work during provider execution, but it cannot interleave a terminal Job mutation after final publication has entered the consequence-bearing fence.

Once the current attempt has a durable Generation ProjectReference, `fail()` and `cancel()` refuse to terminalize that attempt until reconciliation. A local `register_take()` or Job-success persistence exception after artifact commit therefore leaves the Job recoverable instead of stranding the artifact behind `FAILED`. Retry of a failed current attempt is also refused while it has durable artifact evidence pending recovery.

Startup reconciliation now handles the current attempt when the Job is `RUNNING` and also repairs a legacy current-attempt `FAILED`/`CANCELLED` split state produced by an older implementation. It reuses/creates the matching Take and records success only from proven durable materialization; provider execution is never replayed.

### P1 — exact Generation byte/provenance verification

Generation recovery no longer treats a merely non-empty file as success evidence. Before Take creation/reuse or Job success, it verifies:

- ProjectReference Generation `job_id` and current `attempt_id`;
- model identity;
- capability/offer/adapter execution mapping;
- request digest;
- generation contract;
- attempt-derived canonical output name;
- persisted positive `size_bytes`;
- persisted lowercase SHA-256;
- live regular non-symlink file size and SHA-256 exactly matching those persisted values.

Archive export independently revalidates the matching succeeded Job/current attempt/output/Take/provenance and compares each Generation artifact's persisted size/SHA-256 with the size/SHA-256 computed from the **exact bytes streamed into the ZIP**. Changed/truncated/substituted generated media therefore fails closed instead of becoming a successful recovery result or internally self-consistent but semantically corrupted archive.

### P2 — source final-move crash recovery

Startup managed-output reconciliation now scans `sources/` as well as `artifacts/` and `exports/`. Unregistered self-identifying `sources/src_<uuid>.*` bytes left by hard process loss after source final move are moved to quarantine at the Project Store root. Registered source references are preserved. Archive remains fail-closed before reconciliation and succeeds after the orphan has been removed from canonical project state.

The source execution boundary is unchanged: request streaming/staging remains outside the canonical project tree; final move, FFprobe validation, portable metadata derivation and source registration remain inside the shared project fence.

## New deterministic regressions

`tests/test_stage19_fresh_review_repairs.py` covers the exact fresh-review failure boundaries:

1. real `GenerationService.run()` with a simulated Take persistence failure after durable artifact registration leaves the Job `RUNNING`, blocks archive before recovery, then recovers to the same artifact/Take/Job success without provider replay;
2. a legacy current-attempt `FAILED` split with durable artifact blocks retry until startup reconciliation and then recovers to success;
3. a second runtime's cancel call blocks behind the Generation publication fence and, after the publishing runtime succeeds, fails with `GenerationJobConflict` instead of splitting state;
4. same-size changed Generation bytes are rejected by startup recovery;
5. mismatched persisted Generation request provenance is rejected by startup recovery;
6. changed bytes of an already succeeded Generation artifact are rejected while archive streams the exact ZIP bytes;
7. an unregistered `sources/src_<uuid>` crash orphan blocks archive before recovery, is quarantined on restart, and no longer blocks archive afterward.

Existing artifact-only and artifact+Take recovery fixtures were updated to carry the same full durable size/digest/provenance shape written by `GenerationService`, so older recovery regressions continue to test real canonical evidence rather than an artificially incomplete fixture.

## Previously repaired Stage-19 behavior retained

The current repair preserves:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejection of raw schema-v1 `project.json`, while historical schema-v1 undo/redo migrates only for validation and restores exact recorded bytes;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exclusion and symlink fail-closed behavior;
- arbitrary-path `timeline.assemble` durable publication markers and crash quarantine;
- WebVTT `sub_<uuid>` orphan quarantine;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair.

## Verification history

- Prior frozen review head `a0974c73fcf48c409c07d7e456b78315544b4018`: stale after two confirmed findings.
- Material repair head `a31f9cfd2dc1d16e1ea940c5c3d62542f6780e5f`: CI #4255 **5/5 SUCCESS**.
- Focused crash-boundary tests added through `5ad22668038870c019961536530b3f3a8ce7a78b`.
- Draft material/docs head `6a3fa91ee1acb3ab52d5c28bc5ea3a7b2d765411`: CI #4261 and #4262 **5/5 SUCCESS**.
- Frozen head `e31f42afe652d7238be99388084a81684626fe08`: post-Ready CI #4265 **5/5 SUCCESS**, then fresh review returned three confirmed findings.
- Fresh-review repair commits include `11563cac943402c3c3a8df1475083b1eb94ede4e` (cross-runtime Generation Job fencing), `27a672121db2144efc39fe416451f9f6f8dd03d9` (verified Generation/source restart reconciliation), `497f30230fcd061f99d83522c6be7fdd06361776` (exact Generation archive digest/provenance), and `c93bac4a02889083d501148fff915fbb957a4c1f` (focused fresh-review regressions).
- First repair CI on `c93bac4...` exposed only three old incomplete Generation test fixtures; all seven new fresh-review regression tests were already green. Fixtures were aligned with real durable provenance through `4948ea7d5b8545874e887c2559677092a17a4397`; Ubuntu bootstrap on CI #4284 is green and Windows/app-baseline were still running when documentation synchronization began.

## Current repair gate

Lifecycle remains `draft`. Runtime/test repair is complete; Project Store/archive/current-state documentation is synchronized with the actual repaired semantics. The next authoritative gate is all five required CI jobs on the final exact Draft documentation-sync head.

After exact Draft-head CI is **5/5**:

1. reply to each of the three fresh-review GitHub threads with exact repair/test/CI evidence and resolve only after validation;
2. perform one context-only `draft -> review` freeze;
3. return PR #89 to Ready without changing the frozen head;
4. require authoritative post-Ready exact-head CI **5/5**;
5. verify no unresolved review threads;
6. run a completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
