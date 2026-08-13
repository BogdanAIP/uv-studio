# Dubbing and Translation Architecture

## Purpose

Stage 5 adds dubbing and translation as a composition of UV Studio's existing project, editor, capability, review and render foundations. It does not create a second timeline, project format, provider stack or filmmaking workflow.

## Product boundary

The canonical workflow is:

```text
project-owned source video / selected range
  -> speech/audio evidence
  -> transcript
  -> optional translation
  -> prepared spoken replacement
  -> alignment + subtitle state
  -> synchronization/audio review
  -> explicit acceptance
  -> non-destructive audio/timeline state
  -> deterministic preview/render/export
```

Each stage has a typed UV Studio-owned contract. Provider-specific identifiers and credentials remain outside portable project state.

## Reuse-first component policy

Professional maintained open-source components should be integrated behind semantic adapters before writing equivalent signal-processing infrastructure inside UV Studio.

The initial component evaluation targets:

- Whisper-compatible local ASR engines for baseline transcription;
- WhisperX-compatible forced alignment/word timestamps where its dependency/runtime cost is justified;
- FFmpeg for deterministic audio extraction, channel/layout transforms, loudness measurement and final media composition;
- existing UV MLT adapter for editor/timeline projection;
- Edge TTS compatibility already present in the repository as one optional speech-synthesis offer, never as the only speech path.

A concrete dependency is accepted only after license, maintenance, Windows/Linux feasibility, model/runtime footprint and structured-output quality are recorded. A rejected candidate must have a technical reason rather than being replaced reflexively with custom code.

## Canonical state

Stage 5 must add typed/versioned portable domain objects for transcript, translation, spoken replacement/alignment and dubbing review/acceptance. Canonical state references project-owned media by IDs/portable project paths. It never stores host absolute paths, raw engine commands, provider credentials or raw MLT XML.

## Capability boundaries

Semantic capabilities remain provider-neutral. Stage 5 is expected to compose or add capabilities such as:

```text
speech.transcribe
text.translate
speech.synthesize
audio.align
audio.measure_loudness
audio.replace_dialogue
subtitle.render
video.lip_sync          # optional
```

Local/free deterministic or model paths are preferred where viable. Remote/non-free offers remain optional and must pass the existing D-017 preparation/authorization boundary before execution.

## Imported and recorded speech

Imported/recorded speech is a first-class prepared-media path. TTS is not mandatory. A user can supply a project-owned recording, align/review it and accept it through the same workflow contracts as generated speech.

## Review boundary

Acceptance must be evidence-based. At minimum the review model should be able to represent:

- transcript/translation text being approved for the selected source evidence;
- timing coverage and overlap/gap observations;
- spoken replacement duration/synchronization observations;
- clipping/peak and loudness observations where measurable;
- source audio preservation policy (replace dialogue only, duck/mix, or full replacement when explicitly chosen);
- subtitle timing/text observations when subtitles are produced;
- optional lip-sync observations when that capability is used.

No remote model's self-reported success is sufficient for acceptance.

## Rendering

The editor state remains non-destructive. Heavy media generation and final mux/mix happen only through explicit render/preview/export operations. Browser preview remains a deterministic projection of an accepted/rendered artifact and never becomes a second editing authority.

## Initial implementation order

1. typed transcript/translation/alignment domain state;
2. project-owned audio extraction and import/read APIs;
3. local ASR candidate evaluation and baseline adapter;
4. transcript/translation editor workflow;
5. prepared recording/TTS speech path;
6. alignment, loudness and synchronization review;
7. accepted non-destructive dubbing state projected into MLT/editor state;
8. deterministic preview/render/export;
9. representative real-media/audio fixtures and browser workflow coverage on Windows/Linux.
