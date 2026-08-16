# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-7-music-video-mode -->

**Updated:** 2026-08-16

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 6 is merged through PR #35 / merge commit `ea0b766c03d216a154961ca0cd3043e3d3e94d43`. Its exact idle closure head `89bb51cbba301c85e7822fd4120bc67de43fec54` passed post-merge push CI #1321 with all five permanent jobs green, including the maintained browser E2E on Ubuntu and Windows. This satisfies the Stage 7 entry gate.

UV Studio currently has a product-owned Project Store, Recipe and Capability registries, D-017 authorization for remote/non-free execution, deterministic FFmpeg media/render paths, MLT behind a UV-owned editor adapter, targeted existing-video editing, dubbing/translation and optional linked-shot continuity/review. Stage 7 must compose these primitives rather than create another project or media engine.

## Architecture invariants

- Project Store/domain state remains canonical; external skills, model runtimes, MLT and FFmpeg are adapters/engines, not second authorities.
- GUI, scripts, AI and MCP converge on UV-owned semantic commands/workflows.
- Remote/non-free execution remains behind D-017 with explicit provider/cost behavior.
- Music-video behavior is an optional recipe/policy and must not become mandatory for general video, narration, dubbing or targeted editing.
- Local/free deterministic work is preferred where viable; generated assets may use optional providers without embedding provider IDs into canonical project state.
- Windows and Linux remain continuous engineering targets.
- Development/review remains Chat-first under D-040; automatic Codex code review is excluded.

## Stage 6 completion evidence

PR #35 final review head `55ca0e9c138594c34b8563f6267c6823cbc5794b` passed complete PR CI runs #1318 and #1319. PR #35 merged as `ea0b766c03d216a154961ca0cd3043e3d3e94d43`. Atomic closure head `89bb51cbba301c85e7822fd4120bc67de43fec54` returned lifecycle to idle and passed push CI #1321: development-context, both bootstrap jobs and both app-baseline jobs succeeded, including API/real HTTP, FFmpeg/MLT real-media coverage, frontend lint/audit/build and browser E2E on both operating systems.

Stage 6 preserves optional planned/observed continuity, SHA-bound takes, explicit Review/Accept/re-anchor, bounded TimelineContext and non-authoritative provider-neutral Review Assist. Its Chat-only audit regressions fail closed on stale/corrupted review evidence before and after acceptance.

## Stage 7 Music Video Mode — active draft

The Stage 7 goal is a professional, optional 20–30 second music-video excerpt workflow. The baseline direction is:

- add a dedicated `music_video` recipe instead of widening `general_video` semantics;
- treat the selected song/excerpt as the authoritative timing reference for this mode while Project Store remains the canonical project authority;
- persist a typed/versioned UV-owned Music Map where durable state is required: exact song reference/identity, excerpt range, musical sections, beat/downbeat or other timing markers, lyric/vocal phrases when known, climax/emphasis windows and revision identity;
- keep Music Director decisions and shot timing plans provider-neutral and bound to the exact Music Map revision;
- support manual/project-supplied timing as a complete provider-free path; automatic analysis is optional and must enter through a tested capability/adapter boundary;
- use existing editor/render primitives for assembly and master-audio preservation rather than a second EDL/render engine;
- make generated assets sample-first; remote/non-free generation stays behind D-017;
- add deterministic rhythm/timing audit from known Music Map markers and edit boundaries, plus evidence-based final review;
- add a product UI Music Map / Music Director workflow and permanent browser scenario C for a 20–30 second excerpt using provider-free fixtures.

## `musical-mv-storyboard` evaluation

The named upstream `huangserva/musical-mv-storyboard` was inspected at exact commit `3b73fe98a8953df13cae80238ad9bcd1bc5ae490` (V2.11 status commit). It contains useful workflow concepts around song-first timing, director score, visual-duration planning, phrase/lip-sync mapping, sample-first work and rhythm audit.

However, GitHub currently reports no repository license and the repository contains no `LICENSE` file. Therefore Stage 7 will not copy, vendor, import or derive its scripts/templates/code. Until compatible licensing provenance exists, it is architecture/reference material only. UV Studio may independently express general workflow ideas through its own typed contracts and existing engines.

## Completion gates for Stage 7

Engineering gate:

- music state is typed, versioned, portable and provider-neutral;
- exact song/media identity and Music Map revisions are trust-boundary inputs;
- automatic analysis suggestions cannot mutate canonical state without explicit UV-owned commands;
- assembly uses existing deterministic editor/render boundaries;
- remote/non-free work cannot bypass D-017;
- archive/reopen/stale-binding/failure behavior is tested;
- non-music regression scenarios remain green.

User-outcome gate:

- from the production UI, a user can select a song/excerpt, define or inspect the Music Map, plan music-aware shots, use prepared or explicitly generated assets, assemble, audit/review and render a 20–30 second excerpt without manual API calls or a required paid provider.

## Cross-cutting backlog

Existing non-blocking debt remains: broader codec/device fixtures, dependency reproducibility, renderer file-handle/TOCTOU hardening, richer continuity authoring and eventual retirement of transitional compatibility surfaces. Stage 7 should not absorb unrelated cleanup unless it blocks the music-video user outcome or trust boundary.

## Development-memory lifecycle

D-038 keeps one canonical active slice. The active slice is `stage-7-music-video-mode` on `stage-7/music-video-mode`, based on verified idle main head `89bb51cbba301c85e7822fd4120bc67de43fec54`. The declared next handoff is `stage-8-additional-recipes`.
