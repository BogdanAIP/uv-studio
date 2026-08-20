# UV Studio Product Recovery Plan

## Status

This plan is a release-blocking product-recovery gate discovered during human Windows 10 validation of Stage 9.

Stage 9 packaging, installer, runtime integrity and native-shell work remain valuable and must be preserved. However, Stage 9 must not merge merely because packaging/release automation is green. Human validation exposed a deeper mismatch between the product UI, recipe/execution metadata and the actually executable application paths.

The recovery goal is **not** to rewrite UV Studio from scratch. It is to preserve the strong product-owned backend/runtime foundation, remove dead or misleading compatibility surfaces, add the missing product orchestration layer, and make every visible workflow truthful and completable by a normal user.

## Why recovery is required

The repository currently contains several individually strong layers that do not yet compose into one coherent product:

- Project Store, archives, capability authorization, provenance and deterministic local media execution are real and reusable;
- Stage 3.5 correctly stopped mounting the complete legacy VideoClaw application because it could bypass UV-owned safety/authorization boundaries;
- some legacy frontend clients and recipe execution plans still describe those old pipeline routes as if they were live;
- the current frontend often orchestrates several backend state machines directly instead of consuming one product-level workflow state;
- D-033 selected MLT plus selective OpenCut Classic reuse to avoid building a new NLE, but the current product increasingly owns custom timeline/editor interaction and domain workflow UI while MLT is mostly a projection/render adapter;
- several visible recipes describe complete production modes although their user path is partial, capability-gated or absent;
- automated browser tests can prove known scripted paths while still missing cold-start discoverability, setup requirements and apparently dead controls.

The result can pass engineering and packaging checks while still failing the user-outcome gate.

## Recovery principles

1. **Truth before polish.** UI availability, recipe compatibility and execution plans must reflect an actually reachable executable path on the running UV-owned server.
2. **Intent before internal state.** Users express the result they want; the product orchestrator maps that intent onto plans, capabilities, jobs, reviews and artifacts.
3. **Reuse before new editor code.** Do not expand a custom generic NLE until the D-033 implementation gap is explicitly re-evaluated.
4. **One semantic command model.** GUI, AI, MCP and scripts must converge on the same product-owned commands/workflow semantics rather than independently assembling backend REST calls.
5. **Progressive disclosure.** Internal concepts such as capability IDs, plan hashes, review objects, runtime profiles and provider-specific setup stay hidden until they are actionable or diagnostically relevant.
6. **Unavailable means unavailable.** A mode with no executable path is hidden from normal creation or shown as clearly gated with an explicit setup action; it is never presented as ready and then allowed to fail later.
7. **Human outcome is a release gate.** A green CI matrix cannot override a failed clean installed-app user journey.

## Target product architecture

```text
User / AI / MCP / Script
          |
          v
   Product Orchestrator
          |
          +--> Workflow state / next actions / prerequisites
          |
          v
  UV semantic Command Model
          |
   +------+------------------+
   |                         |
Project Store         Capability Registry
   |                         |
   |                 selection/authorization
   |                         |
   +----------+--------------+
              v
   FFmpeg / MLT / local ML / MCP / provider adapters
```

The frontend should render product state and invoke semantic actions. It should not need to understand every internal plan/candidate/review/store transition in order to decide what the user may do next.

## Component disposition

### Keep and protect

These are valuable foundations and should not be replaced without separate evidence:

- canonical Project Store, archives, migrations and path boundaries;
- D-017 execution authorization and provider-neutral Capability Registry;
- capability provenance, cancellation and job ownership;
- deterministic FFmpeg media operations, preview and render adapters;
- accepted-edit/dubbing/music durable state that is already portable and tested;
- MLT runtime and adapter where it provides real editing/render value;
- Stage 9 immutable payload, mutable-data separation, packaged toolchain resolution, Windows installer/update/rollback and Rust/WebView2 native host;
- security, license and dependency hardening already proven by Stage 9.

### Refactor around a product orchestrator

- recipe readiness and project execution planning;
- project creation and project workspace routing;
- targeted-edit workflow presentation;
- dubbing workflow presentation;
- music-video workflow presentation;
- story/commercial/free-project composition flows;
- capability/setup diagnostics shown to end users;
- command/API boundaries currently split across many feature-specific calls.

### Retire after dependency proof

- stale frontend clients for unmounted legacy routes such as `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/sandbox/*` where no live compatibility boundary uses them;
- legacy donor UI components that are no longer reachable product surfaces;
- redirect-only pipeline pages whose only purpose is preserving obsolete navigation;
- execution-plan targets that point to routes not mounted by the UV-owned FastAPI application.

No compatibility code is deleted merely because it looks old. Each retirement requires call-site/search evidence and tests proving that no supported product path depends on it.

### Re-evaluate explicitly

