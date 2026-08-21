# UV Studio Product Recovery Plan

## Status

This is a release-blocking recovery plan discovered after the Stage 9 Windows installed-app review. PR #38 proved that package engineering, native hosting and release checks can be green while the product remains confusing and some advertised workflows are not actually executable.

The recovery does **not** restart UV Studio from scratch. It preserves Project Store, capability authorization, deterministic media adapters, portable workflow state and the archived Stage 9 packaging/native-shell work while repairing product truth and orchestration.

## Product identity is not under recovery

UV Studio is already defined by `README.md` and `ROADMAP.md` as a desktop/local-first **video production and editing workspace** with task-specific workflows. Recovery must not turn the project into either a generic NLE clone or a workflow-only AI application.

Guided workflows, manual editing, AI actions, scripts and MCP are different ways to operate on one UV-owned project model. They are expected to converge on the same semantic/domain mutation boundaries.

## Core diagnosis

The repository contains strong individual layers that do not yet compose into one coherent product:

- Stage 3.5 correctly stopped mounting the complete legacy VideoClaw backend;
- some legacy frontend clients and historical execution metadata still describe removed runtime contracts;
- some visible recipes do not have a complete current UV-owned user journey;
- frontend components still reconstruct several backend state machines and hidden prerequisites;
- D-033 selected a reuse-first UV + MLT + OpenCut editor foundation, but the implementation needs a conformance audit before further generic editor growth;
- informed E2E tests can pass with seeded or implementation-aware state while a first-time user cannot discover the required path.

The D-033 audit is therefore an implementation-quality task. It is **not** permission to reopen product identity or to choose one winner between UV Studio, OpenCut and MLT.

## Recovery principles

1. **Truth before polish.** A ready action must map to a reachable mounted execution path.
2. **Intent before internal state.** Users express outcomes; the product maps them to plans, capabilities, jobs, reviews and artifacts.
3. **Reuse before new editor code.** D-033 remains the accepted baseline; new generic editor primitives require conformance evidence and reuse analysis first.
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
          +--> readiness / prerequisites / relevant workspaces / next actions
          |
          v
  UV semantic/domain commands
          |
   +------+------------------+
   |                         |
Project Store         Capability Registry
   |                         |
   +-----------+-------------+
               v
 FFmpeg / MLT / local ML / MCP / provider adapters
