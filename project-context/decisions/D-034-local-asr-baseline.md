# D-034 — Local ASR baseline for Stage 5

**Status:** Accepted

**Date:** 2026-08-13

## Context

Stage 5 needs speech transcription that can run on an ordinary Windows/Linux UV Studio installation without making a paid/cloud model mandatory and without coupling canonical project state to one ASR implementation.

The repository already defines the semantic `speech.transcribe` capability but deliberately had no concrete offer. The Stage 5 dubbing state and Command API are provider-neutral, so the ASR engine should remain an execution adapter that returns typed timing/text evidence rather than becoming part of the project schema.

Reuse-first evaluation considered three mature open-source paths:

1. **whisper.cpp** — compact native runtime, MIT, official Windows/Linux binaries, CPU baseline with optional accelerated builds, structured JSON output and timestamps;
2. **faster-whisper** — MIT, CTranslate2/Python integration, strong word-timestamp support and a useful alternative adapter when its Python/runtime footprint is acceptable;
3. **WhisperX** — BSD-2-Clause, valuable forced-alignment/diarization layer but materially heavier and therefore better treated as an optional alignment capability rather than a prerequisite for basic transcription.

## Decision

Use **whisper.cpp v1.9.2** as the initial local/free `speech.transcribe` baseline behind a UV-owned adapter.

Pinned upstream facts for the first integration:

- repository: `ggml-org/whisper.cpp`;
- release: `v1.9.2`;
- release target commit: `306c88f4d1286aec1bf96e544632897886af5501`;
- license: MIT;
- Ubuntu x64 release asset: `whisper-bin-ubuntu-x64.tar.gz`;
- Ubuntu x64 asset SHA-256: `46811a3ecf584307480a220b9ef5ff81b7b22dc41577cbc274ce3afc61f753b1`;
- Windows x64 release asset: `whisper-bin-x64.zip`;
- Windows x64 asset SHA-256: `49dcc16de826f20bd53d44f947a1ae49dfa81f86cad67a64d80820cb192d674a`.

The adapter ID is `local_whisper_cpp`; the initial offer ID is `local_whisper_cpp.speech_transcribe`.

## Runtime boundary

The whisper executable and model are **runtime configuration**, not portable project state.

Initial discovery contract:

```text
binary = UV_WHISPER_CPP_BIN, otherwise whisper-cli from PATH
model  = UV_WHISPER_CPP_MODEL
```

The offer is:

- `available` only when both a usable binary and model file are configured;
- `configuration_required` when the binary is available but the model is not configured;
- `unavailable` when the executable cannot be resolved.

Model identity/path must not be written into `project.json`, `timeline/dubbing-state.json`, transcript/translation state, or exported project archives. A future settings UI may manage installation/runtime preferences outside portable project content.

## Input boundary

Callers provide semantic inputs only:

```text
source_id
optional start_us / end_us
language = BCP-47-like tag or auto
```

They cannot provide:

- host filesystem source paths;
- model paths;
- raw whisper.cpp CLI arguments;
- shell commands;
- output paths;
- provider/model identity to persist into the project.

The adapter resolves source media through the Project Store, extracts a bounded 16 kHz mono WAV with FFmpeg when needed, executes `whisper-cli` with argv and `shell=False`, parses structured JSON, converts engine time offsets into integer project microseconds, then deletes temporary files.

The adapter result is execution evidence. Canonical transcript persistence still occurs through the UV dubbing domain/Command API and is bound to the current source SHA-256.

## Output boundary

The normalized result may contain:

```text
source_id
source range
language
segments:
  segment_id
  start_us
  end_us
  text
  optional confidence
```

Raw whisper.cpp JSON, absolute executable/model/temp paths and command lines are not canonical outputs.

## Alternatives retained

`faster-whisper` remains a valid future alternative offer for `speech.transcribe`; selecting whisper.cpp now does not make the semantic capability engine-specific.

WhisperX or another mature forced-alignment component should be evaluated separately for `audio.align`/word-level synchronization. It must not become a mandatory dependency of baseline transcription solely because Stage 5 may later benefit from tighter dubbing alignment.

## Consequences

- UV Studio gets a local/free CPU-capable transcription baseline without PyTorch in core dependencies.
- Windows and Linux can use pinned official upstream binaries.
- ASR model/runtime size stays outside the portable project format.
- Paid/cloud ASR remains optional through normal Capability Registry offers and D-017 authorization.
- Transcript review remains necessary; ASR output is not automatically accepted as canonical dialogue truth.
