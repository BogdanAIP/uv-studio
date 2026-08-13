# Project State

<!-- uv-active-slice: stage-5-dubbing-translation -->

**Updated:** 2026-08-13

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 5 dubbing / translation — review

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

Stage 4C is merged through PR #31. UV Studio has a complete existing-video range-edit workflow on the reusable D-033 editor foundation and Stage 5 now composes professional dubbing/translation on that same Project Store, Command API, Capability Registry, review and render boundary.

The Stage 5 user path is implemented as:

```text
project-owned source / selected dialogue range
  -> imported transcript or local whisper.cpp ASR draft
  -> explicit transcript acceptance
  -> manual/imported or optional local Argos translation draft
  -> imported/recorded speech or D-017-authorized TTS
  -> project-owned PreparedAudio / PreparedSpeech
  -> optional WhisperX forced-alignment draft
  -> server-measured timing/loudness evidence
  -> explicit Review
  -> explicit AcceptedDubbingEdit
  -> deterministic accepted visual+dubbing materialization
  -> browser preview / export
  -> optional project-owned WebVTT subtitle artifact
```

## Stage 5 canonical boundaries

- Project Store/domain state remains canonical; there is no second dubbing project or timeline model.
- Transcript, translation, PreparedSpeech, forced alignment, review and accepted dubbing state are typed/versioned and provider-neutral.
- GUI, scripts, AI and MCP share the same semantic capabilities and editor Command API rather than mutating project JSON or raw MLT.
- `whisper.cpp` is the local/free ASR baseline; ASR output remains a draft until explicit `accept_asr_transcript`.
- Argos Translate is an optional local/free translation runtime; language packages remain outside portable project state.
- Existing Edge TTS is reused instead of creating another synthesis subsystem; remote execution requires D-017 one-shot consent for the exact text.
- TTS output is re-copied into `assets/`, re-hashed and re-probed before it can become PreparedSpeech.
- WhisperX is an optional heavy precision `audio.align` layer with explicit local model-cache configuration and no hidden downloads; alignment output remains a draft until accepted through the Command API.
- Review binds exact source/script/take/audio revisions and server-measured timing/loudness evidence plus explicit human content/synchronization confirmation.
- Same-source accepted dubbing ranges cannot overlap; stale revisions fail closed.
- `video.render_dubbing` accepts only canonical project identity, maps source-time dubbing through preceding accepted visual duration deltas and does not accept caller filtergraphs/host paths.
- `replace_source_audio_range` is the only currently materialized composition policy. Background-preserving/mix policies remain fail-closed until D-036 real-media separation evaluation is completed.
- WebVTT is a deterministic projection of canonical transcript/translation state, supports overlapping dialogue cues, and is downloaded only through a bounded registered-artifact route.

## Stage 5 decisions

- D-034: local ASR baseline.
- D-035: evidence-based dubbing Review/Accept boundary.
- D-036: dialogue/background separation evaluation gate.
- D-037: reusable language/audio precision stack and optional-runtime policy.

## Draft implementation gate

Final draft implementation head:

`1b98c936d1b1ddf3945da10ee1985b5b4f001363`

CI #1103 / run `31694526656` passed all five required checks:

- `development-context`
- `bootstrap (ubuntu-latest, 3.11)`
- `bootstrap (windows-latest, 3.11)`
- `app-baseline (ubuntu-latest)`
- `app-baseline (windows-latest)`

The app-baseline jobs include API integration, real FFmpeg/MLT media evidence and frontend lint/audit/build on Ubuntu and Windows.

## Reusable evidence retained

Stage 4C remains authoritative for visual editing/timeline materialization. Stage 5 adds audio/text state and composition without reopening D-033. Real-media Stage 5 coverage proves accepted dubbing replacement while preserving source audio before/after the target range and preserving expected media duration on both supported CI platforms.

## Cross-cutting debt retained outside this slice

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- the aggregate decision index still needs lifecycle/process maintenance;
- broader free-form project JSON fields still need recursive portability hardening outside newly typed boundaries;
- broader accepted-file/content-addressing integrity remains future hardening;
- the compatibility `/api/stages` catalog should be retired when no UV-owned screen needs it;
- broader codec/device fixtures remain incremental hardening.

## Next product slice

After the exact review-context head passes the same five required checks and PR #32 merges, continue with `stage-6-sequence-continuity-review` using the same canonical Project Store, Capability Registry, Command API and explicit Review/Accept boundaries.
