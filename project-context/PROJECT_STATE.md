# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` remains `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`. PR #95 is refrozen for review after repairing the confirmed P2 found on superseded review head `cd5bea656ef2e7612bda46f9c324d933103860ae`.

The final material Draft head is `cb9852c6ee8b59020d00c0adc8c1b309705cced2`. Exact-head CI #4888 completed with all five permanent jobs SUCCESS, including Stage 4A real-media and Stage 4C/5 browser outcomes on Ubuntu and Windows.

## Confirmed P2 and repair evidence

The old Product Workflow `render_music_master` action required `rhythm_aligned`; the first direct `video.render_music_video` capability migration omitted that prerequisite. PR #95 returned to Draft before material repair.

The canonical direct execution boundary now calls `MusicDirectionStore.rhythm_audit(project_id)` and rejects the render unless `summary.all_aligned == true`, before source probing or FFmpeg execution. The focused real-media regression uses a valid current Music Director/Assembly state with an unbound 2.5 s cut and nearest global marker at 3.0 s, proving a 500,000 µs misalignment is rejected with HTTP 422 before an injected media runner can execute and without creating a render artifact. The existing aligned render path remains green.

The five Product Workflow Music mutation actions remain retired. Music Map, Direction, Assembly, render and Review remain on the established direct domain/capability endpoints; Product Workflow remains read-only compatibility state for the legacy Music page.

## Review boundary

This refreeze changes context only. Runtime, frontend and acceptance bytes are exactly those proven on material head `cb9852c6ee8b59020d00c0adc8c1b309705cced2`.

Before merge require all five permanent jobs SUCCESS on the exact new review head, resolve the confirmed P2 review thread with the repair evidence, and obtain a genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0. Any material change supersedes that review identity and requires Draft again.
