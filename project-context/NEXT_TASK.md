# Next Task

<!-- uv-next-slice: stage-4-range-continuity-brief -->

Updated: 2026-08-12

## Expected handoff

After the active non-destructive edit-state slice is merged, continue Stage 4B with `stage-4-range-continuity-brief`.

The next slice should add a typed/versioned provider-neutral bounded evidence/continuity document attached to exact project edit ranges.

## Required direction

```text
accepted exact edit decision
  -> bounded before/after project evidence
  -> mechanical source/probe facts
  -> optional observations/inferences with confidence
  -> replacement continuity constraints
  -> review targets
```

Requirements:

- immutable integer-microsecond range identity;
- project-relative evidence references only;
- mechanical facts separated from observations/inferences;
- no provider/model/runtime IDs, host paths or credentials in canonical state;
- archive/import/reopen proof;
- valid baseline brief does not require a remote VLM/provider call;
- provider execution, when later used to enrich a brief, remains behind the existing capability/D-017 boundary.

## Boundary

Do not combine RangeContinuityBrief with the full Stage 4C editor UI, provider generation adapters, dubbing/music modes or Windows packaging.

If the active edit-state slice exposes a structural blocker, change this handoff before merge rather than carrying an invalid assumption forward.
