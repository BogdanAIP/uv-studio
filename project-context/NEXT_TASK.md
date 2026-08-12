# Next Task

<!-- uv-next-slice: stage-4-replacement-review-gate -->

Updated: 2026-08-12

## Expected handoff

After candidate preparation is merged, continue Stage 4B with `stage-4-replacement-review-gate`.

The next slice should consume a **current candidate bound to a current approved ReplacementPlan** and persist an explicit evidence-based review verdict before any final `AcceptedRangeEdit` can be created from that candidate.

## Required direction

```text
current ReplacementCandidate
  + current RangeContinuityBrief / ReplacementPlan
  -> mechanical candidate validation
  -> continuity/review-target evidence
  -> optional model-assisted review behind Capability Registry + D-017
  -> approved / rejected / needs_revision verdict
  -> only approved current candidate may become AcceptedRangeEdit
```

Requirements:

- candidate target + plan digest must still be current before review;
- mechanical validation is separate from observations/inferences;
- all persisted review criteria trace back to plan/Brief review targets;
- remote/VLM review is optional and authorized; a viable local/manual review path remains possible;
- provider/model/runtime identity stays in execution provenance, not portable review schema;
- rejected/needs-revision candidates remain project artifacts/history but cannot be accepted;
- accepted edit creation must use the exact reviewed candidate project path and exact target range;
- candidate approval must not silently reapprove a stale plan or changed Brief;
- no Stage 4C full editor UI, dubbing/music mode or packaging work in this slice.