```

The frontend renders product state and invokes semantic actions. It must not be the primary owner of workflow orchestration or canonical timeline/domain state.

## Preserve

- canonical Project Store, archives, migrations and path boundaries;
- D-017 authorization and provider-neutral Capability Registry;
- provenance, cancellation and bounded jobs;
- deterministic FFmpeg operations, preview and render adapters;
- accepted edit/dubbing/music durable state;
- D-033 editor foundation: UV canonical state/commands + MLT adapter + selective OpenCut reuse;
- Stage 9 immutable payload, packaged toolchain, installer/update/rollback and Rust/WebView2 host as archived engineering work.

## Refactor

- recipe readiness and execution planning;
- project workspace routing;
- targeted-edit, dubbing and music workflow presentation;
- story/commercial/free composition flows;
- setup diagnostics and prerequisite presentation;
- mutation paths that bypass an existing UV semantic/domain command boundary;
- editor code that duplicates a mature reusable primitive without a recorded technical reason.

## Retire after dependency proof

- stale frontend clients for unmounted legacy routes;
- unreachable donor UI components;
- historical pipeline pages no longer reachable from the supported shell;
- execution targets pointing to routes not mounted by the UV-owned server;
- privileged mutation routes that duplicate/bypass the product-owned command model.

No compatibility code is deleted without call-site evidence and regression tests.

## D-033 conformance questions

These are implementation questions under the already accepted editor architecture:

- does every meaningful canonical editor mutation pass through a UV-owned semantic/domain command boundary?
- is MLT engine state derived/internal rather than a second public project authority?
- are current MLT responsibilities sufficient for the bounded editor features actually shipped, and are future generic mechanics delegated to it where D-033 intended?
- is OpenCut Classic being reused selectively where it removes real duplicated editor UI work, without inheriting its application/storage architecture?
- are browser-only playhead/selection/form states kept transient while durable edit identity remains in UV state?
- is authoritative export ownership still consistent with D-033 and its parity requirement?
- which transaction/undo-redo and GUI/scripts/AI/MCP convergence claims remain incomplete and need explicit follow-up evidence?

A D-033 amendment is justified only if reproducible evidence shows an accepted ownership boundary is technically unsuitable. Selective implementation incompleteness is not such evidence.

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

**Status:** completed as the D-062 recovery inventory; continue correcting it when implementation changes.

## Phase 2 — Repair recipe/execution truth

- remove stale launch targets;
- derive readiness from current UV-owned workflows/capabilities;
- expose `ready`, `setup_required`, `partial`, `unavailable` at the product boundary;
- expose structured prerequisites;
- hide or visibly gate incomplete modes;
- test every advertised executable target against mounted routes.

**Status:** base contract repair completed in PR #42. Non-migrated product journeys remain intentionally fail-closed.

## Phase 3 — Product Orchestrator

Minimum projection:

```text
ProjectWorkflowState
- intent / recipe
- readiness
- current_outcome
- prerequisites[]
- relevant_workspaces[]
- next_actions[]
- active_jobs[]
- user_decisions[]
- recent_artifacts[]
- diagnostics[]
```

Each next action has a stable semantic ID, user-facing explanation, enabled state, structured prerequisites, bounded inputs, execution/authorization metadata and expected result.

Orchestration is a projection over canonical domain state plus runtime availability, not a second canonical store.

**Foundation status:** implemented for **Photo → Video only** in PR #43. `compose_photos` delegates to the existing D-017 capability execution boundary. The UV-owned shell also isolates legacy pipeline/session/task/sandbox navigation. Visualizer still has a real deterministic capability path but is not yet migrated to Product Orchestrator. Other recipes remain explicitly partial until migrated.

When additional workflows are migrated, do not assume every semantic action is necessarily a capability execution. State/domain decisions such as approve/reject/accept may be owned by coherent UV domain commands without a provider capability ID.

## Phase 4 — D-033 editor conformance and clarification

D-033 is the accepted ownership map. This phase does **not** choose between “UV editor”, OpenCut and MLT. It compares the live implementation with D-033 and classifies differences as:

1. **conforming adaptation** — for example transient browser interaction state or selective OpenCut reuse that preserves UV canonical authority;
2. **incomplete implementation** — an accepted D-033 responsibility not yet fully implemented/proven;
3. **conformance defect** — a canonical editor mutation bypass, duplicate authority or unjustified general-purpose custom primitive;
4. **evidence-backed amendment candidate** — only where reproducible technical evidence shows the accepted boundary itself is unsuitable.

Current first bounded defect: accepted range edits are canonical D-028 timeline state, while the historical `DELETE /api/uv/projects/{project_id}/edits/{edit_id}` route mutates `RangeEditStateStore` directly. That removal path should converge on the editor Command API after call-site evidence and regression tests.

Exit:

- one current ownership/conformance map against D-033;
- contradictory recovery documentation corrected;
- concrete bypasses found by the audit removed or recorded as bounded follow-up;
- no generic NLE expansion during the audit;
- D-033 reaffirmed/clarified by default, or amended only with explicit reproducible counter-evidence.

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

Workspace presentation should increasingly come from Product Orchestrator `relevant_workspaces` rather than a parallel frontend recipe switch.

## Phase 6 — Additional recipes

- keep Photo → Video as the first orchestrated reference flow;
- migrate Visualizer as the second simple deterministic reference flow;
- turn Story/Commercial from preparation-only workspaces into orchestrated paths;
- keep Performance/Lip-sync visibly setup-gated;
- give Action Transfer/Digital Human real current paths or keep them unavailable/partial;
- keep Free Project focused on reusable tools rather than every specialized workflow at once.

## Phase 7 — Cold-start verification

Add a separate cold-start product regression class:

- clean Project Store and machine config;
- UI-only actions after launch;
- no API/helper pre-seeding of transcripts, plans, reviews, music maps or accepted edits;
- optional runtime setup only through user-visible documented surfaces;
- fail on unexplained disabled primary controls;
- fail when a ready mode cannot reach an artifact/result;
- fail when irrelevant specialist workspaces dominate the selected task.

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
- Product Orchestrator owns user-facing readiness/prerequisites/relevant-workspace/next-action projection for supported journeys;
- D-033 conformance is established and generic editor ownership is not ambiguous;
- permanent scenarios A-E complete through UI without hidden state seeding;
- cold-start automation passes;
- Windows installed-app human review passes;
- preserved Stage 9 release/security/integrity gates remain green.
