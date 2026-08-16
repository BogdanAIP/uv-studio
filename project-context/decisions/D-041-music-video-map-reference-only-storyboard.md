# D-041 — Music Video Mode uses UV-owned Music Map and reference-only storyboard research

**Status:** accepted  
**Date:** 2026-08-16

## Context

Stage 7 adds a professional music-driven workflow without turning music-specific production policy into a requirement for general video, narration, dubbing or targeted existing-video editing. The mode needs durable song timing, structure, shot-direction, visual assembly and review evidence, but UV Studio already owns the canonical Project Store, Recipe Registry, Capability Registry, editor/render boundaries and D-017 authorization.

The named research repository `huangserva/musical-mv-storyboard` was inspected at exact commit `3b73fe98a8953df13cae80238ad9bcd1bc5ae490`. Its workflow contains useful general concepts such as song-first timing, director scoring, phrase mapping, sample-first work and rhythm audit. At inspection time GitHub reported no repository license and no `LICENSE` file was present.

## Decision

1. `music_video` is a dedicated optional recipe. It does not modify the semantics of `general_video` or make music state globally mandatory.
2. Project Store remains the single canonical project authority. Inside Music Video Mode, the selected project-owned song/excerpt is the authoritative timing and final master-audio reference, not a second project database or EDL.
3. Durable music timing is UV-owned typed state under `timeline/`:
   - Music Map binds exact project audio path, SHA-256, byte size and duration;
   - it records the selected excerpt plus structured sections, timing markers and lyric/vocal phrases where known;
   - it has a deterministic revision digest.
4. Music Director state is provider-neutral and binds the exact Music Map revision the user reviewed. A stale map revision cannot be silently accepted. Shot windows must form one contiguous coverage of the selected excerpt and any explicit sync marker must exist in the bound Music Map.
5. Music Assembly is a separate UV-owned visual-binding state, not an EDL replacement. It binds every current Music Director shot exactly once to a project-owned video source, exact source path/SHA/size and source interval. Stale Director revisions, substituted source bytes and invalid intervals fail closed before render.
6. Rhythm audit is derived/read-only evidence. It measures cut boundaries against explicit sync markers or deterministic Music Map targets and does not create a second canonical timeline.
7. Manual/project-supplied Music Map data is a complete provider-free path. Optional `audio.analyze_music` Music Analysis Assist may propose excerpt/sections/markers/lyrics through an ephemeral exact-song binding, but normalized analysis remains non-canonical until a user explicitly writes Music Map through the existing semantic command. The capability may legitimately have zero configured offers.
8. Generated visual assets reuse the existing Stage 4B sample-first contract rather than a music-specific generator: a `generative_transform` candidate starts at `stage="sample"`, requires an explicit `SampleApproval` for the same replacement-plan SHA and only then may register a `stage="full"` candidate. Manually supplied project-owned video remains the provider-free fallback. Re-uploading an external file is treated as explicit user-supplied media, not as a claim about generation provenance.
9. Final assembly uses the semantic capability `video.render_music_video`. Its client input contains only the exact Music Assembly revision SHA. The adapter re-resolves and verifies current Map/Director/Assembly state and all media bytes, strips audio from visual clips, concatenates normalized video segments, and uses the exact selected song excerpt as the single final audio track. User-controlled FFmpeg paths or flags are not part of this contract.
10. Final Music Video Review binds the exact rendered artifact SHA plus current Music Map, Music Director and Music Assembly revisions. Approval requires deterministic rhythm evidence, exact master-audio/assembly provenance, a human `pass` for scene transitions and a release excerpt duration of 20–30 seconds. Shorter fixtures may exercise mechanics but cannot receive an approved release verdict.
11. Remote/non-free generation or analysis remains behind D-017. Provider/model identifiers do not belong in canonical Music Map, Music Director, Assembly or Review state.
12. `huangserva/musical-mv-storyboard@3b73fe98a8953df13cae80238ad9bcd1bc5ae490` remains **reference-only while compatible licensing provenance is absent**. UV Studio will not copy, vendor, import, translate, or derive its scripts/templates/code. General workflow ideas are independently implemented through UV-owned contracts. Any future code-level adapter requires an explicit compatible upstream license and pinned provenance first.

## Consequences

- Music projects are portable, deterministic and reviewable without a mandatory cloud/music-analysis provider.
- Updating Music Map deliberately invalidates stale Director/Assembly/render/review state instead of silently retiming it.
- Song upload and visual upload are first-class project media rather than dubbing/generation-specific shortcuts.
- Generated assets retain the already-tested sample-first human gate instead of bypassing it in Music Video Mode.
- Final rendering has one authoritative audio source: the exact project-owned master-song excerpt.
- A visually acceptable but too-short test clip can prove mechanics while remaining correctly ineligible for release approval.
- The upstream storyboard repository can inform product thinking without creating an unlicensed dependency or provenance ambiguity.

## Verification required

Stage 7 must retain permanent non-music regression checks and add evidence for:

- Music Map opt-in state, exact media identity and stale/tampered revision rejection;
- optional, provider-neutral Music Analysis Assist that never mutates canonical Music Map;
- Music Director exact revision binding, contiguous timing coverage and marker validation;
- deterministic rhythm audit;
- Music Assembly exact Director/media binding and stale/substitution rejection;
- portable archive/reopen of song, Music Map, Music Director and Assembly state;
- first-class project audio/video source upload with probe/SHA/rollback guarantees;
- real FFmpeg evidence that visual source audio is excluded and the master-song excerpt is the only output audio;
- production browser flow from song/Map/Director through Assembly and render on Ubuntu and Windows;
- evidence-bound final review with an explicit 20–30 second approval gate;
- permanent sample-first enforcement for generated replacement candidates;
- final evidence without importing code from the unlicensed research repository.
