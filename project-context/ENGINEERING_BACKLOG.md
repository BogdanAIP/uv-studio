# Engineering Backlog

This is the durable queue behind the single active handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices. The coordinator promotes one item at a time into `ACTIVE_SLICE.json`.

GitHub Issues are currently disabled for this repository, so these gaps remain repository-owned until issue tracking is enabled deliberately.

## P0 — Stage 3.5 runtime trust boundary

### Runtime security boundary

Close the active next slice from `NEXT_TASK.md`:

- raw provider credentials must not be returned by configuration APIs;
- real provider configuration must live outside the vendored source tree;
- transitional legacy secret files must be ignored defensively;
- wildcard CORS must not expose mutating localhost APIs to arbitrary browser origins;
- legacy sandbox/pipeline/provider execution must not bypass the product-owned D-017 authorization boundary;
- prefer a UV Studio-owned FastAPI root with explicitly mounted compatibility routes rather than permanent ownership by the complete upstream VideoClaw app.

### Dependency ownership

After the security slice:

- define UV Studio-owned core Python runtime requirements;
- split optional provider/runtime extras from baseline dependencies;
- stop receiving FastAPI/Uvicorn/Pydantic and provider SDKs only as incidental transitive state from vendored VideoClaw requirements;
- make optional Edge TTS/provider stacks actually optional in development installation;
- repair Next/ESLint compatibility and audit the known npm advisories;
- add explicit dependency-health gates to CI.

### Development-state lifecycle

The D-023 schema must gain a post-merge/idle or handoff-ready state so `main` cannot indefinitely declare an already-merged PR as active. Then extend validation toward trustworthy live diff-vs-write-scope enforcement and slice-specific quality gates.

## P0 — Stage 4A real mechanical verification

### Real FFmpeg golden E2E

Before treating targeted range mechanics as production-proven:

- create or generate small deterministic real fixtures with explicit provenance;
- cover representative CFR, VFR, with/without audio and non-zero timestamp cases;
- execute real `video.extract_range` and `video.replace_range` through the project adapters;
- probe and assert actual boundaries, duration tolerance, geometry, stream presence and rollback behavior;
- run without media downloads on Ubuntu and Windows;
- preserve useful diagnostics without leaking host paths/secrets into portable state.

### Media-edit state scalability

Current reinsertion deliberately produces a whole FFV1/FLAC lossless intermediate. Preserve that correctness baseline, but do not make full lossless re-encoding after every edit the permanent project model.

Evaluate and implement a project-owned non-destructive edit-decision/timeline representation so repeated short edits can remain lightweight and full media rendering happens at an explicit preview/export gate.

Refactor the FFmpeg adapter shape before operation growth turns inheritance into an adapter-on-adapter chain: one facade, shared path/probe/subprocess primitives and operation-specific handlers.

## P1 — Stage 4B edit intelligence

### Provider-neutral range continuity brief

Build a versioned provider-neutral exact-range evidence/continuity contract only after the Stage 3.5 runtime gate and Stage 4A real-media evidence are trustworthy.

Required direction:

```text
exact ProjectMediaRange
  -> bounded project evidence
  -> mechanical source/probe facts
  -> optional observations with confidence/evidence
  -> replacement constraints
  -> review targets
```

Do not store provider/model/runtime IDs in canonical brief state. Prefer a dedicated typed/versioned document or extension contract over an unvalidated free-form blob.

### Complete targeted range-edit intelligence

- optional replacement preparation/generation behind existing semantic capabilities and D-017;
- independent review against bounded evidence and exact range identity;
- no silent retiming, provider downgrade or whole-video analysis by default;
- source audio policy and boundary continuity remain explicit.

## P1 — Stage 4C user outcome

Deliver the composed product path through the actual UI:

```text
open source video
  -> select exact range
  -> inspect bounded context
  -> review replacement brief/method
  -> prepare/generate replacement when needed
  -> preview in context
  -> accept/reject
  -> project-owned edit decision
  -> explicit export
```

Required quality:

- integer-microsecond-backed timeline selector;
- explicit failure/cost/authorization states;
- frontend unit and accessibility checks;
- browser E2E for the complete targeted range scenario;
- no manual API request required for completion.

## P1 — Project portable-state hardening

Canonical paths are already validated, but `settings`, `extensions` and reference `metadata` remain general JSON-like mappings.

Add proportionate typed portability enforcement:

- durable feature models use explicit versioned schemas;
- recursively reject non-finite/non-JSON data before persistence;
- machine-only paths/secrets/runtime handles are represented by explicit non-portable configuration references rather than embedded values;
- archive round-trips prove the portable contract.

Do not turn the small general project schema into one universal media schema.

## P1 — General quality gates

The current matrix still lacks some product gates:

- measured coverage policy;
- proportionate Python lint/type checks;
- frontend lint;
- browser E2E;
- dependency audit;
- real encoded-media assertions.

Add them as the corresponding product surfaces become real. Avoid blanket ignores over product source.

## P2 — Broaden replaceable capabilities

- local/free speech transcription baseline before optional cloud ASR;
- provider-neutral continuity/review adapters through existing capability and D-017 boundaries;
- explicit provider/model/cost choice for paid media generation;
- evaluate mature permissively licensed components per capability rather than extending VideoClaw by default;
- preserve FFmpeg/local tools for deterministic work and keep optional runtimes optional.

## P3 — Additional recipes and product modes

After Stage 4 user outcome and runtime trust boundaries are proven, compose existing primitives into dubbing, continuity-sensitive sequences, music-video mode and additional recipes rather than inventing new engines per mode.

## P3 — Windows product distribution

Stage 9 remains the release/productization epic rather than the first place security and verification occur:

- bundled/provisioned backend, frontend and FFmpeg;
- launcher, installer/uninstaller and update/rollback strategy;
- project migrations, backups, logs, cancellation and recovery UX;
- clean-machine and weak-hardware verification;
- final release license/security/dependency audit building on earlier gates;
- signed release artifacts;
- no developer Python, Node/npm or manual FFmpeg requirement for baseline users.
