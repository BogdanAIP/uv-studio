# Project State

<!-- uv-active-slice: stage-4-replacement-preparation -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Replacement candidate preparation

**Last verified `main` baseline:** `324a7de606e58224c1dd30de05b5169bcc31819f`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

Stage 4 has explicit product-owned state gates for target intelligence and method approval:

```text
targeted range intent
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> candidate preparation
  -> independent evidence-based review
  -> accepted replacement decision (D-028)
  -> explicit render/export
```

The active slice begins only after a currently valid approved plan exists.

## Active slice

`stage-4-replacement-preparation` produces **candidate replacement artifacts**, not accepted edits.

Required boundaries:

- preparation revalidates the current ReplacementPlan/Brief revision before any work;
- runtime implementation must match the approved method class;
- `prepared_asset` is project-scoped/local and imports/copies a project file into a fresh candidate artifact;
- deterministic preparation may only use local/free deterministic media capabilities that return UV-owned artifacts;
- generative preparation remains optional and uses existing semantic capability selection + D-017 authorization;
- a generative full candidate is blocked until the plan's sample-first obligation has a separately approved sample candidate;
- candidate state binds exact target identity and server-computed current plan digest;
- candidate state contains project-relative artifact paths and portable non-secret provenance references, not provider/model/runtime IDs;
- candidate creation never writes `timeline/range-edits.json`;
- external MCP tools cannot nominate arbitrary output host paths: exact bindings must declare output arguments whose UV-owned destination paths are injected by the trusted adapter;
- output files are validated as regular non-empty project-owned artifacts before they become candidate/reference state;
- stale candidates remain inspectable/removable while explicit validation fails closed.

The following slice remains an independent replacement review gate; preparation success is not acceptance.

## Expected following work

After this slice proves candidate production, continue with `stage-4-replacement-review-gate`: validate a candidate against its bound plan/Brief review targets and continuity evidence, persist an explicit review verdict, and only allow `AcceptedRangeEdit` creation from a current approved candidate/review pair.

## Remaining cross-cutting gaps

- D-023 still needs post-merge/idle lifecycle and live diff-vs-write-scope enforcement;
- general free-form project JSON fields still need recursive portability hardening;
- Stage 4C owns the complete timeline/preview/accept/export UI;
- broader real-world codec/device fixture coverage remains incremental hardening.
