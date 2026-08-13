# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: chore-context-lifecycle-closure -->

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

## Known gaps before Stage 6

The repository audit after PR #32 found a bounded hardening slice that must close before sequence continuity starts:

- dubbing Review history has no explicit chronological identity; frontend selection must not infer recency from UUID ordering;
- an existing translation ID must not be silently retargeted to another language/dubbing identity;
- newly created TTS takes must become the explicit selected take instead of relying on ID-order fallback;
- transcript/translation binding checks and PreparedSpeech attachment need one transaction-sized Project Store lock boundary;
- accepted/review/render trust boundaries need verification against current media bytes rather than only stored metadata hashes;
- the legacy root VideoClaw workspace is still exposed by the product frontend although the UV-owned server intentionally does not mount its old backend routes;
- Stage 4C/5 roadmap user-outcome gates still lack browser E2E coverage.

## Cross-cutting backlog

After Stage 5 hardening, remaining non-blocking debt includes recursive portability validation for general JSON mappings, broader codec/device fixtures, measured Python/frontend quality gates, dependency reproducibility hardening and eventual retirement of transitional compatibility surfaces such as `/api/stages`.

## Development-memory lifecycle

D-038 upgrades repository context to an explicit `idle -> draft -> review -> idle` lifecycle. `ACTIVE_SLICE.json` may have `active_slice = null` only in `idle`; `last_completed` records the exact merged slice/PR/merge commit. A new development slice must start from an idle `main`, not from a merged branch that still claims to be active.

Repository-memory closure is process/documentation-only; its declared handoff is `stage-5-correctness-browser-e2e`. Stage 6 remains blocked until that hardening slice is merged and the repository returns to idle.
