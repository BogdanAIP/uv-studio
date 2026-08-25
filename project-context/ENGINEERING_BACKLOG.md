# Engineering Backlog

This is the durable queue behind the single handoff in `NEXT_TASK.md`. It does not authorize parallel implementation slices.

D-064 and D-065 are the current product-composition and shared-production-semantics authorities. Recipe/Stage/Product-Orchestrator work below is compatibility migration work unless explicitly described otherwise.

## P0 — Shared production semantics / first micro-drama proof

Next slice after Stage 12 lifecycle closure: `studio-v2-micro-drama-production-semantics`.

Required proof:

- shared Scene/Shot/Take/accepted-take contracts under `production/`;
- micro-drama Story/Characters/Locations/continuity extensions referencing shared identities;
- multiple Takes and one explicit accepted Take for a Shot;
- accepted project-owned material projected to canonical Timeline through one transaction;
- product-level undo/redo without split production/reference/timeline state;
- one semantic command path shared by GUI, Agent, scripts and MCP callers.

Freeze during this slice:

- no new product RecipeDefinition;
- no new Stage UI;
- no provider integration;
- no second timeline engine;
- no Agent-only mutation route.

## P0 — Application transactions / undo boundary — active PR #65

Implemented under review:

- file-first `ProjectUnitOfWork` with prepared journals and restart recovery;
- one commit across production JSON, project references/assets and canonical Timeline;
- durable portable transaction identity and project-level undo/redo;
- exact rollback proof with no split canonical state;
- shared timeline commands plus HTTP/Studio UI history controls;
- transactional source-media and Studio-export registration.

## P1 — User-visible Model Registry

Build a backend-owned Model Registry above Capability Registry.

Required properties:

- named model identity and provider;
- explicit user-visible model selection in relevant Studio tools;
- supported tool modes (`t2i`, image edit, `t2v`, `i2v`, start/end frame, etc.);
- model-specific option schema and bounds;
- availability, locality and cost facts;
- mapping to Capability Offer / Adapter / transport;
- Settings own connection/runtime configuration, not creative per-operation model choice;
- `Auto` may later be an optional policy, never the only model path.

The current donor-era `frontend/lib/modelRegistry.ts` and `workflowApi.ts` are not the target implementation.

## P1 — Project-scoped Job Manager

Required before broad image/video provider work becomes a normal product path:

- queued/running/succeeded/failed/cancelled lifecycle;
- durable project/job identity;
- progress when available;
- cancellation and safe retry;
- exact selected-model/input/output provenance;
- Project Store result registration;
- no ad-hoc background process as a competing canonical state store.

## P1 — First real Image AI vertical

After Model Registry + Job Manager:

`Inspector -> choose named model -> prompt/references/options -> D-017 if required -> job -> project-owned generated asset -> Media Bin -> AddClip command -> timeline`.

Acceptance must prove model identity remains visible to the user and no provider-specific branch leaks through unrelated frontend code.

## P1 — First real Video AI vertical

Repeat the same architecture for a named video model with only the modes/options that model actually supports. Long-running execution must use the Job Manager and register output/provenance before timeline use.

## P2 — Move proven specialist logic into Studio tools

Migrate one domain at a time; do not rewrite proven invariants.

Recommended order:

1. targeted edit -> selected Clip/Range `AI Edit`;
2. dubbing/translation -> selected Clip/Audio `Dubbing`;
3. Music Map/analysis -> selected audio `Analyze Music / Sync`;
4. continuity -> Scene/Shot/Character `Consistency`;
5. photo-to-video -> selected images `Arrange/Add to Timeline / Slideshow`;
6. visualizer -> selected audio `Visualizer`;
7. Story/Narrated/Commercial/Music Video -> optional templates, Agent-assisted setup and production policies rather than separate project engines.

## P2 — Project Model enrichment

Add only when a real vertical requires it:

- lightweight Scene/Shot state;
- GenerationRecord;
- later Character, Location, Voice and richer reference relationships;
- content-integrity strategy proportionate to large media;
- keep secrets, machine paths and runtime handles outside portable state.

Do not turn `project.json` into one giant schema; use versioned project-owned documents.

## P2 — Retire parallel modern truths

After v2 callers exist:

- inventory and retire/derive `GET /api/uv/projects/{project_id}/execution-plan`;
- stop treating recipe Product Orchestrator as modern product authority;
- retire Stage 8 workspaces after supported state has moved;
- make mandatory `recipe_id` compatibility-only through a versioned project migration;
- retain old project readability/import until migration evidence proves removal safe.

## P2 — Remove dead donor-era frontend/runtime surfaces

After import/call-site proof:

- `frontend/lib/workflowApi.ts`;
- old frontend `modelRegistry.ts` implementation;
- HomePage / WorkflowPanel / pipeline / stage / sandbox tails;
- unmounted old VideoClaw API assumptions;
- prove supported UV server/runtime works without vendored VideoClaw backend `sys.path` injection, then remove it if safe.

Keep donor provenance/licenses and selectively adapted primitives where useful.

## P2 — Architecture hardening

Still valuable from the pre-D-063 backlog:

- executable dependency-boundary tests for `projects`, `editor`, `capabilities`, application and API direction;
- handler/transport registries instead of central execution switches;
- strict portable JSON/corrupt-project isolation as state expands;
- explicit single-backend-process assumption until locking is deliberately introduced;
- proportionate lint/type/frontend accessibility/coverage gates;
- codec/container/device fixtures only when concrete compatibility risks justify them.

## P3 — Selective Windows release-stack restoration

Archived PR #59 / Release #395 is an engineering donor, not a product baseline.

After the Studio product spine is accepted, selectively port and re-prove:

- Rust/WebView2 native host;
- packaged backend/frontend/runtime;
- diagnostics/system-resource helpers worth retaining;
- immutable release payload/integrity gates;
- legal/dependency closure;
- NSIS installer/uninstaller;
- safe user-data preservation;
- installed launch/deep verification;
- A->B->A update/rollback.

Old #395 artifacts prove only the historical packaging implementation. Exact-head release evidence must be rerun for the accepted Studio code.

## Deferred repository administration

`main` branch protection is intentionally deferred by current development direction and is not part of the Studio-v2 implementation slices until explicitly requested.
