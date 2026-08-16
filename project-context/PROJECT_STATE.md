# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: stage-8-additional-recipes -->

**Updated:** 2026-08-16

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 7 Music Video Mode is merged through PR #36 / merge commit `523424bf8b58aa1d2da21664fc985f26f757b3b3`. Its idle closure head `b68669a9eb56e2d85601b9e35f1783ce23a33c1a` passed post-merge CI #1431 with all five permanent jobs green.

Stage 8 Additional Recipes is implemented in PR #37 on `stage-8/additional-recipes` and is now entering review. The final product-code head before this context-only transition is `2fb903794cf6b6bef576f941c21c18bee9059377`. CI #1572 / Actions run `31969309483` passed all five required jobs on that exact head: development-context, Ubuntu/Windows bootstrap and Ubuntu/Windows app-baseline. Both app baselines passed API integration, real HTTP, FFmpeg/MLT real-media evidence, frontend lint/audit/build and Playwright browser user outcomes.

## Architecture invariants

- Project Store/domain state remains canonical; engines, providers and compatibility runtimes are adapters rather than competing project authorities.
- Stage 8 broadens the studio by composition. Recipes select UV-owned capabilities, production-policy gates and task-specific UI without creating a second universal timeline, project store, media registry or provider lifecycle.
- Paid/remote execution remains optional and behind D-017; provider/model identifiers remain outside canonical project state.
- Specialized primitives from targeted edit, dubbing, continuity and music remain optional building blocks rather than global requirements.
- GUI, scripts, AI and MCP converge on UV-owned semantic commands/workflows.
- Performance/lip-sync remains fail-closed unless the exact optional MuseTalk pack satisfies D-043 provenance/runtime/CUDA verification.
- Windows and Linux remain continuous engineering targets.
- Development/review remains Chat-first under D-040; automatic Codex code review is excluded.

## Stage 8 Additional Recipes — ready for review

Stage 8 now provides six truthful product modes without a competing project or media engine:

1. **Story Video** — composition-first workspace for brief/script plus exact project-owned image/video/audio bindings. Workspace state is typed/versioned, stored under Project Store extensions, SHA/size-bound and fails closed when bound bytes change.
2. **Commercial / Product** — the same portable workspace contract with product-oriented media roles and no fake native pipeline claim.
3. **Photo → Video** — semantic capability `video.compose_photos` through bounded local FFmpeg offer `local_ffmpeg.video_compose_photos`; ordered project-owned stills, optional project-owned audio, deterministic 1280x720/30 fps H.264 output and exact source/duration/artifact provenance.
4. **Audio Visualizer** — semantic capability `audio.visualize` through bounded local FFmpeg offer `local_ffmpeg.audio_visualize`; project-owned master audio, optional artwork, waveform render, measured duration verification and exact artifact provenance.
5. **Performance / Lip-sync** — supplied portrait + finished speech path through optional local MuseTalk 1.5 offer `local_musetalk.video_digital_human`. The offer becomes executable only after exact pinned checkout, clean worktree, entrypoint fingerprint, runtime imports and CUDA checks; otherwise the product reports `configuration_required`/partial and creates no fake result.
6. **Free Project** — intentionally has no required one-click pipeline; users compose only the UV-owned primitives needed by the project.

All six recipes preserve their real media input kinds and avoid the old generic TEXT fallback. Story/commercial/free use the shared Stage 8 composition workspace rather than a new timeline or pipeline engine. Photo/visualizer use deterministic local media capabilities where the operation is inherently local. Performance/lip-sync keeps the heavyweight ML runtime outside the normal UV Studio dependency graph.

## Stage 8 user-outcome evidence

Permanent browser coverage now exercises Stage 8 through the built production frontend against the real FastAPI backend:

- story/commercial/free workspaces save and reopen exact SHA-bound project media through product UI;
- photo-to-video uploads real still images and optional audio, preserves a user-chosen image order across later project-source refreshes, renders real media and verifies artifact source bindings in that exact order;
- visualizer uploads real master audio and artwork and produces a real local render;
- performance/lip-sync registers project-owned portrait and speech, exposes the truthful `configuration_required` state when the verified optional pack is absent, keeps execution disabled and proves no fake render artifact is created;
- the existing Music Video, targeted-edit, dubbing and linked-shot continuity browser outcomes remain green.

The real-media suite separately covers photo/visualizer output semantics and stale/substituted registered-source failure paths. Project archive portability for the Stage 8 workspace is also covered by permanent tests.

## Stage 8 review findings closed during implementation

Review-oriented CI work found and fixed concrete defects before the lifecycle transition:

- the photo execution-plan diagnostic lost semantic capability ID `video.compose_photos`; the API projection now keeps capability identity in blocked readiness diagnostics;
- browser tests previously raced asynchronous project-source registration after uploads; shared option selection now waits for the exact project-owned source option instead of treating an already-visible `<select>` as completion evidence;
- performance/lip-sync had the same source-registration race and now waits for the exact portrait/speech source IDs;
- Stage 8 media and lip-sync panels were forcibly remounted whenever `project.sources.length` changed, which could discard manual image order and selections after an upload; the panels now remain mounted, preserve valid choices and deterministically append newly registered sources;
- browser evidence now explicitly reorders photo inputs, uploads audio afterward and verifies the final render artifact retains the user-selected order.

## Stage 8 decisions

D-042 keeps all additional modes composition-first and forbids new universal project/timeline/provider engines or false compatibility. D-043 accepts MuseTalk 1.5 only as an optional, independently installed, provenance-verified local performance/lip-sync pack; its GPU/runtime requirements are not core dependencies and Stage 9 owns installation/diagnostics.

## Stage 8 completion gate

The engineering and user-outcome gates are satisfied on product-code head `2fb903794cf6b6bef576f941c21c18bee9059377` with CI #1572 / Actions run `31969309483` fully green on all five required jobs. This context-only transition moves the active slice from `draft` to `review`; one final CI run on the resulting context head is required before PR #37 is marked Ready for review.

Stage 9 remains blocked until PR #37 is reviewed, explicitly merged, atomically closed to `idle` on `main`, and the exact post-merge idle head passes all permanent required checks.

## Cross-cutting backlog

Existing non-blocking debt remains: broader codec/device fixtures, reproducible Python dependency locking, schema migration/versioning for growing extension state, generated frontend contracts, a future common command envelope, reusable frontend primitives, CI job decomposition, renderer file-handle/TOCTOU hardening beyond current identity checks, richer continuity authoring and eventual retirement of transitional compatibility surfaces. These are not Stage 8 review blockers and must not be mixed into this slice unless review exposes a direct regression.

## Development-memory lifecycle

D-038 keeps one canonical active slice. The active slice is `stage-8-additional-recipes` on `stage-8/additional-recipes`, based on verified idle main head `b68669a9eb56e2d85601b9e35f1783ce23a33c1a`, and is now in `review`. The declared next handoff is `stage-9-desktop-productization-release-hardening`.
