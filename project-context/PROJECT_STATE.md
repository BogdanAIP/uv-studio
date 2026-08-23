# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: product-recovery-story-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository is back to **idle** on `main` after Story Video recovery PR #54 merged as `755d38c5ef22bd66dd8c75c650df0ec0da00a536`.

`story_video` is now recovered through the permanent Product Orchestrator to the furthest currently audited preparation state without introducing a parallel Story workflow database, reopening editor ownership, or claiming a final Story render that is not yet proven end to end.

## Accepted Story boundary

- Stage 8 owns the required brief, optional script and ordered SHA-bound Story image/video/audio bindings;
- Product Orchestrator projects that verified Stage 8 state as the authoritative preparation outcome and fails closed on stale/tampered project-owned bytes;
- existing `sequence_continuity` state is reused as optional continuity evidence only when accepted media remains current;
- the Story recipe declaration of `timeline.assemble` is not treated as proof of an audited Story-specific final render/export path;
- provider-backed generation remains optional and setup-dependent and is not represented as local/free Story execution;
- the visible Story project surface is the Stage 8 Story workspace plus Sequence Continuity;
- no `render_story` action, provider bypass, hidden seed state, generic NLE authority or parallel Story workflow store was introduced.

## Verification evidence

Exact Draft head `0adb90a91a0beaaec84747ab66f14bf0e283fba3` passed CI run `32653462863` (#2581) with all five permanent checks green.

Exact Review head `49a72c268a8d2105c3a23895901556c0e925c072` passed CI run `32653979961` (#2589) with all five permanent checks green:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

Both Review app-baseline jobs passed the full browser user-outcome suite, including the visible Story path that creates a Story project, enters brief/script, imports project-owned media, saves the SHA-bound Stage 8 workspace and reaches preparation-ready state without advertising a final render action.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-commercial-product-orchestration`, as defined by `project-context/NEXT_TASK.md`.
