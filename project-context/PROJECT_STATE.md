# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-8-additional-recipes -->

**Updated:** 2026-08-16

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 7 Music Video Mode is merged through PR #36 / merge commit `523424bf8b58aa1d2da21664fc985f26f757b3b3`. The final idle closure head is `b68669a9eb56e2d85601b9e35f1783ce23a33c1a`; post-merge CI #1431 passed all five permanent jobs, including real-media and Playwright browser E2E on Ubuntu and Windows.

Stage 8 Additional Recipes is now the active draft slice on `stage-8/additional-recipes`, based exactly on that green idle head.

## Architecture invariants

- Project Store/domain state remains canonical; engines, providers and compatibility runtimes are adapters rather than competing project authorities.
- Stage 8 broadens the studio by composition. A new recipe may select existing capabilities, production-policy gates and UI sections, but must not create a second universal timeline, project store, media registry or provider lifecycle.
- Paid/remote execution remains optional and behind D-017; provider/model identifiers remain outside canonical project state.
- Specialized primitives from targeted edit, dubbing, continuity and music are reused only where the recipe needs them.
- GUI, scripts, AI and MCP converge on UV-owned semantic commands/workflows.
- Windows and Linux remain continuous engineering targets.
- Development/review remains Chat-first under D-040; automatic Codex code review is excluded.

## Stage 8 Additional Recipes — draft

Target modes from the roadmap:

1. story video;
2. commercial/product;
3. photo-to-video;
4. visualizer;
5. performance/lip-sync;
6. free project.

The implementation order is composition-first:

- define provider-neutral recipe semantics, capability mappings and production-policy gates;
- give each recipe typed execution input slots rather than relying on the generic text fallback;
- surface the modes through the existing Projects UI and task-specific project workspace sections only where additional controls are actually needed;
- reuse existing deterministic/project-owned assembly and review paths where they fit;
- add representative API/browser regressions while keeping permanent general-video, narrated-video, music-video, dubbing and targeted-edit scenarios green.

## Stage 8 completion gate

Each new mode must complete its relevant user-facing workflow through product UI without a competing project/media engine. The mode should remain mostly recipe + capability mapping + production policy + minimal task-specific UI. Existing permanent regression scenarios must remain green.

Stage 9 remains blocked until Stage 8 is reviewed, explicitly merged, atomically closed to `idle` on `main`, and the exact post-merge idle head passes all permanent required checks.

## Development-memory lifecycle

D-038 keeps one canonical active slice. The active slice is `stage-8-additional-recipes`; the declared handoff is `stage-9-desktop-productization-release-hardening`.
