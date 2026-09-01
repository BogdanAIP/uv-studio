# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The third repair had been frozen at `5336999067b19fb0b692d6d41cf5f94958be56a1` and passed post-Ready CI #4339 **5/5**, but a fresh inline P2 then identified a remaining hard-crash recovery gap for still-mounted legacy `art_<uuid>.mp4` publishers. PR #89 was returned to Draft and the prior freeze/CI evidence is stale for merge authority.

## Fourth review repair in progress

### P2 — recover crash-left legacy `art_<uuid>.mp4` outputs

`audio_visualizer.py` and `music_video_render.py` both materialize final files directly as `artifacts/art_<32-hex>.mp4` before registering the owning `ProjectReference`. A hard process loss in that gap leaves canonical bytes without metadata. Archive correctly rejects those bytes as unpublished managed media, but the prior startup filename recovery recognized only `src_`, `sub_`, and `generated_attempt_`, so restart could not unblock export.

Material repair `205731cf8dbe24b09aeb29599674ebbb06d19521` extends startup recovery to the legacy `art_` identity. Regression commit `3d7b9ef8cea0b54c2cb5ee58603e9aca4e1634da` proves an unregistered crash-left legacy artifact is quarantined outside the project and export succeeds after restart, while a registered `art_` artifact and a near-miss ordinary file remain untouched.

The exact repair boundary is being re-checked against the two live producers before the fourth repair is accepted; both producers currently generate `artifacts/art_<32-hex>.mp4`.

## Third review repair retained

### P2 — managed publication recovery matches reference identity

`tasks/pub_<uuid>.json` markers persist both canonical `relative_path` and expected `reference_id`. Recovery treats a pending marker as already completed only when a registered Project source/artifact matches both that path and the marker identity. Reused-path/different-reference crash-left bytes are quarantined outside the project before the marker is cleared.

Deterministic regression: `tests/test_project_publication_recovery.py::test_recovery_quarantines_bytes_when_same_path_has_different_reference`.

### P2 — Generation recovery preserves explicit Take Undo

Generation recovery consults durable `ProjectUnitOfWork` transaction/operation journals before creating a missing Take for an artifact-owning non-succeeded attempt. If the original Take was committed and the latest durable operation is Undo, recovery preserves the historical `take_id`, leaves current Production Semantics undone and reconciles without provider replay or replacement Take creation.

Deterministic regression: `tests/test_generation_recovery.py::test_restart_preserves_explicit_undo_of_existing_take`.

## Previous Stage-19 invariants retained

The repair preserves:

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
- Third repair material/test head `fe2afbd7681ae06317941ba988e61c224227a619`: CI #4331 **5/5**.
- Final third-repair Draft head `1f9504f4d9391901f4f8e8386a7b412a0e0ba2e7`: CI #4336 **5/5**.
- Frozen third-repair head `5336999067b19fb0b692d6d41cf5f94958be56a1`: post-Ready CI #4339 **5/5**, then one confirmed P2 finding for legacy `art_` crash recovery.
- `205731cf8dbe24b09aeb29599674ebbb06d19521`: legacy `art_` startup recovery repair.
- `3d7b9ef8cea0b54c2cb5ee58603e9aca4e1634da`: deterministic legacy `art_` recovery/boundary regressions; CI #4344 started on this material/test head.

## Current repair gate

Lifecycle is `draft`. The fourth-repair material/test CI and exact recovery boundary must be accepted before the open P2 thread can be resolved or the branch can be refrozen.

Next required sequence:

1. finish the exact legacy `art_` recovery boundary and deterministic regression coverage;
2. require exact Draft material/test CI **5/5**;
3. synchronize current Project/PR context with the fourth repair and require final exact Draft-head CI **5/5**;
4. reply to and resolve the remaining P2 review thread with exact repair/test/CI evidence;
5. verify zero unresolved review threads;
6. perform one context-only `draft -> review` refreeze;
7. return PR #89 to Ready without changing the frozen head;
8. require authoritative post-Ready exact-head CI **5/5**;
9. re-resolve live base/head/thread identity and run another completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved. Lifecycle closure remains a separate follow-up after merge.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
