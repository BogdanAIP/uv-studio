# Next Task

<!-- uv-next-slice: product-recovery-orchestrator-foundation -->

## Goal

After Product Truth Inventory closes false/stale readiness contracts, introduce the first UV Studio Product Orchestrator projection so the frontend can ask one product-level question: **what can the user do next, and what prerequisite blocks it?**

## Required direction

- implement a read-only `ProjectWorkflowState` projection over canonical Project Store/domain state plus runtime capability availability;
- expose explicit readiness: `ready`, `setup_required`, `partial`, `unavailable`;
- expose structured prerequisites rather than implicit disabled-button conditions;
- expose stable semantic `next_actions` with bounded inputs, execution/authorization class and expected result kind;
- keep Project Store and existing domain state canonical; the orchestrator must not become a second persistence engine;
- migrate one representative workflow to consume the orchestrator before broad frontend rewrites;
- preserve D-017 authorization and provider-neutral capability boundaries;
- do not add generic NLE features until the D-033 editor ownership/reuse question is explicitly re-resolved.

## Completion proof

The slice is complete when at least one real project workflow renders its enabled/blocked actions from Product Orchestrator state, a blocked action names an actionable prerequisite, GUI/API tests prove the same semantic state, and no duplicate canonical workflow store is introduced.

## Entry gate

Do not start this slice until `product-recovery-truth-inventory` has:

- a reviewed Product Truth Matrix;
- zero known `AVAILABLE` execution plans pointing to unmounted routes;
- explicit classification of legacy VideoClaw-derived execution/client surfaces;
- focused contract tests preventing stale executable targets from returning.
