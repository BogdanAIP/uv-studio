# D-027 — Real-media evidence makes non-destructive edit state a Stage 4A prerequisite

Status: accepted  
Date: 2026-08-12

## Decision

Keep the existing D-021/D-022 FFV1/FLAC extraction/reinsertion path as a deterministic local correctness/render mechanism, but do **not** use a newly materialized whole-output lossless file as the canonical state of every accepted short edit.

Before Stage 4B adds durable range-continuity/intelligence state, Stage 4A will introduce a provider-neutral non-destructive edit-decision model that represents:

```text
original source reference
  + exact integer-microsecond requested range
  + accepted prepared replacement reference
  + deterministic composition order/policy
```

The complete edited media file is produced only by an explicit preview/render/export operation when needed.

## Evidence

Cross-platform real-media tests in PR #24 execute the actual `LocalFFmpegAdapter` against installed FFmpeg/FFprobe rather than a fake runner.

Correctness was reproduced on Ubuntu FFmpeg 6.1.1 and Windows FFmpeg 9.0 for:

- CFR + audio extraction/reinsertion;
- observable VFR frame intervals;
- no-audio extraction/reinsertion;
- non-zero mux timestamp offsets with zero-based portable project ranges;
- real produced-file rollback after a later extraction failure;
- visible prefix/replacement/suffix ordering through pixel sampling.

A separate compressed-source measurement replaced 1 second in an 8-second 320x180 30-fps MPEG-4 source.

| Platform | Source bytes | Whole-output FFV1 bytes | Ratio | Reinsertion |
|---|---:|---:|---:|---:|
| Ubuntu | 713,056 | 3,440,122 | **4.824x** | 389 ms |
| Windows | 713,058 | 3,440,072 | **4.824x** | 397 ms |

The complete evidence is recorded in `project-context/evidence/STAGE_4A_REAL_MEDIA.md`.

## Rationale

The mechanical path itself did not fail: it preserved the tested range, timing, stream and rollback invariants on two materially different FFmpeg builds.

The problem is the state model implied by accepting each edit as another complete FFV1/FLAC rendition. Even the deliberately small compressed fixture requires rewriting the whole 8-second source and expands it by 4.824x for a one-second replacement. Repeating that model for ordinary long compressed video would duplicate unchanged media and make project storage/work scale with the whole rendered source after every accepted edit.

The measured tiny-fixture runtime is not extrapolated into a claim about 1080p/4K performance. The decision does not require such extrapolation: the unnecessary whole-file materialization and reproduced storage expansion are enough to reject it as canonical repeated-edit state.

## Rejected alternatives

### Keep whole-output FFV1 as canonical edit state

Rejected for repeated edits because it duplicates unchanged source regions and grows project storage unnecessarily.

### Replace the safe composition path with packet-copy concatenation

Rejected. This would weaken exactness and codec/GOP safety to solve the wrong layer of the problem.

### Jump directly to RangeContinuityBrief

Rejected for now. Persisting richer Stage 4B intelligence before the edit state model is settled would couple durable intelligence to a state representation already shown to be unsuitable for repeated short edits.

## Consequences

1. `video.replace_range` remains useful as a deterministic render/correctness operation.
2. Canonical accepted edits become references/decisions, not full lossless rendered media by default.
3. A project can accumulate multiple exact edits without re-encoding unchanged regions after each acceptance.
4. Preview/export will compose the source plus accepted edit decisions explicitly.
5. The next slice changes from `stage-4-range-continuity-brief` to `stage-4-non-destructive-edit-state`.
6. RangeContinuityBrief remains the following Stage 4B task once the non-destructive state boundary is proven portable and deterministic.