- how much of OpenCut Classic should be reused versus maintained as a design donor only;
- whether UV Studio is a specialized AI/media orchestrator with bounded editing, or intends to own a broader generic NLE surface;
- the long-term role of MLT: true editing/timeline engine versus validation/projection/render adapter;
- the exact supported compatibility boundary for VideoClaw pipelines after Stage 3.5;
- which local ML runtimes are bundled, first-run installable or deliberately optional.

## Phase 0 — Freeze misleading release progression

Goal: preserve Stage 9 work while preventing a technically green but product-incoherent build from becoming the maintained baseline.

Actions:

- keep PR #38 Draft;
- do not merge from historical or current green workflow evidence alone;
- record the failed human installed-app review as authoritative product evidence;
- stop adding signing/publication polish until the Product Truth Gate is satisfied;
- preserve exact Stage 9 packaging/runtime commits so recovery can reuse them later.

Exit:

- repository docs and PR state clearly say that product recovery, not signing, is the next release blocker.

## Phase 1 — Product Truth Inventory

Goal: create a machine-reviewable inventory of every visible workflow and action.

For every user-visible mode/control, record:

- recipe or product intent;
- frontend route/component and click handler;
- frontend API function;
- backend HTTP route;
- domain service/command;
- required capability/offer;
- actual adapter/runtime;
- required user setup;
- expected artifact/state change;
- current status: `working`, `working_with_setup`, `partial`, `misleading`, `dead`;
- cold-start user evidence.

Required truth checks:

- no `AVAILABLE` execution plan may target an unmounted route;
- no visible primary action may depend on a hidden prerequisite;
- no workflow may be called complete only because tests pre-seed state through helpers/internal API;
- donor/legacy code must be distinguished from current product authority.

Deliverable:

`docs/architecture/PRODUCT_TRUTH_MATRIX.md` plus focused contract tests that fail when recipe/execution metadata diverges from the mounted application.

Exit:

- every permanent regression scenario and every recipe has one truthful status and one owner path.

## Phase 2 — Repair recipe/execution truth

Goal: make product metadata impossible to disagree with the running server.

Actions:

- remove or replace stale legacy `launch_path` entries;
- derive recipe readiness from an actually registered product workflow/capability, not historical compatibility assumptions;
- introduce explicit states such as `ready`, `setup_required`, `partial`, `unavailable` at the product-orchestrator boundary;
- expose actionable prerequisite objects instead of generic failure strings;
- hide or visibly gate unfinished recipes on the create-project screen;
- add tests that enumerate mounted routes and validate every advertised executable target.

Exit:

- a recipe shown as ready can be started successfully from a clean project using only mounted UV-owned paths;
- a gated recipe explains exactly what is missing before the user starts it.

## Phase 3 — Introduce the Product Orchestrator

Goal: stop teaching the frontend every backend state machine.

Minimum product-level contract:

```text
ProjectWorkflowState
- intent / recipe
- readiness
- current outcome
- prerequisites[]
- next_actions[]
- active_jobs[]
- user_decisions[]
- recent_artifacts[]
- diagnostics[]
```

Each `next_action` should contain:

- stable semantic action ID;
- user-facing title and explanation;
- whether it is enabled;
- if disabled, structured prerequisites and the action that satisfies them;
- expected cost/locality/remote authorization class when relevant;
- bounded input schema;
- resulting state/artifact kind.

Implementation direction:

- use existing Project Store/capability/command services rather than adding a second canonical state store;
- orchestration state is a projection of canonical domain state plus runtime capability availability;
- add a common command envelope incrementally; do not rewrite all feature APIs in one commit;
- GUI, AI, MCP and scripts call the same semantic actions even when transport adapters differ.

Exit:

- project pages render from orchestrator state instead of hand-assembling prerequisite logic for each feature;
- no ordinary frontend component needs to know internal hashes/review IDs merely to determine the next user step.

## Phase 4 — Re-resolve the editor foundation

Goal: enforce the original reuse-first intent of D-033 before generic editor complexity grows further.

Research questions:

1. Can a larger compatible portion of OpenCut Classic provide the media-bin/viewer/timeline editing shell while UV Project Store remains canonical?
2. Can MLT own more timeline operations behind UV commands without exposing raw MLT state as canonical project data?
3. If neither option is maintainable, should UV Studio explicitly narrow itself to bounded task-oriented editing rather than continue growing a home-made generic NLE?

Required outcome:

- one accepted architecture decision replacing ambiguity;
- an explicit list of editor features UV owns versus reuses;
- no new generic trim/split/multitrack/effects/keyframe editor feature before that decision.

Exit:

- the editor direction is coherent, reusable and compatible with GUI/AI/MCP command semantics.

## Phase 5 — Rebuild core journeys as intent -> result

The order is based on permanent release scenarios, not on historical stage numbering.

### 5A. Targeted existing-video edit

Target journey:

`import video -> select range -> describe change -> choose/provide/produce replacement -> preview in context -> accept -> export`

Rules:

- Brief/Plan/Candidate/Review may remain internally durable but ordinary users see them only when a decision is required;
- deterministic prepared replacement remains available;
- generative replacement is offered only when an executable capability exists;
- every disabled action explains the next prerequisite inline.

