# Dubbing and Translation Architecture

**Status:** CURRENT SUPPORTING DOMAIN CONTRACT  
**Product role under D-064:** contextual Studio tool; distinct from `dub_battle`

## Canonical reusable workflow

```text
project-owned source
 -> transcript / ASR draft
 -> explicit transcript acceptance
 -> optional translation draft
 -> imported/recorded/synthesized speech
 -> alignment/timing/loudness evidence
 -> explicit Review
 -> accepted dubbing state
 -> deterministic render / subtitles
```

Draft-producing model operations do not directly mutate accepted state. Bindings remain project/source/script/audio identity-based; credentials and raw engine state stay outside portable project state.

## Reusable implementation

The repository contains tested local/optional components including whisper.cpp transcription, optional Argos translation, D-017-authorized remote synthesis compatibility, optional WhisperX alignment, FFmpeg/FFprobe media composition/evidence, MLT projection and deterministic WebVTT export.

Only execution modes backed by current capability evidence are advertised; unavailable separation/mix behavior remains fail-closed.

## D-064 placement

Ordinary dubbing/translation is a contextual tool that may be invoked inside any suitable Production Direction. It must migrate onto the shared Studio/Application Command + Project Unit of Work boundary rather than define a separate project engine.

`dub_battle` is different: it is a Production Direction organized around source scene, characters, dialogue, cast, recording takes and final mix. It may reuse this domain implementation without making ordinary dubbing a top-level project identity.

## Current architectural debt

Existing dubbing state/API/UI is valuable compatibility/domain code, but some paths predate the modern Studio Core. Migration should preserve tested review/integrity behavior while moving user-facing actions into direction/tool surfaces and coordinated transactions.

Historical Stage-5 hardening lists and PR-specific status are retained in Git history; they are not the current next-slice plan.
