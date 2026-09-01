# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The most recent frozen review head `e31f42afe652d7238be99388084a81684626fe08` passed authoritative post-Ready CI #4265 **5/5**, but a fresh ordinary-ChatGPT semantic review returned three `CURRENT` findings. Development-context independently re-read the exact head and classified all three as `CONFIRMED`. Therefore the review, CI and freeze evidence on `e31f42af...` are stale for merge authority and material repair is authorized only after this `review -> draft` lifecycle transition.

## Current confirmed findings

### P1 — durable Generation artifact can become stranded behind terminal Job state

Generation publication currently commits canonical bytes and ProjectReference before Take and Job success. If `register_take()` or `jobs.succeed()` raises after the artifact is durable, ordinary exception handling preserves the registered artifact but can mark the still-running Job `FAILED`. Separately, Generation Job state mutations still use only the process-local store lock, so another runtime can cancel a Job during the publication critical section. Startup materialization reconciliation currently considers only `RUNNING` Jobs, while archive export rejects generation artifacts whose Job/attempt is not matching `succeeded`; retry also leaves the older artifact bound to an earlier attempt. This can permanently block project export.

Repair requirement: Generation Job state mutations that participate in publication must share the cross-runtime project fence, and a publication failure after a durable artifact boundary must remain recoverable instead of being converted into an unreconcilable terminal state. Recovery must be able to reconcile the durable attempt without provider replay and without rewriting unrelated historical attempts.

### P1 — recovery must verify durable Generation bytes and provenance

Generation artifact metadata already stores `size_bytes`, SHA-256 and generation provenance. `_reconcile_running_materialization()` currently verifies only regular-file/non-empty existence before creating/reusing a Take and marking Job success. A truncated or replaced non-empty file can therefore be promoted to canonical `SUCCEEDED` state, and archive streaming hashes only prove ZIP consistency rather than equality with the original generation digest.

Repair requirement: recovery must verify the exact persisted size/digest and durable generation provenance against the Job/request/attempt before success; archive export must also fail closed if a succeeded generation artifact's live bytes no longer match its persisted generation digest/size.

### P2 — source-upload final-move crash leaves a permanent archive blocker

Source upload intentionally stages request bytes outside the project and keeps final move + FFprobe + metadata registration inside the shared project fence. A hard process loss after `os.replace()` and before source registration leaves `sources/src_<uuid>...` canonical but unregistered. Archive export correctly rejects that managed orphan, but current startup publication recovery scans only `artifacts/` and `exports/`, so restart does not reconcile the source orphan.

Repair requirement: startup reconciliation must recognize unregistered canonical `sources/src_<uuid>...` outputs, move them outside the project tree without deleting evidence, and leave registered source references untouched. Archive remains fail-closed before reconciliation.

## Previously repaired Stage-19 findings retained

The current repair must preserve all earlier accepted behavior:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejects raw schema-v1 `project.json`, while historical schema-v1 undo/redo migrates only for validation and restores exact recorded bytes;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exclusion and symlink fail-closed behavior;
- `timeline.assemble` arbitrary-path durable publication markers and crash quarantine;
- WebVTT `sub_<uuid>` orphan quarantine;
- source request streaming/staging outside the canonical project tree with FFprobe deliberately inside the publication fence;
- Generation bytes-only/artifact-only/artifact+Take restart semantics without provider replay;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair.

## Verification history

- Prior frozen review head `a0974c73fcf48c409c07d7e456b78315544b4018`: stale after two confirmed findings.
- Material repair head `a31f9cfd2dc1d16e1ea940c5c3d62542f6780e5f`: CI #4255 **5/5 SUCCESS**.
- Focused crash-boundary tests added through `5ad22668038870c019961536530b3f3a8ce7a78b`.
- Draft material/docs head `6a3fa91ee1acb3ab52d5c28bc5ea3a7b2d765411`: CI #4261 and #4262 **5/5 SUCCESS**.
- Frozen head `e31f42afe652d7238be99388084a81684626fe08`: post-Ready CI #4265 **5/5 SUCCESS**, then fresh review returned the three confirmed findings above.

## Current repair gate

Lifecycle is `draft`. Material edits may proceed only within `ACTIVE_SLICE.write_scope`.

Before another review freeze:

1. repair all three confirmed findings;
2. add deterministic regressions for local Take/Job failure after durable artifact publication, cross-runtime cancellation, digest/provenance mismatch and crash-left source bytes;
3. prove archive fail-closed before recovery and successful/clean state after recovery where applicable;
4. pass all five required exact-head Draft CI jobs;
5. synchronize Project Store/archive/current-state documentation with the actual repaired semantics;
6. perform one context-only `draft -> review` freeze, return PR #89 to Ready without changing that head, and require authoritative post-Ready exact-head CI 5/5;
7. run a completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
