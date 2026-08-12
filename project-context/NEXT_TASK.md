# Next Task

<!-- uv-next-slice: stage-4-range-continuity-brief -->

Updated: 2026-08-12

## Expected handoff

If the active real-media slice passes without exposing a structural mechanical/state-model blocker, continue Stage 4B with:

```text
stage-4-range-continuity-brief
  -> typed provider-neutral bounded range/context evidence
  -> observed vs inferred facts
  -> exact requested-range identity
  -> portable versioned project state
```

## Evidence-controlled override

The active `test-real-media-golden` slice must first measure the actual FFmpeg/FFprobe path on Ubuntu and Windows.

If that evidence shows either of the following, this file and `ACTIVE_SLICE.json` must be changed before merge so the next slice becomes a scoped media-edit-core refactor instead:

- exact range/timestamp behavior is structurally wrong for representative encoded inputs; or
- whole-output FFV1/FLAC reinsertion is already impractical enough that repeated-edit state must become non-destructive before Stage 4B adds durable intelligence state.

Do not choose the refactor merely because it is architecturally attractive; use the measured evidence recorded by this slice.

## RangeContinuityBrief requirements if no override is needed

- provider/model-neutral schema;
- integer-microsecond requested range as immutable identity;
- bounded context references only;
- mechanical facts separated from observations/inference;
- explicit continuity constraints and review targets;
- no API keys, host paths, runtime IDs or provider selections in canonical state;
- archive/export round-trip proof;
- no VLM/provider execution required to construct valid baseline state.

## Scope control

Do not combine the next slice with the Stage 4C timeline UI, provider generation adapters, dubbing/music modes or Windows packaging.
