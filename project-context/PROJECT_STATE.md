# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: stage-5-correctness-browser-e2e -->

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

PR #32's final implementation and review-context heads passed the five permanent CI checks on Ubuntu and Windows. The app-baseline jobs run unit/API integration, real FFmpeg/MLT media suites, HTTP smoke, frontend lint, high-severity dependency audit and production build.

Real-media Stage 5 evidence proves that accepted dubbing replaces only the accepted target range, preserves original audio before/after the range and preserves expected output duration.

PR #33 established the explicit idle/draft/review lifecycle. Its post-merge closure head `453832323bcf992714863a4ccc7675c8102b6ba2` passed all five permanent checks while `active_slice` was null.

PR #34's implementation head `775b2a5d4bac687b0375a129ad56cf77a66a604e` passed the full required PR CI run `31799027680`. The final review head `e0f143dcb25e3e8a3190f86b92230fd0af11d0de` then passed exact-head PR run `31800185611`: development-context, Ubuntu/Windows bootstrap, and Ubuntu/Windows app-baseline were all green.

Both final app-baseline jobs passed API integration, HTTP smoke, real FFmpeg/MLT media evidence, frontend lint, high-severity dependency audit and production build. The permanent Playwright browser user-outcome scenario passed on both Ubuntu and Windows: create a project through the production UI, complete targeted media replacement through Review -> Accept -> render, then complete transcript translation, PreparedSpeech import/binding, dubbing Review -> Accept and dubbing master render. Browser CI preserves backend/frontend logs, full unittest output, failure screenshots when applicable and a success outcome report.

## Stage 5 hardening complete

PR #34 closed the bounded post-merge audit findings before Stage 6:

- explicit current/superseded semantics for dubbing Review history;
- immutable translation identity across target language and dubbing identity;
- explicit selection of newly created TTS takes;
- transaction-sized transcript/translation mutation versus PreparedSpeech binding checks;
- current-byte source/prepared-audio/replacement integrity at Review/Accept/render trust boundaries;
- retirement of the unsupported legacy VideoClaw root workspace;
- maintained browser E2E for the targeted existing-video and dubbing user outcomes on both continuous engineering targets.

The PR was reviewed with no unresolved review threads and merged at `e98015da54834a2684e075ede121847df59eda0a`. This closure returns repository lifecycle memory to explicit `idle` without product implementation changes.

## Cross-cutting backlog

Remaining non-blocking debt includes recursive portability validation for general JSON mappings, broader codec/device fixtures, measured Python/frontend quality gates, dependency reproducibility hardening, stronger renderer file-handle/TOCTOU hardening at media trust boundaries and eventual retirement of transitional compatibility surfaces such as `/api/stages`.

## Development-memory lifecycle

D-038 keeps one canonical active slice. The repository is idle after `stage-5-correctness-browser-e2e`; `active_slice` is null and `last_completed` records PR #34 plus merge commit `e98015da54834a2684e075ede121847df59eda0a`. The declared handoff remains `stage-6-sequence-continuity-review`, which may start only after this idle closure head passes the permanent CI matrix.
