# Engineering Backlog

This is the durable queue behind the single handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices.

## P0 — Product truth and repository contract hygiene

Current active slice: `product-recovery-repository-hygiene`.

Required closure:

- keep Product Truth Matrix, Product Orchestrator docs and repository context aligned with the recovered Photo, Visualizer, Targeted Edit, Dubbing and Music journeys;
- retire obsolete addressable `/pipelines/standard`, `/pipelines/action-transfer`, `/pipelines/digital-human` and `/sandbox` frontend routes rather than remounting their historical backend runtime;
- fix semantic request-contract mismatches such as Dubbing `accepted_id` loss at the Product Orchestrator boundary;
- remove dead projector code where behavior is already covered by current integrity checks;
- keep `main` branch protection recorded as an external repository-setting P0 until it is enabled in GitHub settings.

Do not restart Stage 9 from this slice.

## P0 — Remaining Product Truth Recovery

After repository hygiene:

1. `product-recovery-narrated-orchestration` — recover the canonical script/narration/visual/assembly journey without a duplicate workflow store;
2. `product-recovery-general-orchestration` — establish a truthful general production journey rather than advertising incomplete legacy behavior;
3. reconcile any remaining recipe/workspace leakage and readiness-blind creation behavior exposed by those migrations.

All recovered journeys must preserve Project/domain stores as canonical and route provider/runtime execution through Capability Registry/D-017.

## P1 — Portable-state and corruption hardening

- recursively reject non-finite and otherwise non-JSON values in portable `settings`, `extensions` and reference metadata before persistence;
- quarantine corruption per project so one damaged project cannot make unrelated projects unavailable;
- keep machine paths, secrets and runtime handles outside portable project state;
- define a content-integrity strategy that avoids unnecessary full-file hashing while preserving Review/Accept/render/export trust;
- keep the current single-backend-process assumption explicit until inter-process locking/state is deliberately introduced;
- broaden Python lint/type/frontend unit/accessibility/coverage gates proportionately;
- make dependency/runtime support claims match CI (Python 3.11 is the continuously verified baseline);
- expand codec/container/device fixtures only when concrete compatibility risks justify them;
- retire transitional `/api/stages` after no supported product surface depends on it.

These items should be split into bounded hardening slices if they would broaden a product-recovery PR.

## P1 — Product usability evidence

- Class C cold-start validation from user-equivalent clean state, without implementation knowledge or hidden workflow-decision seeding;
- verify that every task advertised as ready can produce a real outcome through discoverable visible controls;
- installed Windows human acceptance on the actual packaged application;
- cold-start/recovery diagnostics that distinguish product defects from missing optional runtimes/providers.

## P2 — Optional domain/product extensions

- sequence continuity remains optional typed/provider-neutral domain state; simple standalone clips must not inherit it automatically;
- broader `free_project` tool palette only after an explicit ownership/product decision;
- truthful Action Transfer / Digital Human journeys only when a complete authorized current workflow exists;
- Story/Commercial production beyond their current preparation surfaces;
- optional performance/lip-sync setup UX improvements.

## P3 — Stage 9 release program

Only resume after Product Truth Recovery plus Class C and installed Windows acceptance are complete:

- clean-machine packaging and first-run checks;
- migration/recovery UX;
- signed release artifact verification;
- Windows installer/uninstaller/desktop host acceptance;
- release evidence and distribution hardening.
