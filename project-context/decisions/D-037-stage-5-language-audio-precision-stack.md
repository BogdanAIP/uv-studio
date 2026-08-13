# D-037 — Stage 5 reusable language/audio precision stack

Status: Accepted
Date: 2026-08-13
Slice: `stage-5-dubbing-translation`

## Decision

Stage 5 follows the project-wide reuse-first/orchestration-first rule. UV Studio owns portable project state, workflow gates and adapter boundaries; mature external engines remain replaceable runtime capabilities rather than becoming the project model.

### Speech recognition

- Keep `whisper.cpp` as the local/free baseline for `speech.transcribe`.
- ASR output is a draft. It cannot mutate canonical transcript state directly.
- `accept_asr_transcript` rebinds the reviewed text to the current project-owned source revision before persistence.

### Translation

- Use Argos Translate as an optional local/free `text.translate` offer when its runtime and the required installed language pair are present.
- Do not make Argos or language packages core dependencies.
- Provider/model/package identity is runtime configuration, not portable project state.
- Translation output remains a draft until the user/agent explicitly accepts it through the shared editor Command API.

Argos was selected because it is MIT-licensed, offline-capable and maintained. Its August 2026 upstream dependency cleanup also makes it materially more suitable as a lightweight optional runtime than older releases that pulled a heavier NLP stack.

### Speech synthesis

- Reuse the existing `speech.synthesize` capability instead of creating another TTS subsystem.
- The currently available Edge TTS path is remote/free and remains protected by D-017 one-shot `remote_execution` consent.
- The UI must show the exact text that will be sent and require an explicit one-time acknowledgement before authorization.
- A generated audio artifact is not automatically trusted as PreparedSpeech. UV Studio copies it into the project `assets/` boundary, re-hashes it, re-probes it and then attaches the resulting PreparedAudio through the same PreparedSpeech → Review → Accept path used by imported or recorded speech.

### Forced alignment

- Keep simple duration-window checking separate from forced alignment. `timing_pass` must never be presented as word/phoneme alignment or lip-sync evidence.
- Use WhisperX only as an optional precision-layer for `audio.align`.
- Evaluated upstream: `m-bain/whisperX`, BSD-2-Clause, active in 2026; API surface is `load_align_model(...)` + `align(...)` returning word-level `word/start/end/score` data.
- The evaluated precision stack is intentionally not a core dependency because it brings a heavy Torch/torchaudio/torchvision/pyannote/transformers-class runtime.
- WhisperX execution is available only when the optional runtime is installed and `UV_STUDIO_WHISPERX_MODEL_DIR` points to an existing local model cache.
- Hidden model downloads are disabled (`model_cache_only=True`).
- `audio.align` accepts only `take_id`; script, language, audio path and revision identity are derived server-side.
- Engine output remains an alignment draft. `accept_dubbing_alignment` re-derives the current take/script/audio SHA bindings, target range and language before writing provider-neutral alignment marks to Project Store.

### Alignment state

Canonical alignment state is `timeline/dubbing-alignments.json`, schema version 1.

It stores only portable data:

- prepared-speech take ID and exact take revision SHA;
- script kind/ID/SHA;
- audio ID/SHA;
- language and optional transcript segment ID;
- exact source target range in integer microseconds;
- ordered typed `word` / `token` / `phoneme` marks with audio-relative microsecond ranges and optional confidence.

It must not store WhisperX model names, provider names, host paths, CUDA devices or runtime cache locations.

Any current take, script, audio, range or language mismatch makes an alignment stale and invalid fail-closed.

### Subtitles

- WebVTT export is a built-in local/free deterministic projection from current canonical transcript/translation state.
- It is not a second subtitle editing model.
- Canonical timing remains integer microseconds. WebVTT timestamps are an export projection at millisecond precision; exact source/script SHA bindings remain in artifact metadata.

### Dialogue/background preservation

Do not claim professional background preservation until a dedicated real-media evaluation selects an engine.

Current candidates include reusable open systems such as `audio-separator` and ClearerVoice-Studio. The archived Meta Demucs repository is not adopted as a new primary dependency.

Until evaluation evidence exists:

- `replace_source_audio_range` is the only accepted dubbing composition policy that may be materially rendered;
- `duck_source_mix` and `replace_dialogue_preserve_background` remain declared but fail closed;
- UI wording must not imply that ambience/dialogue stems were professionally separated.

## Consequences

1. Core UV Studio remains materially lighter than a monolithic Torch/WhisperX/TTS installation.
2. A project remains portable when optional language/audio engines are absent on another machine.
3. GUI, AI, scripts and MCP all consume the same capability and Command API boundaries.
4. Remote synthesis cannot bypass D-017.
5. Model output never silently becomes accepted project state.
6. Higher-quality engines can replace Argos, WhisperX or Edge TTS later without a project-format migration.
7. Professional background-preserving dubbing remains an explicit evidence-gated enhancement rather than an unsupported claim.
