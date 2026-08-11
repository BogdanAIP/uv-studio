# UV Studio Roadmap

The roadmap targets the full product. Early stages create useful working slices, but the architecture must remain compatible with later stages.

## Initial product completion gate

The initial UV Studio program is complete when Stage 9 produces a distributable Windows release and the release candidate proves all five permanent regression scenarios through user-facing workflows rather than manual API calls.

The completion gate requires:

- clean-machine installation without a separately prepared Python, Node/npm or FFmpeg toolchain;
- canonical projects that survive restart, export/import, upgrade, backup and recovery;
- complete UI paths for general video, narrated video, music-video excerpt, dubbing and targeted existing-video range edit;
- local/free baseline implementations wherever a viable local path exists, with remote/paid providers remaining explicit optional choices;
- real media fixtures and evidence-based output checks on Windows and Linux;
- cancellation, diagnostics, migration and rollback behavior suitable for user data;
- license/security/dependency audit and signed release artifacts;
- no mandatory dependency on VideoClaw, Qwen, MCP, a particular model vendor or a paid API in canonical project state.

After this gate passes, additional recipes, providers and refinements belong to a versioned post-release backlog. They do not postpone the initial product indefinitely.

## Permanent architecture rules

- no single mandatory film/music/micro-drama pipeline;
- paid AI APIs are optional capabilities, never hidden baseline dependencies;
- prefer deterministic/local tools for deterministic work;
- local/free implementations may coexist with paid providers behind the same semantic capability;
- provider choice and expected paid cost must remain explicit for chargeable generation;
- capability discovery/ordering is metadata, not permission to execute or spend;
- professional workflow policy (source review, planning, sample-first generation, scene/take gates, evidence-based review) is separate from the provider that performs an AI operation;
- OpenClaw, Qwen-MM-Plugins and other MCP/runtime packages are optional adapters, not the canonical project state or mandatory execution layer;
- Windows remains a first-class target even when an optional third-party package currently requires WSL2.

## Stage 0 — Clean baseline

Goal: establish a reproducible modern VideoClaw-derived baseline and repository discipline.

- pin upstream `HITsz-TMG/VideoClaw` commit;
- import only modern `video-claw/video-claw` application paths required by runtime;
- preserve MIT notices;
- identify/remove unreachable historical code only after dependency checks;
- make backend/frontend start reproducibly;
- add baseline CI and smoke tests;
- document Windows setup;
- verify existing narrated, action-transfer, digital-human and film workflows where credentials are available.

Exit: clean buildable baseline with tracked upstream provenance.

## Stage 1 — Universal Project Store

Goal: project state survives chats, restarts and task failures independently of UI sessions.

- project schema/versioning;
- atomic local persistence;
- source/artifact/task references;
- validated `.uvproj.zip` project archives with checksums and traversal protection;
- import/export;
- backups/migrations/recovery helpers;
- Projects API/UI.

Exit: close/reopen application, export/import a complete project, and resume without data loss.

## Stage 2 — Recipe Registry + Production Policy

Goal: one studio supports different tasks without one mandatory pipeline, while professional production discipline is reusable across recipes.

- recipe schema/registry;
- required/optional capabilities;
- UI schema/progressive disclosure;
- wrap existing VideoClaw pipelines;
- add `general_video` and rename narrated semantics clearly;
- provider-neutral production policy hooks;
- source-review gate for workflows based on real footage;
- optional creative direction/taste contract;
- sample-first generation policy;
- scene/take ledger where multi-scene work needs it;
- plan/review gate contracts;
- evidence-based final review with timestamps/frame references;
- use/adapt suitable Apache-2.0 Qwen-MM-Plugins `video-edit` workflow ideas without inheriting its DashScope dependency.

Exit: user selects a task, only relevant workflow/UI loads, and recipes can opt into professional planning/review gates independently of model/provider choice.

## Stage 3 — Capability Registry & Adapters

Goal: stable semantic interface to replaceable local, MCP and provider capabilities without a mandatory intermediate runtime.

