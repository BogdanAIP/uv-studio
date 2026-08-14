# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-6-sequence-continuity-review -->

**Updated:** 2026-08-14

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 5 is merged on `main` through PR #32 / merge commit `6f7531d9b87f569074a632972ca11e36562e8bd7`, with the bounded post-merge hardening completed by PR #34 / merge commit `e98015da54834a2684e075ede121847df59eda0a`.

UV Studio currently has:

- UV-owned FastAPI runtime and secret/configuration boundary;
- canonical file-first Project Store and portable `.uvproj.zip` archives;
- provider-neutral Recipe Registry and Production Policy;
- semantic Capability Registry with local, MCP and exact native compatibility adapters;
- D-017 exact one-shot authorization for remote/non-free execution;
- MLT behind a UV-owned editor adapter and FFmpeg as the deterministic authoritative media/render layer;
- complete targeted existing-video range workflow through Brief -> Plan -> Candidate -> Review -> Accept -> render/preview;
- Stage 5 transcript/translation/PreparedSpeech/alignment/review/accepted-dubbing state;
- local whisper.cpp ASR baseline, optional Argos translation and optional WhisperX alignment;
- D-017-protected Edge TTS reuse;
- deterministic accepted dubbing render, project-owned WebVTT export and bounded artifact download;
- maintained production-browser E2E for the targeted replacement and dubbing user outcomes on Ubuntu and Windows.

## Architecture invariants

- Project Store/domain state is canonical. MLT, FFmpeg, VideoClaw compatibility code and optional model runtimes are adapters/engines, not second project authorities.
- Reuse-first/orchestration-first is mandatory for general editor/media primitives.
- GUI, scripts, AI and MCP must converge on UV-owned semantic commands/workflows; direct canonical-state mutation is not an automation API.
- Remote/non-free execution stays behind D-017.
- Optional continuity, dubbing, music and other specialized workflows must remain optional.
- Windows and Linux remain continuous engineering targets.

## What is verified

PR #34's final review head `e0f143dcb25e3e8a3190f86b92230fd0af11d0de` passed exact-head PR run `31800185611`: development-context, Ubuntu/Windows bootstrap and Ubuntu/Windows app-baseline were all green, including the permanent Playwright browser user-outcome scenario on both operating systems.

PR #34 merged at `e98015da54834a2684e075ede121847df59eda0a`. The mechanical idle closure head `9f47f5ac2e4c6cc608162550313894bdb6e194ae` then passed push run `31801356588` with all five permanent checks green, including browser E2E on Ubuntu and Windows. This satisfies the Stage 6 entry gate.

## Stage 6 sequence continuity/review in development

The active slice is `stage-6-sequence-continuity-review`. Its scope is optional linked-shot continuity only where an accepted prior shot/take must constrain a later shot. Standalone clips and existing one-shot workflows must remain free of sequence state and review overhead.

The initial architecture direction is:

- keep planned continuity distinct from observed accepted-take state;
- model explicit locks, allowed changes, take verdicts and re-anchor operations in provider-neutral project state;
- build bounded `TimelineContext` as a derived inspection view from canonical Project Store/media/transcript/timeline state rather than a second source of truth;
- add rendered-output evidence so automated/local checks or optional VLM review can inspect the actual produced take around continuity boundaries before human acceptance;
- route optional VLM/generation/review through the existing Capability Registry and D-017 authorization boundary;
- preserve a complete human/manual baseline when automated visual evidence is unavailable or uncertain;
- reuse existing D-029 continuity evidence concepts and mature external components only where they prove a missing general primitive.

`browser-use/video-use` is being evaluated as an MIT architecture donor for compact text-plus-on-demand-visual context and rendered-output self-review, not as a direct project/session authority or mandatory dependency. PySceneDetect is being evaluated only as an optional deterministic shot-boundary helper; Stage 6 does not make either project canonical state.

## Cross-cutting backlog

Remaining non-blocking debt includes recursive portability validation for general JSON mappings, broader codec/device fixtures, measured Python/frontend quality gates, dependency reproducibility hardening, stronger renderer file-handle/TOCTOU hardening at media trust boundaries and eventual retirement of transitional compatibility surfaces such as `/api/stages`.

## Development-memory lifecycle

D-038 keeps one canonical active slice. `stage-6-sequence-continuity-review` is now the draft slice on `stage-6/sequence-continuity-review`, based on the verified idle main head `9f47f5ac2e4c6cc608162550313894bdb6e194ae`. The declared next handoff is `stage-7-music-video-mode`; it remains blocked until Stage 6 is reviewed, merged, closed back to idle and its post-merge checks are green.
