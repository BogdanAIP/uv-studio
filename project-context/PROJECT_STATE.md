# Project State

<!-- uv-active-slice: stage-4-replacement-plan-gate -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Replacement plan gate

**Last verified `main` baseline:** `58ff29eb4f295bb890a0b6f1c76b2f2f5f08cd38`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

Stage 4 now has three proven layers: exact local range mechanics, non-destructive accepted replacement decisions, and a provider-neutral pre-replacement `RangeContinuityBrief` under D-029. PR #26 corrected the workflow so continuity evidence and constraints exist before replacement preparation rather than describing an already-produced take.

The current product order is:

```text
targeted range intent
  -> RangeContinuityBrief
  -> approved replacement plan
  -> replacement preparation / optional generation
  -> evidence-based review
  -> accepted replacement decision
  -> explicit render/export
```

## Active slice

`stage-4-replacement-plan-gate` introduces a typed/versioned approved plan under `timeline/` for one logical `edit_id`.

The plan must:

- load and explicitly validate the current RangeContinuityBrief;
- inherit exact `edit_id + source_path + start_us + end_us` from that Brief rather than trusting duplicate caller identity;
- bind to a server-computed SHA-256 digest of canonical Brief JSON so later Brief changes make the plan stale;
- approve a provider-neutral method class such as deterministic edit, prepared project asset or generative transform;
- persist bounded required/allowed/forbidden change scope and an audio strategy;
- automatically carry continuity constraint IDs and review target IDs from the Brief;
- make sample-first mandatory for generative plans and unnecessary for non-generative plans;
- contain no provider/model/offer/runtime/credential/host identity;
- remain valid before any replacement media or `AcceptedRangeEdit` exists;
- perform no media/provider execution when approved;
- remain structurally readable/removable if the Brief later changes or disappears, while explicit validation fails closed.

Persisting a plan is the approval gate. Draft editor form state does not become canonical project state in this slice.

## Expected following work

After this gate is proven, continue with `stage-4-replacement-preparation`: consume an approved current plan and produce candidate replacement media without automatically accepting it. Deterministic/prepared methods stay first-class; optional generative execution uses semantic capabilities and D-017, with sample-first enforced before full generation.

## Remaining cross-cutting gaps

- D-023 still needs post-merge/idle lifecycle and live diff-vs-write-scope enforcement;
- general free-form project JSON fields still need proportionate recursive portability hardening;
- Stage 4C still owns complete timeline/preview/accept/export UI;
- broader real-media codec/device coverage remains incremental hardening.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
