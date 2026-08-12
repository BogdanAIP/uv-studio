# Next Task

<!-- uv-next-slice: stage-4-non-destructive-edit-state -->

Updated: 2026-08-12

## Handoff

Cross-platform real-media evidence triggered the Stage 4A architecture override recorded in D-027.

The next slice is:

```text
stage-4-non-destructive-edit-state
  -> canonical provider-neutral edit decisions
  -> original source + exact range + accepted replacement references
  -> multiple accepted edits without whole-source re-encode per acceptance
  -> deterministic preview/render projection
  -> portable archive/reopen proof
```

## Why this now precedes RangeContinuityBrief

The D-021/D-022 mechanical path is correct on the tested Ubuntu/Windows fixtures, but a one-second replacement in an eight-second 320x180 MPEG-4 source produced a complete FFV1 output **4.824x** the source size on both platforms.

That whole-output file is acceptable as a deterministic render/intermediate, but not as canonical repeated-edit project state. Persisting Stage 4B continuity/intelligence before fixing this state boundary would make richer durable data depend on a representation already shown to duplicate unchanged media.

## Required next-slice outcome

The next slice must define and prove a small typed/versioned edit-state contract, not a new editor framework.

Minimum requirements:

- project-relative original source reference;
- immutable integer-microsecond requested range;
- project-relative accepted prepared-replacement reference;
- deterministic ordering/overlap rules for multiple accepted edits;
- no API keys, host paths, provider IDs or runtime IDs in canonical state;
- archive/export/import/reopen round-trip;
- explicit projection of edit decisions into the existing deterministic composition/render path;
- no automatic full-video FFV1 materialization merely because an edit is accepted;
- rollback/validation if an edit decision references missing/incompatible project media;
- tests for multiple non-overlapping edits and explicit rejection/policy for overlapping edits.

## Boundary

Do not weaken the existing D-021/D-022 exact FFmpeg mechanics and do not replace them with unsafe packet-copy concatenation.

Do not combine this slice with provider generation, RangeContinuityBrief semantics, the Stage 4C full timeline UI, dubbing/music modes or Windows packaging.

## Following task

After the non-destructive edit-state boundary is proven portable and deterministic, return to `stage-4-range-continuity-brief` for Stage 4B provider-neutral bounded context/intelligence state.
