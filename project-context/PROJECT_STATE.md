# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-5-correctness-browser-e2e -->

**Updated:** 2026-08-13

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 5 is merged on `main` through PR #32 / merge commit `6f7531d9b87f569074a632972ca11e36562e8bd7`.

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
- deterministic accepted dubbing render, project-owned WebVTT export and bounded artifact download.

## Architecture invariants

- Project Store/domain state is canonical. MLT, FFmpeg, VideoClaw compatibility code and optional model runtimes are adapters/engines, not second project authorities.
- Reuse-first/orchestration-first is mandatory for general editor/media primitives.
- GUI, scripts, AI and MCP must converge on UV-owned semantic commands/workflows; direct canonical-state mutation is not an automation API.
- Remote/non-free execution stays behind D-017.
- Optional continuity, dubbing, music and other specialized workflows must remain optional.
- Windows and Linux remain continuous engineering targets.

## What is verified

PR #32's final implementation and review-context heads passed the five permanent CI checks on Ubuntu and Windows. The app-baseline jobs run unit/API integration, real FFmpeg/MLT media suites, HTTP smoke, frontend lint, high-severity dependency audit and production build.

Real-media Stage 5 evidence proves that accepted dubbing replaces only the accepted target range, preserves original audio before/after the range and preserves expected output duration.

PR #33 then established the explicit idle/draft/review lifecycle. Its post-merge closure head `453832323bcf992714863a4ccc7675c8102b6ba2` passed all five permanent checks while `active_slice` was null.

## Stage 5 hardening in progress

This slice closes the bounded post-merge audit findings before Stage 6:

- explicit current/superseded semantics for dubbing Review history;
- immutable translation identity across target language and dubbing identity;
- explicit selection of newly created TTS takes;
- transaction-sized transcript/translation mutation versus PreparedSpeech binding checks;
- current-byte source/prepared-audio integrity at Review/Accept/render trust boundaries;
- removal or explicit isolation of the unsupported legacy VideoClaw root workspace;
- browser E2E for the targeted existing-video and dubbing user outcomes.

## Cross-cutting backlog

After Stage 5 hardening, remaining non-blocking debt includes recursive portability validation for general JSON mappings, broader codec/device fixtures, measured Python/frontend quality gates, dependency reproducibility hardening and eventual retirement of transitional compatibility surfaces such as `/api/stages`.

## Development-memory lifecycle

D-038 keeps the repository in `draft` for this single active slice. The declared handoff is `stage-6-sequence-continuity-review`, but Stage 6 remains blocked until this slice merges, closes back to `idle`, and its closure CI is green.
