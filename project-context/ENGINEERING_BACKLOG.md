# Engineering Backlog

This is the durable queue behind the single active handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices. The coordinator promotes one item at a time into `ACTIVE_SLICE.json`.

GitHub Issues are currently disabled for this repository, so these gaps remain repository-owned until issue tracking is enabled deliberately.

## Completed early gates

### Stage 3.5 runtime security boundary — completed

D-025 / PR #22 moved the product to a UV Studio-owned FastAPI root, separated machine secrets from public configuration, blocked untrusted browser origins before routing, removed unsafe legacy provider/sandbox/pipeline routes from the default application and kept runtime configuration outside `vendor/` and canonical Project Store data.

### Stage 3.5 dependency ownership — completed

D-026 / PR #23 made UV Studio own its core/dev dependency graph, removed full vendored VideoClaw backend requirements from baseline setup/CI, aligned Next/ESLint on 16.2.12 and made frontend lint, high-severity npm audit and production build permanent Ubuntu/Windows gates.

### Stage 4A deterministic real-media baseline — completed by the active PR after final merge gate

PR #24 executes real FFmpeg/FFprobe through `LocalFFmpegAdapter` on generated CFR/VFR/audio/no-audio/non-zero timestamp media on Ubuntu and Windows. It also proves observable replacement ordering, real produced-file rollback and records evidence under `project-context/evidence/STAGE_4A_REAL_MEDIA.md`.

D-027 records the measured state-model consequence: a one-second replacement in an eight-second 320x180 MPEG-4 source produced a complete FFV1 output **4.824x** the source size on both platforms. Whole-output FFV1 remains a deterministic render/intermediate path, not canonical repeated-edit state.

## P0 — Stage 4A non-destructive edit state

### Canonical edit decisions

The next active handoff is `stage-4-non-destructive-edit-state`.

Implement a small product-owned, provider-neutral, versioned edit-state contract so accepting a short edit does not automatically materialize a new complete lossless video.

Required direction:

```text
original project source
  + immutable exact ProjectMediaRange
  + accepted project replacement reference
  + deterministic ordering/overlap policy
  -> explicit preview/render/export projection
```

Required proof:

- project-relative source/replacement references only;
- multiple non-overlapping accepted edits remain lightweight;
- overlapping edits follow one explicit fail-closed policy;
- archive/export/import/reopen round trip preserves decisions exactly;
- missing/incompatible referenced media fails clearly;
- existing D-021/D-022 exact mechanics remain the render/correctness layer;
- no full-video FFV1 output is created merely because an edit decision is accepted.

### FFmpeg adapter shape

Refactor the FFmpeg adapter shape before operation growth turns inheritance into an adapter-on-adapter chain: one facade, shared path/probe/subprocess primitives and operation-specific handlers. Do this only where it materially helps the non-destructive projection/render boundary; do not rewrite working D-021/D-022 mechanics for style alone.

### Development-state lifecycle

D-023 still needs a post-merge/idle or handoff-ready state so `main` cannot indefinitely declare an already-merged PR as active. Then extend validation toward trustworthy live diff-vs-write-scope enforcement and slice-specific quality gates.

## P1 — Stage 4B edit intelligence

### Provider-neutral range continuity brief

Build a versioned provider-neutral exact-range evidence/continuity contract after the non-destructive edit-state boundary is proven.

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

## P1 — Remaining general quality gates

Already permanent: Ubuntu/Windows unit/API/HTTP, frontend production build, frontend lint, high-severity npm audit and deterministic real encoded-media assertions.

Still missing:

- measured coverage policy;
- proportionate Python lint/type checks;
- frontend unit tests;
- accessibility checks;
- browser E2E;
- broader device/container/codec media fixtures as concrete failures appear.

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
