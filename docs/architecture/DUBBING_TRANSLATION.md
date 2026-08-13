# Dubbing and Translation Architecture

## Current status

Stage 5 implementation is merged through PR #32. Dubbing composes the existing UV Project Store, Command API, Capability Registry, Review/Accept and render foundations; it does not create a second project or timeline model.

## Canonical workflow

```text
project-owned source
  -> imported transcript or whisper.cpp ASR draft
  -> explicit transcript acceptance
  -> optional manual/Argos translation draft
  -> imported/recorded speech or D-017-authorized TTS
  -> PreparedAudio / PreparedSpeech
  -> optional WhisperX alignment draft
  -> timing + loudness evidence
  -> explicit Review
  -> explicit AcceptedDubbingEdit
  -> deterministic accepted visual+dubbing render
  -> browser preview/export
  -> optional WebVTT artifact
```

Draft-producing model operations do not directly mutate accepted state.

## Implemented reusable stack

- **whisper.cpp** — local/free baseline for `speech.transcribe`;
- **Argos Translate** — optional local/free `text.translate` adapter when runtime/language packages exist;
- **Edge TTS** — reused remote/free synthesis path, still requiring D-017 remote consent;
- **WhisperX** — optional heavy local-cache `audio.align` precision layer with no hidden downloads;
- **FFmpeg/FFprobe** — deterministic probing, loudness evidence and final media composition;
- **MLT** — existing editor/timeline projection engine behind the UV adapter;
- **WebVTT exporter** — built-in deterministic subtitle projection from current canonical script/timing state.

Optional model/runtime packages remain outside portable project state.

## Canonical state

Typed/versioned state includes transcript, translation, PreparedSpeech, forced alignment, review and accepted dubbing. Bindings use exact project/source/script/audio identity; provider credentials and raw engine state are excluded.

## Review/accept boundary

D-035 requires server-owned timing/audio evidence plus explicit human content-fidelity and synchronization confirmation before approval. Accepted same-source dubbing ranges cannot overlap. Only `replace_source_audio_range` is currently executable; background-preserving/mix policies remain fail-closed pending D-036 separation evidence.

## Rendering

`video.render_dubbing` accepts canonical source identity, derives current accepted visual+dubbing decisions server-side, maps source-time dubbing through preceding visual edit duration deltas and replaces only accepted audio ranges. Real-media tests verify original audio before/after the target range and replacement audio inside it on Windows and Ubuntu.

## Subtitles

WebVTT export derives text/timestamps from current transcript or exact translation state, supports overlapping dialogue cues, escapes cue text and writes only a registered project-owned subtitle artifact downloadable through the bounded artifact route.

## Post-merge hardening before Stage 6

The audit after PR #32 identified correctness/quality gaps that are intentionally tracked as the next slice rather than hidden as “Stage 6 work”:

- Review recency/current semantics must not use lexical UUID order;
- an existing translation ID must not change target language/dubbing identity;
- newly synthesized speech must become the explicit selected take;
- mutation-vs-binding checks require transaction-sized locking;
- critical accepted-media identity checks must verify current bytes where stored SHA is trusted;
- browser E2E is still required by the roadmap user-outcome gate.

These are targeted hardening items; they do not reopen the Stage 5 architecture or the D-033 editor-foundation choice.
