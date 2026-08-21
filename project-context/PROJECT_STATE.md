# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-dubbing-orchestration -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-dubbing-orchestration` is the active Draft slice on branch `fix/product-recovery-dubbing-orchestration`, based on idle `main` after PR #46.

PR #46 completed targeted existing-video edit orchestration. The next recovery task is the already documented permanent Dubbing journey; this slice does not reopen D-033 editor ownership or Stage 9 packaging.

## Dubbing product truth at slice entry

The existing Dubbing implementation is substantial and already split into canonical UV-owned domains:

- `DubbingStore` owns source-SHA-bound transcript and optional translation;
- `PreparedSpeechStore` owns project speech takes over verified prepared audio;
- optional alignment remains a separate accepted projection;
- `DubbingReviewStore` owns evidence-based Review and immutable AcceptedDubbingEdit;
- `video.render_dubbing` is a deterministic local FFmpeg/FFprobe capability over current accepted state;
- ASR, translation, TTS and alignment remain provider/runtime capabilities behind the Capability Registry and D-017 authorization.

The defect is product routing and orchestration, not absence of these domains. Dubbing is currently exposed as a specialist panel on non-migrated `general_video`, while Recipe Registry has no dedicated Dubbing task even though Product Recovery defines Dubbing as a permanent core journey.

## Required implementation direction

This slice will add a provider-neutral `dubbing` recipe and a read-only Product Orchestrator projection for that task. The projection will derive prerequisites, readiness and next actions from verified project-owned source video, current capability offers and the existing canonical Dubbing/PreparedSpeech/Review/Accepted state.

Semantic mutations must delegate to existing UV-owned command/services. Capability actions must continue through existing Capability Registry selection and D-017 authorization. No second Dubbing workflow store, hidden remote fallback, raw path mutation or legacy VideoClaw route is permitted.

The migrated project page must mount Dubbing from Product Orchestrator `relevant_workspaces`. Existing non-migrated compatibility must not be mistaken for alternate workflow authority.

## Evidence target

Class A/API evidence must cover at least empty/setup-gated, transcript-ready, speech-prepared/reviewed, accepted and renderable/current-outcome states, including fail-closed runtime availability and stale canonical references.

Class B browser evidence must exercise a dedicated `dubbing` project through real UI controls without direct backend seeding of the canonical transcript, while still distinguishing this from future Class C cold-start usability and installed Windows acceptance.

## Architecture invariants

- Project Store/domain stores remain canonical;
- D-017 provider authorization remains binding;
- D-034 ASR output is draft evidence until explicit transcript acceptance;
- D-035 Review -> Accept remains mandatory before final render;
- D-036 unsupported background-preservation policies remain fail-closed;
- D-037 translation/TTS/alignment outputs remain drafts until their accepted UV-owned boundaries;
- no generic NLE expansion or second editor authority is introduced.

## Next handoff

After this slice reaches review, passes exact-head CI, merges and closes to `idle`, continue with `product-recovery-music-orchestration` over the existing Music Map / Direction / Assembly / Review domains.
