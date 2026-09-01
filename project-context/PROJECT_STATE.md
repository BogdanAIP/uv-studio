# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen in `review` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The third repair is complete. Exact material/test head `fe2afbd7681ae06317941ba988e61c224227a619` passed CI #4331 (`33523018672`) **5/5** on Ubuntu and Windows. Final Draft docs/context head `1f9504f4d9391901f4f8e8386a7b412a0e0ba2e7` then passed authoritative post-body-sync CI #4336 (`33524495361`) **5/5**: `development-context`, both Ubuntu/Windows bootstrap jobs and both Ubuntu/Windows app-baseline jobs all succeeded, including full unit suites, API integration, HTTP probe, pinned real-media verification, frontend lint/audit/build and browser Product Truth.

The two P2 inline review threads discovered on the previous frozen head were answered with exact repair/test/CI evidence and resolved after CI #4336. There are now zero unresolved review threads before this context-only `draft -> review` refreeze.

## Third review repair now frozen

### P2 — managed publication recovery matches reference identity

`tasks/pub_<uuid>.json` markers persist both canonical `relative_path` and expected `reference_id`. Recovery treats a pending marker as already completed only when a registered Project source/artifact matches both that path and the marker identity.

A dangling or historical ProjectReference that merely reuses the same path can no longer claim new crash-left bytes for a different publication. If the marker identity does not match the registered identity, materialized interrupted bytes are moved to quarantine outside the canonical project tree before the marker is cleared. Matching path + matching identity retains canonical bytes and clears only the stale marker.

Deterministic regression: `tests/test_project_publication_recovery.py::test_recovery_quarantines_bytes_when_same_path_has_different_reference`.

### P2 — Generation recovery preserves explicit Take Undo

Generation recovery consults durable `ProjectUnitOfWork` transaction/operation journals before creating a missing Take for an artifact-owning non-succeeded attempt.

If no committed `production.register_take` history exists for the exact Shot/artifact, recovery is at the genuine pre-Take crash boundary and may create the missing Take through the normal Production command. If a matching Take committed and the latest durable operation for that exact transaction is `undo`, recovery preserves the original historical `take_id`, leaves current Production Semantics in the user's undone state, and reconciles the attempt without provider replay or replacement Take creation. Missing Take state with registration history but without authoritative latest Undo fails closed.

A live Take must still belong to the exact Shot/artifact, and any already-persisted attempt `take_id` must agree with the resolved authority.

Deterministic regression: `tests/test_generation_recovery.py::test_restart_preserves_explicit_undo_of_existing_take`.

## Previous Stage-19 invariants retained

The frozen repair preserves:

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
- `a47100a2c1d72c49a4392d44adcd504a1cbe605d`: managed-publication recovery requires exact path/reference identity.
- `af1c198fed8356b6a80a7518eafa432dbe457af9`: Generation recovery preserves explicit durable Take Undo and fails closed on inconsistent missing-Take history.
- `047da06d3090168983cd60a5cf0cdbfb34ecc5bd`: publication identity regression.
- `fe2afbd7681ae06317941ba988e61c224227a619`: explicit Take Undo regression; material/test CI #4331 **5/5 SUCCESS**.
- `1f9504f4d9391901f4f8e8386a7b412a0e0ba2e7`: final Draft docs/context head; authoritative post-body-sync CI #4336 (`33524495361`) **5/5 SUCCESS**.
- Both current P2 review threads resolved after #4336; unresolved thread count was zero before refreeze.

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
