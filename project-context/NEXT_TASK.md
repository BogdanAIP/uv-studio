# Next Task

<!-- uv-next-slice: stage-4-replacement-plan-gate -->

Updated: 2026-08-12

## Expected handoff

After the active RangeContinuityBrief slice is merged, continue Stage 4B with `stage-4-replacement-plan-gate`.

The next slice should consume a validated provider-neutral continuity brief for an exact targeted edit intent and persist an explicit approved replacement plan **before replacement preparation or generation begins**.

An already accepted edit is not required to create the plan. If one exists for the same `edit_id`, its source/range identity must remain compatible with the brief.

## Required direction

```text
validated RangeContinuityBrief
  -> replacement method choice
  -> required / allowed changes
  -> audio / timing / continuity constraints
  -> deterministic vs prepared vs generated path
  -> sample-first requirement where generation is used
  -> review targets
  -> approved plan gate
  -> replacement preparation / generation
```

Requirements:

- exact `edit_id + source_path + start_us + end_us` survives the plan unchanged;
- deterministic/local methods stay first-class and do not require a provider;
- generative preparation is optional, semantic-capability based and D-017 authorized when remote/non-free;
- plan state describes the approved **method class and constraints**, not one provider/model/runtime instance;
- runtime provider/model/offer choice remains outside portable canonical plan state;
- no silent downgrade from an approved method class to a weaker path;
- if generation is used, sample-first evidence is required before committing to full replacement generation;
- review targets from the continuity brief remain traceable into the plan/review gate;
- the plan must be usable before any `AcceptedRangeEdit` exists;
- no full Stage 4C UI, dubbing/music mode or packaging work in this slice.
