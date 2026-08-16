# Project State

<!-- uv-context-state: idle -->
<!-- uv-active-slice: none -->

**Updated:** 2026-08-16

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 7 Music Video Mode is merged through PR #36 / merge commit `523424bf8b58aa1d2da21664fc985f26f757b3b3`.

The final review head `e28ccd96d19aa1e74b48e638a8cc6ebbbdfd9f44` passed CI #1428 with all five permanent jobs green: development-context, Ubuntu/Windows bootstrap and Ubuntu/Windows app-baseline. Both app baselines passed API integration, real HTTP, FFmpeg/MLT real-media evidence, frontend lint/audit/build and Playwright browser E2E.

The repository is now atomically returning to the D-038 `idle` lifecycle. Stage 8 remains the declared next slice and may start only after this exact closure head passes the permanent post-merge checks.

## Architecture invariants

- Project Store/domain state remains canonical; external skills, model runtimes, MLT and FFmpeg are adapters/engines, not second authorities.
- GUI, scripts, AI and MCP converge on UV-owned semantic commands/workflows.
- Remote/non-free execution remains behind D-017 with explicit provider/cost behavior.
- Music-video behavior is an optional recipe/policy and does not become mandatory for general video, narration, dubbing or targeted editing.
- Provider/model identifiers stay outside canonical project state; local/manual operation remains a complete fallback where declared.
- Windows and Linux remain continuous engineering targets.
- Development/review remains Chat-first under D-040; automatic Codex code review is excluded.

## Stage 7 completion

Stage 7 adds the complete optional 20–30 second Music Video workflow:

- dedicated `music_video` recipe;
- first-class project-owned audio upload;
- typed/versioned Music Map bound to exact song bytes, excerpt, sections, timing markers and lyric/vocal phrases;
- provider-neutral Music Director and deterministic rhythm audit;
- optional non-canonical `audio.analyze_music` Analysis Assist requiring explicit UV-owned confirmation;
- reuse of the existing Stage 4B sample-first approval gate for generated visual work;
- SHA-bound Music Assembly over project-owned visual sources;
- canonical FFmpeg render that discards source-video audio and uses the exact master-song excerpt;
- production UI covering song upload, Music Map, Director, rhythm audit, visual assignment, Assembly, render and final review;
- evidence-bound Final Music Video Review tied to exact render SHA plus current Map/Director/Assembly revisions and human transition assessment;
- permanent unit/API/archive/real-media/browser regressions for stale/substituted media, forged provenance and the production Music Video outcome on Ubuntu and Windows.

D-041 remains the licensing/architecture boundary: `huangserva/musical-mv-storyboard@3b73fe98a8953df13cae80238ad9bcd1bc5ae490` is reference-only because compatible licensing provenance was absent at inspection time; no upstream code, scripts or templates were copied or vendored.

## Stage 7 review evidence

- Product-code head `9fdee22614e39551e4e9d63276ece32b29e6e7e1`: CI #1424 fully green.
- Final lifecycle/review head `e28ccd96d19aa1e74b48e638a8cc6ebbbdfd9f44`: CI #1428 fully green.
- PR #36 merged as `523424bf8b58aa1d2da21664fc985f26f757b3b3`.
- No automatic Codex Review was used or required.

## Next slice

`stage-8-additional-recipes` is next. It should broaden UV Studio mainly by composing the existing Project Store, Recipe Registry, Capability Registry, production-policy hooks and editor/render primitives for story, commercial/product, photo-to-video, visualizer, performance/lip-sync and free-project modes rather than adding another universal engine.

The Stage 8 entry gate is: Stage 7 merged, lifecycle `idle`, and the post-merge CI on the exact idle closure head fully green.

## Cross-cutting backlog

Non-blocking debt remains: broader codec/device fixtures, dependency reproducibility, renderer file-handle/TOCTOU hardening beyond current identity checks, richer continuity authoring and eventual retirement of transitional compatibility surfaces.

## Development-memory lifecycle

D-038 keeps one canonical active slice. The repository is `idle`; `last_completed` is `stage-7-music-video-mode` / PR #36 / merge commit `523424bf8b58aa1d2da21664fc985f26f757b3b3`. The declared next handoff is `stage-8-additional-recipes`.
