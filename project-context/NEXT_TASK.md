# Next Task

<!-- uv-next-slice: stage-4-replacement-plan-gate -->

Updated: 2026-08-12

## Expected handoff

After the active RangeContinuityBrief slice is merged, continue Stage 4B with `stage-4-replacement-plan-gate`.

The next slice should consume an exact accepted edit decision plus its provider-neutral continuity brief and persist an explicit approved replacement plan before any designed/generative preparation begins.

## Required direction

```text
accepted edit decision
  + validated RangeContinuityBrief
  -> replacement method choice
  -> required/allowed changes
  -> audio/timing/continuity constraints
  -> sample-first requirement where generation is used
  -> review targets
  -> approved plan gate
```

Requirements:

- deterministic/local edit methods stay first-class;
- generative preparation is optional, semantic-capability based and D-017 authorized when remote/non-free;
- no silent downgrade from an approved method/provider class to a weaker path;
- canonical plan state remains provider-neutral unless a user explicitly approves a runtime execution choice outside portable project state;
- exact target edit identity survives the plan unchanged;
- no full Stage 4C UI, dubbing/music mode or packaging work in this slice.
