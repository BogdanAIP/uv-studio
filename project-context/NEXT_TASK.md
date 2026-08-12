# Next Task

<!-- uv-next-slice: stage-4-replacement-preparation -->

Updated: 2026-08-12

## Expected handoff

After the active replacement-plan gate is merged, continue Stage 4B with `stage-4-replacement-preparation`.

The next slice should consume a **currently valid approved replacement plan** and produce candidate replacement media without automatically creating an `AcceptedRangeEdit`.

## Required direction

```text
approved current ReplacementPlan
  -> select implementation for approved method class
  -> deterministic/prepared local path OR optional generative capability
  -> sample-first gate when plan requires generation
  -> bounded candidate artifact + portable provenance
  -> later independent review
  -> only then acceptance
```

Requirements:

- preparation must fail if the plan's bound RangeContinuityBrief digest or exact target identity is stale;
- runtime implementation must not silently change the approved method class;
- deterministic/local preparation remains first-class and provider-free;
- prepared-asset handling remains project-scoped and does not become arbitrary host-file access;
- generative execution remains optional and routes through semantic Capability Registry + D-017 authorization;
- provider/model/offer/runtime selection is execution provenance, not canonical ReplacementPlan state;
- generative plans must satisfy the persisted sample-first requirement before a full replacement candidate is produced;
- candidate outputs are project-owned artifacts with non-secret provenance;
- creating a candidate does not automatically accept it into `timeline/range-edits.json`;
- independent evidence-based replacement review remains the following gate rather than being skipped;
- no Stage 4C full editor UI, dubbing/music mode or packaging work in this slice.
