# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: product-recovery-dubbing-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-dubbing-orchestration` is the active **Review** slice on branch `fix/product-recovery-dubbing-orchestration`, based on unchanged idle `main` after PR #46.

The final Draft head `e755fe0cfecf660cb6ddd0fd2158cf09bf4f9acc` passed every permanent repository check on Ubuntu and Windows, including API integration, real-media, frontend lint/build and browser user-outcome suites. The complete PR diff has been self-reviewed, all 17 changed paths are inside the declared write scope, there are zero unresolved review threads, and `main` remains at the expected base `7e5bebe33b43520cea7b92328be19c9fbaeca246`.

PR #47 is now in `review`; the exact Review head must pass the same five permanent checks before merge. PR #46 remains the last completed slice until #47 is actually merged.

Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Dubbing — implemented orchestration

Dubbing is now a dedicated provider-neutral `dubbing` recipe with one authoritative `dubbing` Product Orchestrator workspace. The Product Orchestrator remains a read projection plus semantic actions over existing canonical state; it does not add another workflow store.

The migrated product chain is:

`verified source video -> verified transcript -> optional accepted translation -> prepared speech -> current Review -> Accept -> local final render`

Canonical authority remains with the existing UV-owned domains:

- `DubbingStore` owns source-SHA-bound transcript and translation state;
- `PreparedSpeechStore` owns speech takes over verified project-owned audio;
- `CurrentReviewStore` / `DubbingReviewStore` own explicit-current Review and immutable AcceptedDubbingEdit;
- `video.render_dubbing` remains the deterministic local FFmpeg/FFprobe capability;
- ASR, translation, TTS and alignment providers remain behind Capability Registry / D-017 boundaries.

Semantic Product Orchestrator actions now cover manual transcript import, local ASR draft and explicit acceptance, translation save/update, prepared-speech attachment, Review, Accept and final render. Unsupported background-preserving composition policy remains fail-closed; Product Orchestrator pins only `replace_source_audio_range` for accepted Dubbing edits.

## Product truth and fail-closed behavior

The Dubbing projection derives availability from current verified bytes and current canonical domain state rather than stale UI state:

- tampered or missing source video is excluded from executable actions;
- tampered PreparedAudio is removed from the attachment contract;
- local/free runtime availability is projected without widening to remote providers;
- ASR is optional and remains a draft until explicit transcript acceptance;
- only the explicit-current approved Review is eligible for Accept;
- already consumed Reviews are not re-advertised;
- a rendered master is `current_outcome` only when its accepted Dubbing IDs exactly match current accepted state.

The normal dedicated Dubbing project page is routed from Product Orchestrator `relevant_workspaces`; generic targeted-edit and Sequence Continuity workspaces do not leak into this journey. Compatibility surfaces remain only for recipes that have not yet migrated and are not alternate workflow authority.

## Verification completed for the Draft head

The exact Draft head passed all permanent checks on both Ubuntu and Windows:

- development-context lifecycle validation;
- Ubuntu and Windows bootstrap/unit suites;
- Ubuntu and Windows API integration and real HTTP probes;
- real-media golden suites;
- frontend dependency audit, lint and build;
- Ubuntu and Windows browser user-outcome suites.

Focused API evidence covers setup-gated state, local ASR draft/accept, translation round-trip through Product Orchestrator, verified-source and PreparedAudio tamper rejection, explicit-current Review semantics, server-owned composition policy, Accept and renderability.

The dedicated browser journey starts with an empty `dubbing` project and performs visible production UI actions through source import -> manual verified transcript -> translation -> prepared speech -> Review -> Accept -> final render. The resulting master is projected as the current Dubbing outcome.

This remains Class B informed regression evidence. PR #47 does **not** claim Class C cold-start product usability or installed Windows human acceptance.

## Architecture invariants preserved

- Project Store/domain stores remain canonical;
- D-017 provider/runtime authorization remains binding;
- D-034 ASR output remains draft evidence until explicit transcript acceptance;
- D-035 Review -> Accept remains mandatory before final render;
- D-036 unsupported background-preservation policies remain fail-closed;
- D-037 translation/TTS/alignment acceptance boundaries remain explicit;
- no generic NLE expansion, second Dubbing store or second editor authority is introduced.

## Remaining recovery work

Dubbing is now `working_orchestrated` at Class A/B evidence level, but UV Studio is not release-ready. Product Recovery still needs Music, Narrated and General orchestration, followed by Class C cold-start validation and installed Windows acceptance before Stage 9/release can resume.

## Next handoff

If the exact Review head passes all five permanent checks with zero unresolved blocking findings and `main` remains unchanged, merge PR #47, close the lifecycle to `idle`, and continue with `product-recovery-music-orchestration` over the existing Music Map / Direction / Assembly / Rhythm Audit / Review domains without creating a second music workflow store.
