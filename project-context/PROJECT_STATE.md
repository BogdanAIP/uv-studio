# Project State

<!-- uv-active-slice: stage-4-replacement-plan-gate -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Replacement plan gate

**Last verified `main` baseline:** `58ff29eb4f295bb890a0b6f1c76b2f2f5f08cd38`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

Stage 4 has a proven chain from exact target selection through provider-neutral intelligence and non-destructive acceptance:

```text
targeted range intent
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> replacement preparation / optional generation
  -> independent evidence-based review
  -> accepted replacement decision (D-028)
  -> explicit render/export
```

PR #26 established that continuity evidence exists before replacement creation. The current slice adds the next approval boundary without executing media/provider work.

## Replacement plan gate — review-ready

Canonical approved plan state lives in:

```text
timeline/replacement-plans.json
```

The implemented boundary provides:

- one approved plan per logical `edit_id`;
- exact target identity inherited server-side from a currently valid RangeContinuityBrief;
- server-computed canonical `brief_sha256` binding so changed Brief content makes old approval stale;
- provider-neutral method classes: `deterministic_edit`, `prepared_asset`, `generative_transform`;
- bounded, duplicate-free and pairwise-disjoint required/allowed/forbidden change scopes;
- explicit `preserve_source` vs `replacement_audio` strategy;
- Brief constraint IDs and review-target IDs copied automatically for traceability;
- derived sample policy: generative plans require sample-first, deterministic/prepared plans do not;
- strict schemas with no provider/model/offer/runtime/credential fields;
- valid approval before replacement media or `AcceptedRangeEdit` exists;
- no FFmpeg/VLM/MCP/provider execution and no artifact creation during approval;
- structural readability/removal after Brief staleness plus explicit current-health validation;
- explicit reapproval after a Brief change refreshes digest and traceability;
- UV-owned list/get/put/delete API with no execution endpoint;
- archive/import/fresh reopen exactness before replacement creation.

D-030 is accepted.

Draft functional head `e816f962ff892fae5401e6cf006204f354ca6630` passed all five required checks in CI run #699 (`31590672057`) on Ubuntu and Windows. Unit/API/HTTP, existing Stage 4A real-media golden tests, frontend lint, zero high-severity npm audit and production build are green.

The final state-only review head must repeat the same five required checks before merge.

## Expected following work

After PR #27 merges, continue with `stage-4-replacement-preparation`: consume a currently valid approved plan and produce candidate replacement media without automatically accepting it. Deterministic/prepared methods remain first-class; optional generative execution uses semantic capabilities and D-017, and generative full preparation must enforce the persisted sample-first obligation.

## Remaining cross-cutting gaps

- D-023 still needs post-merge/idle lifecycle and live diff-vs-write-scope enforcement;
- general free-form project JSON fields still need proportionate recursive portability hardening;
- Stage 4C still owns complete timeline/preview/accept/export UI;
- broader real-media codec/device coverage remains incremental hardening.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
