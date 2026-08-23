# Project State

<!-- uv-context-state: idle -->
<!-- uv-active-slice: none -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **idle** after completion of `product-recovery-dubbing-orchestration` in PR #47.

PR #47 merged as `ab04757a668839427145f6910de28e83ba0889ae` after exact Review head `4142c958b200a2d60b6a37dbe1cd38f664234a3d` passed all five permanent checks on Ubuntu and Windows. The complete diff was self-reviewed, every changed path was inside declared write scope, unresolved review threads were zero, and the base `main` remained unchanged through the merge gate.

Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Completed Product Recovery journeys

The permanent Product Orchestrator now has authoritative Class A/B journeys for:

- `photo_to_video -> photo_composition`;
- `visualizer -> audio_visualizer`;
- `free_project -> targeted_edit`;
- `dubbing -> dubbing`.

These journeys keep Project Store/domain stores canonical and use Product Orchestrator only as current-state projection plus allowed semantic actions.

## Dubbing — completed in PR #47

Dubbing is now a dedicated provider-neutral recipe and Product Orchestrator workspace rather than a specialist panel implicitly mounted inside unrelated projects.

The authoritative product chain is:

`verified source video -> verified transcript -> optional accepted translation -> prepared speech -> current Review -> Accept -> local final render`

Canonical authority remains with the existing Dubbing, PreparedSpeech, CurrentReview/DubbingReview and AcceptedDubbing state. Product Orchestrator semantic actions cover manual transcript import, local ASR draft and explicit acceptance, translation save/update, prepared-speech attachment, Review, Accept and final render. Capability Registry / D-017 remains responsible for provider/runtime execution and authorization.

Fail-closed product truth includes current project-owned byte verification, removal of tampered PreparedAudio from executable contracts, explicit-current Review semantics, consumed-Review suppression and current-outcome validation against exact accepted Dubbing IDs. Unsupported background-preserving composition policy remains unavailable; accepted Dubbing uses only the supported server-owned `replace_source_audio_range` policy.

## Verification completed

The final Draft and exact Review heads both passed the permanent Ubuntu/Windows gates. Review evidence included:

- development-context lifecycle validation;
- Ubuntu and Windows bootstrap/unit suites;
- API integration and real HTTP probes;
- real-media golden suites;
- frontend dependency audit, lint and build;
- Ubuntu and Windows browser user-outcome suites.

Focused API evidence covers setup gates, ASR draft/accept, translation round-trip through Product Orchestrator, stale/tampered source rejection, explicit-current Review, Accept and renderability. Dedicated browser evidence performs source import -> manual verified transcript -> translation -> prepared speech -> Review -> Accept -> final render through visible production UI controls and confirms the resulting master as current outcome.

This is Class A/API plus Class B informed browser evidence. It does **not** claim Class C cold-start product usability or installed Windows human acceptance.

## Remaining recovery work

UV Studio is not release-ready. Product Recovery still requires:

1. Music orchestration over existing Music Map / Direction / Assembly / Rhythm Audit / Review domains;
2. Narrated orchestration;
3. General orchestration;
4. Class C cold-start validation;
5. installed Windows human acceptance;
6. only then resumption of Stage 9 packaging/release work.

## Next authorized slice

`product-recovery-music-orchestration`

Use `project-context/NEXT_TASK.md` as the entry contract. Reuse the existing canonical Music domains and capability boundaries; do not create a second music workflow store or begin Stage 9 packaging.
