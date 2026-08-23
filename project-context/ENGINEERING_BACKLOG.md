# Engineering Backlog

This is the durable queue behind the single handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices.

## P0 — Product truth and repository contract hygiene

Current active slice: `product-recovery-repository-hygiene`.

Required closure:

- keep Product Truth Matrix, Product Orchestrator docs and repository context aligned with the recovered Photo, Visualizer, Targeted Edit, Dubbing and Music journeys;
- retire obsolete addressable `/pipelines/standard`, `/pipelines/action-transfer`, `/pipelines/digital-human` and `/sandbox` frontend routes rather than remounting their historical backend runtime;
- fix the Dubbing `accept_dubbing_review` request contract so optional `accepted_id` survives the Product Orchestrator boundary;
- remove dead Music projector code where behavior remains protected by the current integrity checks;
- record the Project Store portable-JSON/corruption assessment as an explicit separate hardening contract;
- keep `main` branch protection recorded as an external repository-setting P0 until it is enabled in GitHub settings.

Do not restart Stage 9 from this slice.

## P0 — Project Store portable JSON and corruption isolation

Next slice after repository hygiene: `project-store-portable-json-hardening`.

Required closure:

- recursively validate `ProjectDocument.settings`, `ProjectDocument.extensions` and `ProjectReference.metadata` as portable JSON values rather than accepting arbitrary nested Python objects;
- reject `NaN`, `Infinity` and `-Infinity` at canonical model/write/import boundaries and serialize with strict JSON semantics;
- define stable errors for invalid nested values so callers cannot persist non-portable state through create/update/save/import paths;
- isolate corrupt projects during listing so one malformed or invalid project does not hide healthy projects;
- preserve the corrupt project on disk for diagnosis/recovery rather than silently deleting or rewriting it;
- add focused tests for create, update, save, archive/import, reopen and list behavior, including nested non-finite values and one-corrupt-project/multiple-healthy-project cases;
- keep project identity/path validation and existing atomic-write guarantees intact.

This is foundation-level persistence work and must be completed before Narrated/General orchestration adds more canonical project state.

## P0 — Remaining Product Truth Recovery

After Project Store hardening:

1. `product-recovery-narrated-orchestration` — recover the canonical script/narration/visual/assembly journey without a duplicate workflow store;
2. `product-recovery-general-orchestration` — establish a truthful general production journey rather than advertising incomplete legacy behavior;
3. reconcile any remaining recipe/workspace leakage and readiness-blind creation behavior exposed by those migrations.

All recovered journeys must preserve Project/domain stores as canonical and route provider/runtime execution through Capability Registry/D-017.

## P1 — Additional portable-state and runtime hardening

- keep machine paths, secrets and runtime handles outside portable project state;
- define a content-integrity strategy that avoids unnecessary full-file hashing while preserving Review/Accept/render/export trust;
- keep the current single-backend-process assumption explicit until inter-process locking/state is deliberately introduced;
- broaden Python lint/type/frontend unit/accessibility/coverage gates proportionately;
- make dependency/runtime support claims match CI (Python 3.11 is the continuously verified baseline);
- expand codec/container/device fixtures only when concrete compatibility risks justify them;
- retire transitional `/api/stages` after no supported product surface depends on it.

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
