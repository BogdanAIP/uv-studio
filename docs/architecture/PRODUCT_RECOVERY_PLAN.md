# UV Studio Product Recovery Plan

## Status

This is a release-blocking recovery plan discovered after the Stage 9 Windows installed-app review. PR #38 proved that package engineering, native hosting and release checks can be green while the product remains confusing and some advertised workflows are not actually executable.

The recovery does **not** restart UV Studio from scratch. It preserves Project Store, capability authorization, deterministic media adapters, portable workflow state and the archived Stage 9 packaging/native-shell work while repairing product truth and orchestration.

## Core diagnosis

The current repository contains strong individual layers that do not yet compose into one coherent product:

- Stage 3.5 correctly stopped mounting the complete legacy VideoClaw backend;
- some legacy frontend clients and recipe execution metadata still refer to historical `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models` and related routes;
- some visible recipes do not have a complete current UV-owned user journey;
- frontend components directly orchestrate several backend state machines and hidden prerequisites;
- D-033 selected reuse-first MLT/OpenCut foundations, but UV Studio has continued to grow custom editor/timeline behavior while MLT is mostly a projection/render adapter;
- informed E2E tests can pass with seeded state while a first-time user cannot discover the required path.

## Recovery principles

1. **Truth before polish.** A ready action must map to a reachable mounted execution path.
2. **Intent before internal state.** Users express outcomes; the product maps them to plans, capabilities, jobs, reviews and artifacts.
3. **Reuse before new editor code.** Do not expand a generic UV-owned NLE until D-033 is re-evaluated.
4. **One semantic action model.** GUI, AI, MCP and scripts converge on the same product semantics.
5. **Progressive disclosure.** Internal hashes, capability IDs and review objects are shown only when actionable.
6. **Unavailable means unavailable.** Setup-dependent or unfinished workflows are gated before the user starts them.
7. **Human outcome is a release gate.** Green CI does not override a failed installed-app journey.

## Target architecture

```text
User / AI / MCP / Script
          |
          v
   Product Orchestrator
          |
          +--> readiness / prerequisites / next actions
          |
          v
  UV semantic Command Model
          |
   +------+------------------+
   |                         |
Project Store         Capability Registry
   |                         |
   +-----------+-------------+
               v
 FFmpeg / MLT / local ML / MCP / provider adapters
```

The frontend renders product state and invokes semantic actions. It must not be the primary owner of workflow orchestration.

## Preserve

- canonical Project Store, archives, migrations and path boundaries;
- D-017 authorization and provider-neutral Capability Registry;
- provenance, cancellation and bounded jobs;
- deterministic FFmpeg operations, preview and render adapters;
- accepted edit/dubbing/music durable state;
- MLT where it provides proven editing/render value;
- Stage 9 immutable payload, packaged toolchain, installer/update/rollback and Rust/WebView2 host as archived engineering work.

## Refactor

- recipe readiness and execution planning;
- project workspace routing;
- targeted-edit, dubbing and music workflow presentation;
- story/commercial/free composition flows;
- setup diagnostics and prerequisite presentation;
- fragmented command/API boundaries.

## Retire after dependency proof

- stale frontend clients for unmounted legacy routes;
- unreachable donor UI components;
- redirect-only historical pipeline pages;
- execution targets pointing to routes not mounted by the UV-owned server.

No compatibility code is deleted without call-site evidence and regression tests.

## Re-evaluate

- OpenCut Classic: component reuse versus design donor only;
- MLT: real timeline engine versus projection/render adapter;
- scope of the UV-owned editor;
- supported VideoClaw compatibility boundary after Stage 3.5;
- which optional local ML runtimes are bundled, installable or deliberately external.

## Phase 1 — Product Truth Inventory

For every visible mode/control record:

- product intent;
- frontend route/component and handler;
- frontend API function;
- backend route;
- domain command/service;
- required capability/offer;
- actual adapter/runtime;
- user setup;
- expected state/artifact result;
- status: `working`, `working_with_setup`, `partial`, `misleading`, `dead`;
- cold-start evidence.

