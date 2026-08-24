# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-architecture-intent-first-creation -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

PR #59 remains the single active **Draft**, but its product goal changed after real installed-Windows review rejected the recipe-card-first product concept.

The exact Windows candidate `95f96d3ecde159a1957e8ed56ad8da73d96458f6` is valuable automated infrastructure evidence only. CI and Stage 9 Release #395 were green, but that does **not** constitute product acceptance. The user explicitly rejected the underlying interaction model: hiding Stage/VideoClaw/provider implementation details did not turn the collection of recipes and source-ingestion panels into the intended creative product.

## Product decision

The product-facing authority must start from **user intent**, not from a technical recipe catalogue.

The primary journey is now:

1. user describes what they want to create;
2. UV Studio stores that intent as canonical project state;
3. the application layer projects a production plan from the intent, current project materials and Capability Registry;
4. each plan step offers truthful routes such as generate, import/use own material, or complete manually;
5. provider/model/recipe details remain execution concerns behind capabilities;
6. deterministic assembly, review and export remain canonical UV Studio operations;
7. unavailable generation is shown as a missing capability/connection, never as a fake completed feature.

Existing recipes, Stage 8 workspace files and legacy panels may remain temporarily as execution/compatibility primitives for preserved projects. They are no longer allowed to define the primary new-project UX.

## Architectural direction under work

Introduce an application-owned creative-project boundary without breaking portable project archives:

- store the new creative intent under `ProjectDocument.extensions` instead of bumping the project schema prematurely;
- use a small application service to create/update intent-first projects and derive their production plan;
- derive plan routes from the shared Capability Registry (`text.generate`, `image.generate`, `video.generate`, `speech.synthesize`, local assembly) rather than provider names;
- allow existing local General Video assembly to remain an implementation path when the user supplies visuals;
- keep cloud/paid execution explicit under D-017 and capability selection;
- make the `/projects` first-run surface one goal-oriented creation form, not a grid of recipe cards;
- keep old/specialized projects openable, but separate them from the default creation journey.

## Previous acceptance findings retained

The earlier installed pass found and fixed inherited Chinese Settings text. A later pass found exposed Stage 6/8 terminology and provider/model configuration. Those findings remain valid, but the subsequent UI remediation was insufficient because it only made the old architecture more honest and less visible.

This slice is therefore **not waiting for acceptance of Release #395**. Product work continues on top of the proven packaging/runtime foundation until the intent-first path is real and testable.

## Verification status

- PR #58 Class C remains the last completed lifecycle slice.
- PR #59 remains Draft and unaccepted.
- Exact head `95f96d3e...` previously passed CI #2796/#2797 and Stage 9 Windows Release #395 before this product-architecture pivot.
- New commits after the pivot require fresh permanent CI and, once the new product path is coherent, a fresh exact Windows Release and human pass.

Missing `main` branch protection remains intentionally deferred per project direction.

## Next authorized slice

After the intent-first product architecture is reviewed, merged and lifecycle-closed, continue with `architecture-hardening-execution-truth` to remove the remaining independently maintained legacy `/execution-plan` truth and other compatibility tails.
