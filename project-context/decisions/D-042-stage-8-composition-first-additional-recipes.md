# D-042 — Stage 8 additional modes are composition-first recipes, not new universal engines

**Status:** accepted  
**Date:** 2026-08-16

## Context

Stage 8 broadens UV Studio with story video, commercial/product, photo-to-video, visualizer, performance/lip-sync and free-project modes. By this point UV Studio already owns the canonical Project Store, Recipe Registry, Capability Registry, D-017 authorization boundary, editor/render primitives, targeted-edit workflow, dubbing state, linked-shot continuity and Music Video production state.

The main architectural risk is treating every product mode as justification for a new project schema, timeline engine, provider lifecycle or opaque one-click pipeline. That would duplicate already verified infrastructure and make project portability and cross-mode regression behavior harder to reason about.

A second risk is false compatibility: the legacy native VideoClaw pipelines and current Capability Registry do not implement every Stage 8 user outcome. In particular, `video.digital_human` is currently a semantic capability without an accepted executable offer for the supplied portrait + speech contract, and `timeline.assemble` is deterministic concat-copy of already prepared video rather than a still-image animation or audio visualizer engine.

## Decision

1. Stage 8 modes are implemented primarily as `RecipeDefinition` + typed execution inputs + capability mapping + production-policy gates + minimal task-specific UI.
2. Project Store remains the sole canonical project authority. Stage 8 does not introduce a second project store, timeline/EDL, media registry, provider registry or job lifecycle.
3. Story Video composes existing planning, optional generation, Stage 6 continuity and deterministic assembly. Continuity is used only where linked scenes need it.
4. Commercial/Product composes source review, explicit direction, existing sample-first generation, deterministic assembly and final review. Product identity/details are treated as review evidence rather than a new universal media schema.
5. Photo-to-video must have a truthful deterministic local path for still-image composition before the mode is considered complete. It must not pretend that concat-copy alone animates images.
6. Visualizer must have a truthful deterministic local path from project audio (and optional artwork) before the mode is considered complete. It must not route audio into an incompatible generic video-generation contract.
7. Performance/Lip-sync is capability-gated. Until an accepted executable offer satisfies the exact supplied-media contract, the product must report partial/unavailable execution rather than silently route to the legacy VideoClaw product-promo `digital_human` pipeline.
8. Free Project intentionally has no required one-click pipeline. Its inputs and capabilities are optional, and users compose only the UV-owned primitives needed by that project.
9. All Stage 8 execution plans must preserve real media input kinds. Unknown-recipe TEXT fallback must not be used for the six Stage 8 modes.
10. Remote/non-free offers remain optional and behind D-017. Provider/model IDs stay outside canonical recipe/project state.
11. Automatic Codex code review remains excluded under D-040. Ordinary cross-platform CI, unit/API/real-media/browser evidence remains the readiness authority.

## Consequences

- The studio gains distinct user-facing modes without multiplying core engines.
- A recipe may be visible before every optional provider offer exists, but its execution compatibility must remain truthful and fail closed rather than expose a fake launch path.
- Deterministic local FFmpeg capabilities can be added where the media operation is inherently local and reproducible, while generative work continues through Capability Registry and D-017.
- Existing targeted-edit, dubbing, continuity and music primitives remain optional building blocks instead of becoming global requirements.

## Verification required

Stage 8 must prove:

- all six recipes are deterministic in the registry and visible through the existing recipe catalog;
- all six have explicit typed execution input contracts rather than generic TEXT fallback;
- photo-to-video and visualizer have real local-media evidence once their deterministic adapters are added;
- performance/lip-sync never reports native launchability without an accepted exact offer;
- free-project has no fake required pipeline;
- representative user-facing paths work through product UI;
- all permanent general-video, narrated-video, music-video, dubbing and targeted-edit regressions stay green on Ubuntu and Windows.