- semantic contracts for image/video/speech/media-understanding operations;
- capability registry with availability, locality, cost class and safe implementation metadata;
- separate registry metadata from `SelectionPolicy` and execution permission;
- fail-closed `local_free_first`: only `available + free + local`, never implicit remote/paid fallback;
- project-scoped local execution with no arbitrary shell/FFmpeg command surface;
- direct MCP client/adapter with explicit semantic tool bindings;
- local-tool adapter;
- native VideoClaw adapter during migration;
- optional OpenClaw adapter/runtime;
- optional Qwen-MM-Plugins profile/binding pack after generic MCP support is proven;
- exact provider/model selection for paid media;
- explicit consent/cost boundary before potentially-paid or paid execution;
- cost/error/job metadata;
- `local_free_first`, `pinned_offer`, `manual`, and later explicit best-available/budget-aware policies where their permission semantics are defined;
- never require DashScope for a baseline UV Studio feature when an adequate local/free path exists;
- keep Qwen cloud generation/Omni/video-memory capabilities optional for users who explicitly configure their API access.

Exit: core workflows call semantic capabilities; the same operation can be fulfilled directly, locally, through MCP, OpenClaw, Qwen-MM-Plugins, or a native provider without changing project-domain code, and no registry fallback can silently trigger chargeable work.

## Stage 4 — Existing Video / Range Edit

Goal: professionally edit only the requested range of an existing video.

- import/probe and actual source review before content decisions;
- timeline range selection;
- context before/after;
- deterministic FFmpeg operations for mechanical edits;
- edit-direction/pacing/audio-first/beat-sync policies where relevant;
- optional Scene Ledger for multi-scene edits;
- plan gate before designed assembly;
- sample-first rule for generated replacement assets;
- generative transform capability only when needed;
- replacement/reinsertion/preview;
- independent evidence-based review for production outputs;
- no silent downgrade from an approved method/provider to a weaker result.

Exit: replace/change a 5–10 second range without regenerating the whole video, while preserving surrounding context and giving designed edits a verifiable production workflow.

## Stage 5 — Dubbing / Translation

Goal: revoice an existing video without running filmmaking workflow.

- speech extraction;
- local/free ASR path (for example Whisper-compatible/WhisperX) as baseline;
- optional cloud ASR/Omni adapters;
- optional translation;
- speech synthesis/recorded voice;
- alignment/subtitles;
- optional lip-sync;
- mix/export;
- audio-preservation/loudness checks.

Exit: existing video can be dubbed independently without requiring a Qwen/DashScope or other paid media API.

## Stage 6 — Optional Sequence Continuity & Review

Goal: robust linked-shot generation only where continuity matters.

- planned/observed state;
- locks/allowed changes;
- accepted/rejected takes;
- re-anchor policy;
- optional VLM take review;
- human confirmation fallback;
- provider-neutral structured review schema;
- reuse professional scene/take gate concepts without forcing them on standalone clips.

Exit: connected generated clips continue from accepted observed state; simple projects do not pay this complexity.

## Stage 7 — Music Video Mode

Goal: professional music-driven video workflow.

- integrate `musical-mv-storyboard` through adapter boundary;
- song/lyrics/structure analysis;
- Music Map UI;
- Music Director;
- music-aware shot timing;
- beat-sync and audio-first editing craft;
- sample-first generated assets;
- rhythm audit/final assembly;
- evidence-based review of timing/scene transitions.

Exit: 20–30 second music excerpt completes a music-aware production workflow without making music mandatory for other video types.

## Stage 8 — Additional recipes

Goal: broaden product by composing existing primitives, not new engines.

- story video;
- commercial/product;
- photo-to-video;
- visualizer;
- performance/lip-sync;
- free project.

Exit: each mode is mostly recipe + capability mapping + production policy + minimal UI.

## Stage 9 — Desktop packaging and hardening

Goal: distributable Windows application.

- bundled frontend/backend/FFmpeg;
- launcher/updater strategy;
- migrations/backups/recovery;
- cancellation/logging;
- capability self-check and clear optional dependency diagnostics;
- security and license audit;
- CI/golden regression projects;
- documentation/sample projects/release build.

Exit: user installs UV Studio without manually preparing Python/Node; optional WSL/cloud integrations do not prevent normal native-Windows use.

## Permanent regression scenarios

A. 30–60 s general video without required song/narration.  
B. 60 s narrated video with visuals/subtitles.  
C. 20–30 s music-video excerpt.  
D. Existing-video dubbing.  
E. 5–10 s targeted existing-video edit.

Major architecture must remain compatible with all five scenarios and must not make a paid third-party API mandatory for scenarios that have a viable local/free implementation.
