# Engineering Backlog

This is the durable queue behind the single handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices.

## P0 — Product Truth closure

Current active slice: `product-recovery-recipe-workspace-reconciliation`.

Recovered Product Orchestrator journeys now include Photo-to-Video, Visualizer, Targeted Edit (`free_project`), Dubbing, Music Video, Narrated Video, General Video, Story Video preparation and Commercial Product preparation.

Required closure for the active slice:

- separate the durable provider-neutral Recipe Registry from the narrower set of recipes truthfully advertised for new project creation;
- ensure every advertised recipe has an authoritative Product Orchestrator projection and owned visible workspace;
- fail closed for preserved-only recipes instead of mounting generic Editor, Continuity, Dubbing or direct performance surfaces;
- keep imported/recovered projects readable and exportable even when their workflow is not currently supported;
- keep `free_project` aligned with existing Targeted Edit ownership rather than broadening it into a second generic editor;
- keep Action Transfer, Digital Human and Performance/lip-sync outside the creation catalog until separately recovered through complete authorized workflows;
- preserve Project Store/domain stores as canonical, D-033 editor-command ownership and D-017 execution authorization boundaries;
- require exact Draft and Review heads to pass all five permanent CI jobs.

`main` branch protection remains an external repository-setting P0 until enabled in GitHub settings.

## P0 — Product usability evidence

Next planned slice after Product Truth closure: `product-usability-class-c-cold-start`.

Required closure:

- validate UV Studio from a user-equivalent clean state without repository knowledge, direct store writes or hidden readiness seeding;
- prove advertised task discovery, project creation, prerequisite guidance and representative supported outcomes through visible controls only;
- distinguish product defects from optional runtime/provider configuration requirements;
- preserve fail-closed behavior for unsupported recipes and missing capabilities;
- collect durable evidence that can be compared with the later installed Windows human-acceptance gate.

After Class C, installed Windows human acceptance on the packaged application remains a separate P0 gate before Stage 9 resumes.

## P1 — Additional portable-state and runtime hardening

- keep machine paths, secrets and runtime handles outside portable project state;
- maintain strict portable-JSON and corrupt-project isolation guarantees as project state expands;
- define a content-integrity strategy that avoids unnecessary full-file hashing while preserving Review/Accept/render/export trust;
- keep the current single-backend-process assumption explicit until inter-process locking/state is deliberately introduced;
- broaden Python lint/type/frontend unit/accessibility/coverage gates proportionately;
- make dependency/runtime support claims match CI (Python 3.11 is the continuously verified baseline);
- expand codec/container/device fixtures only when concrete compatibility risks justify them;
- retire transitional `/api/stages` after no supported product surface depends on it.

## P2 — Optional domain/product extensions

- sequence continuity remains optional typed/provider-neutral domain state; simple standalone clips must not inherit it automatically;
- broader `free_project` tool palette only after an explicit ownership/product decision;
- truthful Action Transfer / Digital Human journeys only when a complete authorized current workflow exists;
- recover Performance/lip-sync as an authoritative Product Orchestrator journey before advertising it again for new project creation;
- Story/Commercial production beyond their current preparation surfaces;
- optional performance/lip-sync setup UX improvements.

## P3 — Stage 9 release program

Only resume after Product Truth closure, Class C cold-start and installed Windows human acceptance are complete:

- clean-machine packaging and first-run checks;
- migration/recovery UX;
- signed release artifact verification;
- Windows installer/uninstaller/desktop host acceptance;
- release evidence and distribution hardening.
