# D-042 — Stage 8 additional modes are composition-first recipes, not new universal engines

**Status:** accepted  
**Date:** 2026-08-16

## Context

Stage 8 broadens UV Studio with story video, commercial/product, photo-to-video, visualizer, performance/lip-sync and free-project modes. By this point UV Studio already owns the canonical Project Store, Recipe Registry, Capability Registry, D-017 authorization boundary, editor/render primitives, targeted-edit workflow, dubbing state, linked-shot continuity and Music Video production state.

The main architectural risk is treating every product mode as justification for a new project schema, timeline engine, provider lifecycle or opaque one-click pipeline. That would duplicate already verified infrastructure and make project portability and cross-mode regression behavior harder to reason about.

A second risk is false compatibility. At Stage 8 entry, the legacy native VideoClaw pipelines and Capability Registry did not implement every new user outcome: generic concat-copy did not constitute still-image composition or an audio visualizer, and the legacy product-promo `digital_human` pipeline did not satisfy the exact supplied portrait + finished speech contract. Stage 8 therefore had to add truthful semantic capabilities where deterministic local execution was appropriate and keep performance/lip-sync capability-gated rather than claim incompatible execution.

## Decision

1. Stage 8 modes are implemented primarily as `RecipeDefinition` + typed execution inputs + capability mapping + production-policy gates + minimal task-specific UI.
2. Project Store remains the sole canonical project authority. Stage 8 does not introduce a second project store, timeline/EDL, media registry, provider registry or job lifecycle.
3. Story Video composes existing planning, optional generation, Stage 6 continuity and deterministic assembly. Continuity is used only where linked scenes need it.
4. Commercial/Product composes source review, explicit direction, existing sample-first generation, deterministic assembly and final review. Product identity/details are treated as review evidence rather than a new universal media schema.
5. Photo-to-video uses semantic capability `video.compose_photos` with a bounded deterministic local FFmpeg offer. It composes ordered project-owned still images plus optional project-owned audio and records exact input/output identity and duration evidence; concat-copy is not treated as still-image animation.
6. Visualizer uses semantic capability `audio.visualize` with a bounded deterministic local FFmpeg offer. It renders project-owned audio plus optional artwork and verifies the resulting media rather than routing audio into an incompatible generic video-generation contract.
7. Performance/Lip-sync is capability-gated. D-043 accepts only the optional local MuseTalk 1.5 supplied-media offer after exact pinned checkout, clean-worktree, entrypoint-fingerprint, runtime-import and CUDA verification. Without that verified pack the recipe remains partial/`configuration_required`; no incompatible legacy fallback is allowed.
8. Free Project intentionally has no required one-click pipeline. Its inputs and capabilities are optional, and users compose only the UV-owned primitives needed by that project.
9. All Stage 8 execution plans preserve real media input kinds. Unknown-recipe TEXT fallback is not used for the six Stage 8 modes.
10. Remote/non-free offers remain optional and behind D-017. Provider/model IDs stay outside canonical recipe/project state.
11. Automatic Codex code review remains excluded under D-040. Ordinary cross-platform CI, unit/API/real-media/browser evidence remains the readiness authority.

## Consequences

- The studio gains distinct user-facing modes without multiplying core engines.
- Story/commercial/free can persist only their task inputs and exact media bindings without creating a competing planning/timeline authority.
- Photo-to-video and visualizer have deterministic local/free execution where the media operation is inherently local and reproducible.
- Heavy ML dependencies remain optional isolated runtime packs rather than UV core dependencies.
- A recipe may remain visible when an optional runtime is absent, but compatibility stays truthful and fail-closed instead of exposing a fake launch path.
- Existing targeted-edit, dubbing, continuity and music primitives remain optional building blocks instead of becoming global requirements.

## Verification

Stage 8 completion is proven by permanent tests and product UI outcomes:

- all six recipes are deterministic in the registry and visible through the existing recipe catalog;
- all six have explicit typed execution input contracts rather than generic TEXT fallback;
- story/commercial/free persist portable SHA/size-bound Stage 8 workspaces and fail closed on stale source bytes;
- photo-to-video and visualizer have bounded local FFmpeg adapters, API coverage, real-media evidence and production UI flows;
- photo-to-video preserves explicit user ordering across later project-source refreshes and the final artifact provenance records that exact order;
- performance/lip-sync exposes only the optional verified MuseTalk local offer, remains `configuration_required` when the pack/runtime/CUDA checks fail, and does not create a fake artifact;
- free-project has no fake required pipeline;
- representative browser outcomes exercise all six Stage 8 modes through the production frontend;
- permanent music-video, dubbing, targeted-edit, continuity and other regression paths remain green on Ubuntu and Windows.

The final Stage 8 product-code head before review transition is `2fb903794cf6b6bef576f941c21c18bee9059377`; CI #1572 / Actions run `31969309483` passed all five required jobs on that exact head, including API integration, real HTTP, real-media evidence, frontend lint/audit/build and Playwright browser outcomes on Ubuntu and Windows.
