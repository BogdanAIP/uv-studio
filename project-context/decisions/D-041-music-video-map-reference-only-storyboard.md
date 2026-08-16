# D-041 — Music Video Mode uses UV-owned Music Map and reference-only storyboard research

**Status:** accepted  
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
6. Manual/project-supplied Music Map data is a complete provider-free path. Automatic song/structure/beat/lyric analysis may propose data through semantic capability `audio.analyze_music`, but analysis output is ephemeral/non-authoritative and cannot mutate canonical Music Map without an explicit UV-owned command.
7. Remote/non-free generation or analysis remains behind D-017. Provider/model identifiers do not belong in canonical Music Map, Music Director or Assembly state.
8. Generated visual work reuses the existing Stage 4B sample-first contract: a `generative_transform` full candidate requires explicit approval of a sample bound to the same current plan SHA. Music Video Mode does not introduce a second generation lifecycle.
9. Music Assembly is UV-owned state bound to the exact Music Director revision and exact project-owned visual SHA/size/source intervals. Stale plans or substituted media fail before render.
10. Final assembly reuses existing UV-owned render boundaries. Canonical music-video render discards source-video audio and uses exactly the selected master-song excerpt as final audio, while recording exact Map/Director/Assembly and composition provenance.
11. Final Music Video Review is evidence-bound to the exact rendered artifact bytes and current Map/Director/Assembly revisions. Approval requires the 20–30 second release window, passing deterministic rhythm/master/assembly/render evidence and an explicit human transition assessment.
12. `huangserva/musical-mv-storyboard@3b73fe98a8953df13cae80238ad9bcd1bc5ae490` is **reference-only while compatible licensing provenance is absent**. UV Studio will not copy, vendor, import, translate, or derive its scripts/templates/code. General workflow ideas may be independently implemented through UV-owned contracts. Any future code-level adapter requires an explicit compatible upstream license and pinned provenance first.

## Consequences

- Music projects are portable, deterministic and reviewable without a mandatory cloud/music-analysis provider.
- Updating the Music Map deliberately invalidates stale Director/Assembly state instead of silently retiming it.
- UI, scripts, AI and MCP can converge on semantic Music Map / Director / Assembly boundaries.
- Song upload is first-class project media rather than being routed through dubbing-specific prepared-audio semantics.
- Optional analysis and generation can be added through existing Capability/D-017 boundaries without becoming canonical authorities.
- Final review cannot bless a stale/substituted render or incomplete/fake composition metadata.
- The upstream storyboard repository can inform product thinking without creating an unlicensed dependency or provenance ambiguity.

## Verification required

Stage 7 must retain permanent non-music regression checks and evidence for:

- Music Map opt-in state, exact media identity and stale/tampered revision rejection;
- Music Director exact revision binding, contiguous timing coverage and marker validation;
- deterministic rhythm audit;
- portable archive/reopen of song, Music Map and Music Director/Assembly state;
- first-class project audio source upload with probe/SHA/rollback guarantees;
- provider-neutral non-canonical analysis assist and provider-free manual fallback;
- reuse of the existing sample-first generative candidate gate;
- exact Assembly/render provenance and master-audio preservation;
- evidence-bound 20–30 second Final Review;
- a production UI path and real-media/browser evidence on Ubuntu and Windows without importing code from the unlicensed research repository.
