# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: product-recovery-story-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Story Video recovery is active in **Review** on `fix/product-recovery-story-orchestration`, based on validated idle `main` `1a82db63c95b85b2eeb0838066b3f74be267bf72` after General Video PR #53.

PR #54 is the active review surface. The slice recovers `story_video` through Product Orchestrator without introducing a story-specific workflow database, reopening editor ownership, or claiming a final Story render that is not yet audited end to end.

## As-built boundary under review

- Stage 8 owns the required brief, optional script and ordered SHA-bound Story image/video/audio bindings;
- Product Orchestrator projects that verified Stage 8 state as the authoritative preparation outcome: invalid or stale project-owned bytes fail closed instead of advertising readiness;
- existing `sequence_continuity` state is reused only as optional continuity evidence, and accepted takes are exposed only after their current media bytes validate;
- the Story recipe declares `timeline.assemble`, but this slice does **not** treat that declaration as proof of an audited Story-specific final render/export path;
- provider-backed text/image/video/speech generation remains optional and setup-dependent and is not exposed as local/free Story execution;
- the visible Story project surface is the Stage 8 Story workspace plus Sequence Continuity, driven by the same Product Orchestrator readiness shown elsewhere in UV Studio;
- no `render_story` action, provider bypass, hidden seed state, generic NLE authority or parallel Story workflow store is introduced.

## Verification status

The exact Draft head `0adb90a91a0beaaec84747ab66f14bf0e283fba3` passed CI run `32653462863` (#2581) with all five permanent checks green:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

Both app-baseline jobs passed the full browser user-outcome suite, including the visible Story path that creates a Story project, enters brief/script, imports project-owned media, saves the SHA-bound Stage 8 workspace and reaches preparation-ready state without advertising a final render action.

Focused tests cover absent workspace, exact saved preparation state, stale/tampered Story source bytes, API projection and the browser-visible preparation outcome.

PR #54 is now marked ready for review. This commit is the Review lifecycle checkpoint; its exact head must pass the same five permanent checks before merge.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

`product-recovery-commercial-product-orchestration`, as defined by `project-context/NEXT_TASK.md`.
