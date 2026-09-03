# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `6603e46e932432e52e409a4a9656f5625bd9b540` returned `review_validity=CURRENT`, `status=FINDINGS`, `reported_findings=1`, `rejected_candidates=15`. Exact-head CI #4636 (`33771183215`) passed **5/5 SUCCESS**, but CI does not falsify the reported crash/concurrency interleaving.

The finding is independently **CONFIRMED**. `begin_managed_publication()` creates a new durable `pub_<uuid>` record without checking whether another unresolved marker already reserves the same canonical `relative_path`. `timeline.assemble` renders outside the project lock and only rechecks whether the target file exists before creating that marker. If an older runtime crashes after marker creation but before `os.replace`, a second already-running runtime can create a different marker for the same still-absent path, successfully publish/register its own reference, and clear only its marker. Later recovery of the older marker sees the path owned by a different reference and quarantines the newer valid bytes, leaving the newer ProjectReference dangling.

Existing recovery semantics intentionally quarantine bytes when a marker's expected reference ID differs from the current registered reference for the path; therefore the defect is the missing same-path durable reservation rule, not recovery's mismatch handling.

The prior review of `6603e46...` is merge-stale as soon as the material repair lands. PR #89 and lifecycle were returned to Draft before repair.

## Repair invariant

For managed arbitrary-path publication, a canonical project-relative output path may have at most one unresolved durable publication reservation at a time. The reservation check and marker creation must be atomic under the shared cross-runtime project lock. A later publisher must fail closed while an older marker reserves the same path, even when the canonical target file is still absent. Recovery may then clear an interrupted marker with no materialized bytes without risking a newer publication at the same path.

The existing Generation redo-only retry invariant remains unchanged: every failed-job execution entry point must remain blocked before new provider execution while validated redo-owned materialization is reachable.

## Verification already obtained

Accepted pre-repair evidence includes:

- corrected Draft head `90531357773ba1bc1360a66f7c3c143b56b121c8`, CI #4632 (`33770513959`): **5/5 SUCCESS**;
- frozen review head `6603e46e932432e52e409a4a9656f5625bd9b540`, CI #4636 (`33771183215`): **5/5 SUCCESS**;
- mandatory fresh review on `6603e46...`: `CURRENT / FINDINGS / 1 P1 / 15 rejected candidates`.

## Governed continuation

1. add a regression that reproduces the old-marker/no-bytes + second same-path publication reservation case;
2. repair the shared `begin_managed_publication()` boundary so same-path pending markers conflict atomically under the project lock;
3. run focused tests and full Draft CI;
4. synchronize context and PR body, refreeze `draft -> review`, and obtain a new fresh ordinary-ChatGPT semantic review on the new exact HEAD;
5. after a `CURRENT / PASS / 0 findings` review, obtain the final exact-head permanent CI/browser/real-media acceptance confirmation, re-resolve live identity/threads, and merge with expected HEAD SHA;
6. after merge, perform mandatory D-038 lifecycle closure to `idle`.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
