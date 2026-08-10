# UV Studio Roadmap

The roadmap targets the full product. Early stages create useful working slices, but the architecture must remain compatible with later stages.

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
- import/export archive;
- migrations/backups;
- Projects UI.

Exit: close/reopen application and resume project without data loss.

## Stage 2 — Recipe Registry

Goal: one studio supports different tasks without one mandatory pipeline.

- recipe schema/registry;
- required/optional capabilities;
- UI schema/progressive disclosure;
- wrap existing VideoClaw pipelines;
- add `general_video` and rename narrated semantics clearly.

Exit: user selects a task, and only relevant workflow/UI loads.

## Stage 3 — Capability Bridge

Goal: stable semantic interface to replaceable external/local capabilities.

- image/video/speech/media-understanding capability contracts;
- OpenClaw Gateway integration;
- exact provider/model selection for paid media;
- cost/error/job metadata;
- native VideoClaw integrations kept as fallback during migration.

Exit: core workflows call semantic capabilities instead of hard-coded providers.

## Stage 4 — Existing Video / Range Edit

Goal: edit only the requested range of an existing video.

- import/probe;
- timeline range selection;
- context before/after;
- deterministic FFmpeg operations;
- generative transform capability;
- replacement/reinsertion/preview.

Exit: replace/change a 5–10 second range without regenerating the whole video.

## Stage 5 — Dubbing / Translation

Goal: revoice an existing video without running filmmaking workflow.

- speech extraction;
- ASR;
- optional translation;
- speech synthesis/recorded voice;
- alignment/subtitles;
- optional lip-sync;
- mix/export.

Exit: existing video can be dubbed independently.

## Stage 6 — Optional Sequence Continuity & Review

Goal: robust linked-shot generation only where continuity matters.

- planned/observed state;
- locks/allowed changes;
- accepted/rejected takes;
- re-anchor policy;
- optional VLM take review;
- human confirmation fallback.

Exit: connected generated clips continue from accepted observed state; simple projects do not pay this complexity.

## Stage 7 — Music Video Mode

Goal: professional music-driven video workflow.

- integrate `musical-mv-storyboard` through adapter boundary;
- song/lyrics/structure analysis;
- Music Map UI;
- Music Director;
- music-aware shot timing;
- rhythm audit/final assembly.

Exit: 20–30 second music excerpt completes a music-aware production workflow.

## Stage 8 — Additional recipes

Goal: broaden product by composing existing primitives, not new engines.

- story video;
- commercial/product;
- photo-to-video;
- visualizer;
- performance/lip-sync;
- free project.

Exit: each mode is mostly recipe + capability mapping + minimal UI.

## Stage 9 — Desktop packaging and hardening

Goal: distributable Windows application.

- bundled frontend/backend/FFmpeg;
- launcher/updater strategy;
- migrations/backups/recovery;
- cancellation/logging;
- security and license audit;
- CI/golden regression projects;
- documentation/sample projects/release build.

Exit: user installs UV Studio without manually preparing Python/Node.

## Permanent regression scenarios

A. 30–60 s general video without required song/narration.  
B. 60 s narrated video with visuals/subtitles.  
C. 20–30 s music-video excerpt.  
D. Existing-video dubbing.  
E. 5–10 s targeted existing-video edit.

Major architecture must remain compatible with all five scenarios.