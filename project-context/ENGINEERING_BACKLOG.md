# Engineering Backlog

This is the durable queue behind the single active handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices. The coordinator promotes one item at a time into `ACTIVE_SLICE.json`.

GitHub Issues are currently disabled for this repository, so these gaps remain repository-owned until issue tracking is enabled deliberately.

## P0 — Complete the Stage 4 user outcome

### Provider-neutral range continuity brief

Build the next slice specified in `NEXT_TASK.md`: exact range identity, bounded evidence, mechanical constraints derived from project/probe facts, partial typed observations and review targets that survive archive round-trip.

### Complete targeted range-edit flow

Deliver the composed product path:

```text
select range
  -> continuity brief
  -> optional replacement preparation/generation
  -> independent review
  -> deterministic reinsertion
  -> preview
  -> explicit export
```

Do not make VideoClaw, Qwen, another model/provider or a paid API mandatory. Product-domain state is UV Studio-owned; implementations remain replaceable adapters.

## P1 — Production verification and product UI

### Real FFmpeg golden E2E

- create or generate a tiny deterministic VFR + single-audio fixture with explicit provenance;
- execute real `video.extract_range` and `video.replace_range` through project adapters;
- probe and assert actual boundaries, duration tolerance, geometry and stream presence;
- run without media downloads on Ubuntu and Windows;
- preserve useful diagnostics and rollback assertions.

### Frontend range workflow and browser E2E

- timeline/range selector backed by integer microseconds;
- context, brief and review surfaces;
- prepared replacement selection and reinsertion;
- before/after preview and explicit failure/cost states;
- frontend unit tests, accessibility checks and browser E2E;
- no silent mutation of the requested interval.

### Quality gates and dependency health

Current verified findings:

- `npm run lint` fails because the ESLint 9 flat configuration consumes an incompatible `extends`-based configuration;
- `npm ci` reports six high-severity advisories requiring path-by-path audit rather than blind upgrades;
- CI lacks measured coverage, Python lint/type checks, frontend lint and browser E2E.

Acceptance requires a documented dependency audit, green frontend lint in CI, proportionate Python lint/type/coverage gates and no blanket ignores over product source.

### Agent workflow hardening after schema v1

- compare pull-request changed paths with `ACTIVE_SLICE.json.write_scope` using trustworthy GitHub diff data;
- validate local/push branch identity when a reliable ref is available;
- evolve `required_checks` from the schema-v1 exact baseline into a validated CI catalog that can add slice-specific lint/E2E gates without code duplication.

## P2 — Broaden replaceable capabilities

- local/free speech transcription baseline before optional cloud ASR;
- provider-neutral continuity/review adapters through existing capability and D-017 boundaries;
- explicit provider/model/cost choice for paid media generation;
- evaluate mature permissively licensed components per capability rather than extending VideoClaw by default;
- preserve FFmpeg/local tools for deterministic work and keep optional runtimes optional.

## P3 — Windows product distribution

Stage 9 remains the packaging epic:

- bundled/provisioned backend, frontend and FFmpeg;
- launcher, installer/uninstaller and update/rollback strategy;
- project migrations, backups, logs, cancellation and recovery;
- clean-machine and weak-hardware verification;
- signed release artifacts;
- no developer Python, Node/npm or manual FFmpeg requirement for baseline users.