Deliverable: `docs/architecture/PRODUCT_TRUTH_MATRIX.md` plus contract tests.

Exit: every recipe and permanent scenario has one truthful owner path.

## Phase 2 — Repair recipe/execution truth

- remove stale launch targets;
- derive readiness from current UV-owned workflows/capabilities;
- expose `ready`, `setup_required`, `partial`, `unavailable` at the product boundary;
- expose structured prerequisites;
- hide or visibly gate incomplete modes;
- test every advertised executable target against mounted routes.

Exit: a ready recipe starts from a clean project through mounted current paths.

## Phase 3 — Product Orchestrator

Minimum projection:

```text
ProjectWorkflowState
- intent / recipe
- readiness
- current_outcome
- prerequisites[]
- next_actions[]
- active_jobs[]
- user_decisions[]
- recent_artifacts[]
- diagnostics[]
```

Each next action has a stable semantic ID, user-facing explanation, enabled state, structured prerequisites, bounded inputs, locality/cost/authorization metadata and expected result.

Orchestration is a projection over canonical domain state plus runtime availability, not a second canonical store.

## Phase 4 — Editor foundation decision

Before adding generic editor functionality, explicitly decide:

1. whether more OpenCut Classic code/components should be reused;
2. whether MLT should own more timeline operations behind UV commands;
3. or whether UV Studio should deliberately remain a bounded task-oriented editor/orchestrator.

Exit: one accepted ownership map for editor features.

## Phase 5 — Core journeys

### A. Targeted edit
`import -> select range -> describe change -> obtain replacement -> preview -> accept -> export`

### B. Dubbing
`import -> transcribe -> optional translate -> obtain speech -> preview -> accept -> export`

### C. Music video
`song -> analyze/propose structure -> review direction -> assets -> assemble -> rhythm review -> export`

### D. Narrated video
`topic/script -> narration -> visual plan -> assets -> assembly -> preview -> export`

### E. General video
`brief -> proposed visual plan -> assets/generation -> assembly -> preview -> export`

Internal Brief/Plan/Candidate/Review state remains durable where valuable, but ordinary users should see it only when a decision is required.

## Phase 6 — Additional recipes

- keep Photo -> Video and Visualizer as reference intent-to-result flows;
- turn Story/Commercial from preparation-only workspaces into orchestrated paths;
- keep Performance/Lip-sync visibly setup-gated;
- give Action Transfer/Digital Human real current paths or remove them from ready-mode presentation;
- keep Free Project focused on reusable tools rather than every specialized workflow at once.

## Phase 7 — Cold-start verification

Add a separate cold-start product regression class:

- clean Project Store and machine config;
- UI-only actions after launch;
- no API/helper pre-seeding of transcripts, plans, reviews, music maps or accepted edits;
- optional runtime setup only through user-visible documented surfaces;
- fail on unexplained disabled primary controls;
- fail when a ready mode cannot reach an artifact/result.

Human installed-app acceptance remains mandatory.

## Phase 8 — Resume Stage 9

After the Product Truth Gate:

- reconcile the archived Stage 9 packaging/native-shell work with recovered product code;
- rebuild installer candidate;
- rerun integrity/legal/install/update/rollback/native-shell checks;
- repeat installed Windows human review;
- only then finish D-059 signing/timestamp/publication.

## Product Truth Gate

Stage 9 cannot become the maintained baseline until:

- every visible recipe/action has truthful readiness backed by current execution;
- zero advertised launch targets point to unmounted endpoints;
- stale legacy surfaces are retired or explicitly isolated;
- Product Orchestrator owns user-facing readiness/prerequisites/next-action projection;
- editor ownership/reuse direction is accepted;
- permanent scenarios A-E complete through UI without hidden state seeding;
- cold-start automation passes;
- Windows installed-app human review passes;
- preserved Stage 9 release/security/integrity gates remain green.
