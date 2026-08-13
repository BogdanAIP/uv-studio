# Engineering Backlog

This is the durable queue behind the single handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices.

## P0 — Stage 5 correctness + browser user gate

The next implementation slice is `stage-5-correctness-browser-e2e`.

Required closure:

- explicit chronological/current semantics for dubbing Review history;
- immutable translation identity across target language and dubbing identity;
- deterministic explicit selection of newly created TTS takes;
- transaction-sized locking around transcript/translation mutation versus PreparedSpeech bindings;
- current-byte integrity verification at accepted media trust boundaries;
- remove or explicitly isolate the legacy root VideoClaw workspace whose old APIs are not mounted by the UV-owned server;
- browser E2E for the targeted existing-video and dubbing user workflows;
- focused regression tests for each audit finding.

## P1 — Portable-state and runtime hardening

- recursively reject non-finite/non-JSON values in general `settings`, `extensions` and reference metadata before persistence;
- keep machine paths, secrets and runtime handles outside portable project state;
- define a content-integrity strategy that avoids unnecessary full-file hashing on every read while making Review/Accept/render/export identities trustworthy;
- keep the current single-backend-process assumption explicit until inter-process locking/state is deliberately introduced;
- broaden Python lint/type/frontend unit/accessibility/coverage gates proportionately;
- make dependency support/reproducibility claims match CI (currently Python 3.11 is the continuously verified runtime);
- expand codec/container/device fixtures when concrete compatibility risks justify them;
- retire transitional `/api/stages` once no supported product surface needs it.

## P2 — Stage 6 optional sequence continuity

After P0 closes, implement optional typed/provider-neutral planned/observed continuity state, locks/allowed changes, accepted/rejected takes, re-anchor policy and evidence-based review. Simple standalone clips must not inherit this complexity.

## P3 — Later product program

- Stage 7 music-video mode composed from existing primitives;
- Stage 8 additional recipes;
- Stage 9 Windows productization, clean-machine packaging, migration/recovery UX and release hardening.
