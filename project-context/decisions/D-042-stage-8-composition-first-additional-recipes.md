# D-042 — Stage 8 composition-first additional recipes

**Status:** Superseded at product-composition level by D-063 and D-064  
**Date:** 2026-08-16  
**Historical role:** Stage 8 implementation record

## Decision history

D-042 introduced story, commercial/product, photo-to-video, visualizer, performance/lip-sync and free-project behavior primarily through `RecipeDefinition`, typed inputs, capability mapping and bounded task UI. It deliberately reused Project Store, shared engines and capability/security boundaries instead of creating a new project/timeline engine for every mode.

That implementation strategy was appropriate to Stage 8, but its **recipe-first user-facing product composition is no longer current architecture**.

## Invariants that remain accepted

- Project Store remains canonical.
- Do not create a separate project/timeline/provider lifecycle for every task.
- Media operations must use truthful semantic capabilities rather than incompatible fallbacks.
- Remote/non-free execution remains explicit behind D-017.
- Deterministic local FFmpeg implementations such as photo composition and visualizer are useful reusable primitives.
- Optional heavy ML packs remain isolated and fail closed when unavailable.
- Existing targeted-edit, dubbing, continuity and music implementations may be reused rather than rebuilt.

## Superseded clauses

Do not use D-042 as authority to:

- add new `RecipeDefinition` entries for product directions/features;
- expose the old six Stage 8 recipes as the current project taxonomy;
- grow recipe execution plans or Stage workspaces as the normal Studio composition model.

D-064 now defines Production Directions over one shared Studio Core. Photo-to-video, visualizer and lip-sync are contextual tools unless a later accepted decision establishes otherwise.

The original full D-042 text and Stage 8 verification evidence remain available in Git history.
