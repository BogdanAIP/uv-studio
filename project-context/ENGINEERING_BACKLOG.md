# Engineering Backlog

This is the durable queue behind the single handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices.

## P0 — Product Truth closure

Completed through `product-recovery-recipe-workspace-reconciliation` (PR #56, merge `44c853f00766795399de9addf74ba79cef2c35c4`).

Recovered Product Orchestrator journeys include Photo-to-Video, Visualizer, Targeted Edit (`free_project`), Dubbing, Music Video, Narrated Video, General Video, Story Video preparation and Commercial Product preparation. Preserved-only Action Transfer, Digital Human and Performance/lip-sync remain readable but are not advertised for new creation.

The creation catalog, Product Orchestrator projections and visible workspace routing now fail closed rather than mounting generic Editor, Continuity, Dubbing or direct performance surfaces for unsupported recipes. Project Store/domain stores remain canonical; D-033 editor-command ownership and D-017 execution authorization boundaries are unchanged.

`main` branch protection remains an external repository-setting P0 until enabled in GitHub settings.

## P0 — Product usability evidence

Class C cold-start is completed through `product-usability-class-c-cold-start` (PR #58, merge `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`). Exact Draft and Review heads passed all five permanent CI jobs, including browser user-outcomes on Ubuntu and Windows.

The remaining P0 product-usability gate is `product-usability-installed-windows-human-acceptance`:

- validate the packaged UV Studio application on an installed Windows system from first launch;
- verify normal task discovery, project creation, media import, prerequisite guidance and representative product workflows through the installed host;
- distinguish packaging/host failures from optional provider/runtime configuration requirements;
- preserve the Class C evidence as the CI comparison baseline rather than treating browser CI as installed-app acceptance;
- record durable human-acceptance evidence before Stage 9 resumes.

## P1 — Architecture and portable-state hardening

- reconcile the legacy `/api/uv/projects/{project_id}/execution-plan` compatibility projection with Product Orchestrator so UV Studio does not maintain two modern product truths;
- extract API-orchestrated use cases into a small `uv_studio/application/` layer without redesigning the domain core;
- add executable AST dependency-boundary tests for `projects`, `capabilities`, `editor`, `orchestration` and API/application direction;
- introduce a file-first `ProjectUnitOfWork` for multi-step project mutations and external-execution registration/rollback;
- extend development-context validation so durable backlog state cannot drift from `ACTIVE_SLICE.json`/handoff state;
- keep machine paths, secrets and runtime handles outside portable project state;
- maintain strict portable-JSON and corrupt-project isolation guarantees as project state expands;
- define a content-integrity strategy that avoids unnecessary full-file hashing while preserving Review/Accept/render/export trust;
- keep the current single-backend-process assumption explicit until inter-process locking/state is deliberately introduced;
- broaden Python lint/type/frontend unit/accessibility/coverage gates proportionately;
- make dependency/runtime support claims match CI (Python 3.11 is the continuously verified baseline);
- expand codec/container/device fixtures only when concrete compatibility risks justify them;
- retire transitional `/api/stages` after no supported product surface depends on it.

## P2 — Runtime and product extensions

- add a UV-owned Job Manager before long-running AI/provider work becomes a normal product path;
- replace central execution switches with explicit transport/capability-handler registries as provider count grows;
- generate frontend workflow/recipe contracts from backend OpenAPI/JSON Schema rather than maintaining manual duplicates;
- move frontend workspaces incrementally into feature-owned modules plus a workspace-renderer registry;
- remove legacy targeted-edit compatibility only after preserved unmigrated projects no longer require it;
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