### 5B. Dubbing

Target journey:

`import video -> transcribe -> optionally translate -> obtain/record/synthesize speech -> preview -> accept -> export`

Rules:

- if local ASR/TTS is not packaged, first-run setup must be explicit before the action is offered;
- manual prepared-audio import remains a valid fallback, not a hidden necessity;
- technical review/loudness evidence stays available under details rather than dominating the main path.

### 5C. Music video

Target journey:

`add song -> analyze/propose structure -> review/edit direction -> provide/generate assets -> assemble -> rhythm review -> export`

Rules:

- manual second-by-second Music Map authoring is an advanced editor, not the default first step;
- analysis should propose sections, markers and shot timing whenever an available capability can do so;
- users edit proposals instead of constructing backend schema from an empty form.

### 5D. Narrated video

Target journey:

`topic/script -> narration -> visual plan -> assets -> assembly -> preview -> export`

Rules:

- replace the stale legacy pipeline target with a real UV-owned orchestrated path;
- remote/paid generation remains explicit and authorized;
- if required generation capabilities are not configured, project creation must say so before launch.

### 5E. General video

Target journey:

`brief -> proposed visual plan -> assets/generation -> assembly -> preview -> export`

Rules:

- do not advertise complete general-video creation until this path exists;
- narration is optional rather than a silent fallback through the old standard pipeline.

Exit for Phase 5:

- all five permanent scenarios can be completed through current product UI without manual API calls or test-only state seeding.

## Phase 6 — Rationalize additional recipes

After the five permanent scenarios are coherent:

- Story Video and Commercial/Product become orchestrated compositions rather than save-only preparation forms;
- Photo -> Video and Visualizer retain their simple working local paths and become reference examples for product UX;
- Performance/lip-sync remains visibly setup-gated unless the verified MuseTalk pack is usable;
- Action Transfer and Digital Human either receive a real UV-owned executable path or are removed from normal ready-mode presentation;
- Free Project exposes reusable tools without forcing every specialized workflow onto the page.

Exit:

- every visible recipe is either end-to-end working or explicitly marked as setup-required/experimental; no ambiguous middle state remains.

## Phase 7 — Cold-start product verification

Goal: make automated evidence resemble a first-time user rather than an informed test author.

Add a separate `cold-start-product` regression class with these restrictions:

- starts from a clean Project Store and clean machine configuration;
- uses only user-visible UI actions after application launch;
- may not pre-seed transcripts, reviews, plans, music maps or accepted edits via test helpers/internal HTTP calls;
- may install/configure an optional runtime only through the same documented setup surface available to a user;
- fails on unexplained disabled primary controls;
- fails when a mode advertised as ready cannot reach an artifact/result;
- records screenshots/state at each major user decision for review evidence.

Human installed-app acceptance remains mandatory before Stage 9 merge.

Exit:

- all permanent regression scenarios have both engineering evidence and cold-start user-outcome evidence;
- a clean Windows 10 user can identify the first action, understand setup requirements and produce the expected result.

## Phase 8 — Resume Stage 9 release hardening

Only after the Product Truth Gate is green:

- rebase/reconcile preserved Stage 9 packaging with the recovered product surface;
- rebuild the exact Windows installer candidate;
- rerun package integrity, legal/security audits, install/update/rollback/uninstall and native-shell checks;
- repeat Windows 10 human review;
- only then finish D-059 trusted signing/timestamp publication work and final checksums.

Stage 9 exit is therefore both:

1. a reproducible secure Windows package; and
2. a coherent product that completes the permanent user journeys.

## Product Truth Gate

Stage 9 may not merge until all of the following are true:

- every visible recipe/action has a truthful readiness state backed by a mounted executable path;
- there are zero execution-plan targets pointing at unmounted endpoints;
- stale legacy clients/pages are either retired or explicitly isolated as compatibility code;
- the Product Orchestrator owns user-facing next-action/prerequisite projection;
- the editor reuse/ownership direction has an accepted decision;
- permanent scenarios A-E complete through UI without hidden API setup;
- cold-start browser evidence passes from clean state;
- human Windows installed-app review passes;
- the existing Stage 9 security/integrity/release gates remain green.

## First implementation slice after this plan

The first recovery slice should be narrowly scoped to **Product Truth Inventory + recipe/execution contract repair**. Do not start by redesigning screens.

Initial deliverables:

1. `PRODUCT_TRUTH_MATRIX.md` generated/maintained from audited current product paths;
2. tests proving advertised targets are mounted and executable/gated truthfully;
3. corrected readiness for `general_video`, `narrated_video`, `action_transfer`, `digital_human` and other affected recipes;
4. inventory and isolation/retirement plan for stale legacy frontend APIs/components;
5. an initial Product Orchestrator contract proposal based on real current states.

Only after truth is restored should the frontend be structurally rebuilt around the orchestrator.
