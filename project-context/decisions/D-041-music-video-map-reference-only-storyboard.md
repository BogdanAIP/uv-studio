# D-041 — Music Video Mode uses UV-owned Music Map and reference-only storyboard research

**Status:** accepted for Stage 7 draft  
**Date:** 2026-08-16

## Context

Stage 7 adds a professional music-driven workflow without turning music-specific production policy into a requirement for general video, narration, dubbing or targeted existing-video editing. The mode needs durable song timing, structure, shot-direction and review evidence, but UV Studio already owns the canonical Project Store, Recipe Registry, Capability Registry, editor/render boundaries and D-017 authorization.

The named research repository `huangserva/musical-mv-storyboard` was inspected at exact commit `3b73fe98a8953df13cae80238ad9bcd1bc5ae490`. Its workflow contains useful general concepts such as song-first timing, director scoring, phrase mapping, sample-first work and rhythm audit. At inspection time GitHub reported no repository license and no `LICENSE` file was present.

## Decision

1. `music_video` is a dedicated optional recipe. It does not modify the semantics of `general_video` or make music state globally mandatory.
2. Project Store remains the single canonical project authority. Inside Music Video Mode, the selected project-owned song/excerpt is the authoritative timing and final master-audio reference, not a second project database or EDL.
3. Durable music timing is UV-owned typed state under `timeline/`:
   - Music Map binds exact project audio path, SHA-256, byte size and duration;
   - it records the selected excerpt plus structured sections, timing markers and lyric/vocal phrases where known;
   - it has a deterministic revision digest.
4. Music Director state is provider-neutral and binds the exact Music Map revision the user reviewed. A stale map revision cannot be silently accepted. Shot windows must form one contiguous coverage of the selected excerpt and any explicit sync marker must exist in the bound Music Map.
5. Rhythm audit is derived/read-only evidence. It measures cut boundaries against explicit sync markers or deterministic Music Map targets and does not create a second canonical timeline.
6. Manual/project-supplied Music Map data is a complete provider-free path. Automatic beat/structure/lyric/media analysis may later propose data through semantic capabilities such as `media.understand`, but model output is non-authoritative until accepted through UV-owned commands.
7. Remote/non-free generation or analysis remains behind D-017. Provider/model identifiers do not belong in canonical Music Map or Music Director state.
8. Final assembly must reuse existing UV-owned editor/render boundaries. Stage 7 must not import a competing EDL/render engine merely because an external storyboard workflow uses one.
9. `huangserva/musical-mv-storyboard@3b73fe98a8953df13cae80238ad9bcd1bc5ae490` is **reference-only while compatible licensing provenance is absent**. UV Studio will not copy, vendor, import, translate, or derive its scripts/templates/code. General workflow ideas may be independently implemented through UV-owned contracts. Any future code-level adapter requires an explicit compatible upstream license and pinned provenance first.

## Consequences

- Music projects can be portable, deterministic and reviewable without a mandatory cloud/music-analysis provider.
- Updating the Music Map deliberately invalidates stale Music Director plans instead of silently retiming them.
- UI, scripts, AI and MCP can converge on semantic Music Map / Music Director commands.
- Song upload becomes first-class project media rather than being routed through dubbing-specific prepared-audio semantics.
- The upstream storyboard repository can inform product thinking without creating an unlicensed dependency or provenance ambiguity.

## Verification required

Stage 7 must retain permanent non-music regression checks and add evidence for:

- Music Map opt-in state, exact media identity and stale/tampered revision rejection;
- Music Director exact revision binding, contiguous timing coverage and marker validation;
- deterministic rhythm audit;
- portable archive/reopen of song, Music Map and Music Director state;
- first-class project audio source upload with probe/SHA/rollback guarantees;
- a production UI path for a 20–30 second music-video excerpt;
- explicit provider/cost behavior and a provider-free fixture path;
- final real-media/browser evidence without importing code from the unlicensed research repository.
