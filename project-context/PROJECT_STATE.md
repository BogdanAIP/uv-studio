# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: stage-7-music-video-mode -->

**Updated:** 2026-08-16

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 6 is merged through PR #35 / merge commit `ea0b766c03d216a154961ca0cd3043e3d3e94d43`. Atomic idle closure head `89bb51cbba301c85e7822fd4120bc67de43fec54` passed post-merge CI #1321 with all five permanent jobs green.

Stage 7 is implemented in PR #36 on `stage-7/music-video-mode` and is now in review. The final product-code head before this context-only transition is `9fdee22614e39551e4e9d63276ece32b29e6e7e1`; CI #1424 passed all five required jobs on that exact head: development-context, Ubuntu/Windows bootstrap and Ubuntu/Windows app-baseline. Both app baselines passed API integration, real HTTP, FFmpeg/MLT real-media evidence, frontend lint/audit/build and Playwright browser E2E.

## Architecture invariants

- Project Store/domain state remains canonical; external skills, model runtimes, MLT and FFmpeg are adapters/engines, not second authorities.
- GUI, scripts, AI and MCP converge on UV-owned semantic commands/workflows.
- Remote/non-free execution remains behind D-017 with explicit provider/cost behavior.
- Music-video behavior is an optional recipe/policy and does not become mandatory for general video, narration, dubbing or targeted editing.
- Provider/model identifiers stay outside canonical music state; local/manual operation remains a complete fallback.
- Windows and Linux remain continuous engineering targets.
- Development/review remains Chat-first under D-040; automatic Codex code review is excluded.

## Stage 7 Music Video Mode — ready for review

Stage 7 now provides a complete provider-free production path for a 20–30 second music-video excerpt:

- dedicated `music_video` recipe without widening `general_video` semantics;
- first-class project-owned audio upload with bounded streaming, FFprobe validation, SHA/size identity and rollback;
- typed/versioned Music Map bound to exact song bytes, excerpt, sections, timing markers and lyric/vocal phrases with deterministic revision identity;
- provider-neutral Music Director bound to the exact Music Map revision with contiguous shot coverage and validated sync markers;
- deterministic rhythm audit over current Map/Director timing;
- provider-neutral Music Analysis Assist through semantic capability `audio.analyze_music`; suggestions are ephemeral/advisory and cannot mutate canonical Music Map without an explicit UV-owned command;
- Music Assembly bound to the exact Music Director revision and exact project-owned visual SHA/size/source intervals;
- canonical FFmpeg music-video render where visual-source audio is discarded and the exact selected master-song excerpt is the final audio track;
- render-time verification of current media identity and measured output duration;
- production UI for song upload, Music Map, Music Director, rhythm audit, visual assignment, assembly, render and final review;
- evidence-bound Final Music Video Review tied to exact render SHA plus current Map/Director/Assembly revisions, exact composition metadata, rhythm evidence and human transition assessment;
- `approved` final review is impossible outside the 20–30 second release window or when required rhythm/master/assembly/render/transition evidence fails;
- generated visual work reuses the existing Stage 4B `generative_transform -> sample -> explicit SampleApproval -> full` gate; full generative candidates cannot register without an approved sample for the same plan SHA;
- project archive/reopen and stale/substitution paths are covered by permanent tests;
- maintained real-media and browser E2E exercise the real production flow on Ubuntu and Windows.

## Stage 7 trust-boundary review findings

Chat review during implementation closed several concrete defects rather than only adding happy-path coverage:

- a React success message previously appeared before cross-panel refresh/remount completed, producing an Ubuntu-only upload race; success visibility now follows completed synchronization, and browser E2E is green on both OSes;
- Music Assembly rejects stale Director revisions, substituted visual bytes and invalid source intervals before render;
- render revalidates actual media identity/duration and records exact composition provenance rather than trusting client-supplied paths;
- Music Analysis Assist rejects stale song bytes and remains non-canonical;
- Final Review rejects fake/incomplete render provenance, stale revisions, substituted artifacts, bad duration/rhythm evidence and failing human transition review.

## D-041 / upstream boundary

D-041 is accepted. `huangserva/musical-mv-storyboard@3b73fe98a8953df13cae80238ad9bcd1bc5ae490` remains reference-only because the inspected upstream reported no repository license and no `LICENSE` file. No upstream code, scripts or templates were copied, vendored, imported or translated into UV Studio. General workflow ideas were independently implemented through UV-owned contracts.

## Stage 7 completion gate

The engineering and user-outcome gates are satisfied on product-code head `9fdee22614e39551e4e9d63276ece32b29e6e7e1` with CI #1424 fully green. This context-only transition moves the active slice from `draft` to `review`; one final CI run on the resulting context head is required before PR #36 is marked Ready for review.

Stage 8 remains blocked until PR #36 is merged, `main` is atomically returned to `idle`, and post-merge CI is green.

## Cross-cutting backlog

Non-blocking debt remains: broader codec/device fixtures, dependency reproducibility, renderer file-handle/TOCTOU hardening beyond current identity checks, richer continuity authoring and eventual retirement of transitional compatibility surfaces. These are not Stage 7 release blockers.

## Development-memory lifecycle

D-038 keeps one canonical active slice. The active slice is `stage-7-music-video-mode` on `stage-7/music-video-mode`, based on verified idle main head `89bb51cbba301c85e7822fd4120bc67de43fec54`, and is now in `review`. The declared next handoff is `stage-8-additional-recipes`.
