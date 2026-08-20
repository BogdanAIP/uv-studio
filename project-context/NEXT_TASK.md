# Next Task

<!-- uv-next-slice: product-recovery-orchestrator-foundation -->

## Goal

After Product Truth Inventory closes false/stale readiness contracts, introduce the first UV Studio Product Orchestrator projection so the frontend can answer: **what can the user do next, what prerequisite blocks it, and which workspace is actually relevant?** At the same time, begin isolating the live VideoClaw shell/pipeline runtime surfaces that point to backend routes Stage 3.5 intentionally removed.

## Required direction

- implement a read-only `ProjectWorkflowState` projection over canonical Project Store/domain state plus runtime capability availability;
- expose explicit readiness: `ready`, `setup_required`, `partial`, `unavailable`;
- expose structured prerequisites rather than implicit disabled-button conditions;
- expose stable semantic `next_actions` with bounded inputs, execution/authorization class and expected result kind;
- expose `relevant_workspaces` (or equivalent) so recipe/orchestrator state, not a universal page, controls which specialist tools are shown;
- keep Project Store and existing domain state canonical; the orchestrator must not become a second persistence engine;
- migrate one representative working flow (prefer Photo -> Video or Visualizer) to consume the orchestrator before broad workflow migration;
- remove/isolate legacy VideoClaw pipeline/session/task/sandbox navigation from the normal AppShell unless an entry is backed by current UV-owned semantics;
- do **not** remount the complete legacy `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/project/*` or `/api/sandbox/*` runtime merely to satisfy `workflowApi` callers;
- keep the live old frontend code only as bounded migration evidence until replacement/removal is proven by build/tests;
- preserve D-017 authorization and provider-neutral capability boundaries;
- do not add generic NLE features until the D-033 editor ownership/reuse question is explicitly re-resolved.

## First representative outcome

A good first proof is a deterministic mode such as Photo -> Video:

```text
project recipe + current sources + runtime availability
 -> GET ProjectWorkflowState
 -> readiness=ready or explicit prerequisite
 -> relevant workspace=photo composition
 -> next action=compose photos
 -> existing video.compose_photos capability
 -> artifact
```

On that project, unrelated dubbing/continuity/targeted-edit workspaces should not be presented as primary workflow steps, and the legacy pipeline sidebar must not remain a competing path.

## Completion proof

The slice is complete when:

- at least one real workflow renders its enabled/blocked actions from Product Orchestrator state;
- a blocked action names an actionable prerequisite;
- relevant workspace projection prevents unrelated specialist panels from being presented for that representative recipe;
- the normal AppShell no longer advertises at least the three broken legacy `/pipelines/*` runtime entries, or they have been replaced by current UV semantic actions;
- GUI/API tests prove the same readiness/action semantics;
- existing domain/capability tests remain green;
- no duplicate canonical workflow/project/task store is introduced.

## Entry gate

Do not start this slice until `product-recovery-truth-inventory` has:

- a reviewed Product Truth Matrix;
- zero known base `AVAILABLE` execution plans pointing to unmounted routes;
- explicit classification of live legacy VideoClaw shell/pipeline/session/task/model/sandbox surfaces;
- focused contract tests preventing stale executable targets from returning;
- all ordinary permanent checks green on the exact review head.
