# Next Task

<!-- uv-next-slice: product-recovery-truth-inventory -->

## Goal

Restore product truth before further Stage 9 release progression. The first recovery slice audits every user-visible workflow against the actual mounted UV-owned execution path, repairs false/stale recipe execution readiness, and establishes the initial Product Orchestrator contract.

This handoff is governed by D-062 and `docs/architecture/PRODUCT_RECOVERY_PLAN.md`.

## Required direction

### 1. Build the Product Truth Matrix

Create `docs/architecture/PRODUCT_TRUTH_MATRIX.md` and inventory every visible recipe and primary action.

For each entry record:

- user intent/recipe;
- frontend route/component and handler;
- frontend API function;
- mounted backend route;
- domain command/service;
- required capability/offer;
- actual adapter/runtime;
- user-visible setup prerequisite;
- expected result/artifact/state change;
- truthful status: `working`, `working_with_setup`, `partial`, `misleading`, or `dead`;
- automated and human evidence status.

At minimum cover:

- `general_video`;
- `narrated_video`;
- `music_video`;
- targeted existing-video edit;
- dubbing;
- `action_transfer`;
- `digital_human`;
- `story_video`;
- `commercial_product`;
- `photo_to_video`;
- `visualizer`;
- `performance_lip_sync`;
- `free_project`.

### 2. Repair execution truth

- eliminate every `AVAILABLE`/ready target whose launch path is not mounted by the current UV-owned server;
- remove historical compatibility assumptions from product readiness;
- derive readiness from a current executable workflow/capability/adapter;
- introduce structured `setup_required` / `partial` / `unavailable` semantics where needed;
- ensure create-project/workspace UI does not present unfinished modes as ordinary ready workflows;
- add backend tests that enumerate advertised executable targets and fail when the mounted application cannot serve them.

### 3. Audit stale legacy frontend surfaces

Inventory current call sites for legacy VideoClaw-derived clients/routes including `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/sandbox/*`, upload/cache helpers and redirect-only pipeline pages.

Classify each item as:

- required compatibility surface;
- unreachable/dead donor code;
- transitional code still used by a supported path.

Do not delete before dependency/call-site evidence exists.

### 4. Propose the first Product Orchestrator contract

Define a typed product-level projection based on real current domain state, at minimum:

- workflow/recipe intent;
- readiness;
- prerequisites;
- semantic next actions;
- active jobs;
- required user decisions;
- recent artifacts/results;
- actionable diagnostics.

The orchestrator must project existing Project Store + capability/runtime truth; it must not become another canonical project database.

### 5. Preserve proven foundations

Do not rewrite Project Store, authorization, Capability Registry, deterministic FFmpeg adapters, portable domain state, MLT integration or Stage 9 packaging/native-shell work merely to simplify the first recovery slice.

Do not remount the complete VideoClaw backend to make stale launch paths work.

Do not begin a broad frontend redesign before the truth matrix and execution contract are repaired.

## Completion proof

This first recovery slice is complete when:

- `PRODUCT_TRUTH_MATRIX.md` covers every visible recipe and primary action;
- automated contract tests prove that anything advertised as directly executable is backed by a current mounted UV-owned route and real execution boundary;
- known stale readiness for general/narrated/action-transfer/digital-human and any other affected modes is corrected;
- legacy frontend/API surfaces are classified with evidence rather than assumptions;
- an initial Product Orchestrator contract is documented and covered by focused tests/fixtures;
- existing permanent engineering checks remain green;
- no Stage 9 packaging/integrity foundation is silently weakened.

## Entry gate

Do not run this as a second concurrent implementation slice while PR #38 is actively changing product code. PR #38 is now Draft/paused under D-062. Coordinate the lifecycle transition first, preserving the Stage 9 branch as engineering/package reference for later reconciliation.

## Following work

After this slice, implement the Product Orchestrator and simplify the five permanent journeys in the order defined by `PRODUCT_RECOVERY_PLAN.md`. Resume final Stage 9 release/signing work only after the full Product Truth Gate is satisfied.
