# Next Task

<!-- uv-next-slice: test-real-media-golden -->

Updated: 2026-08-12

## Primary target

Prove Stage 4A targeted-range mechanics against **real encoded media**, not only fake subprocess contracts.

The next slice is:

```text
test-real-media-golden
  -> deterministic tiny encoded fixtures
  -> real ffprobe/ffmpeg execution
  -> video.extract_range
  -> video.replace_range
  -> evidence assertions on Windows + Linux
```

This work starts only after the active dependency-ownership slice has made the baseline runtime reproducible and frontend dependency health explicit.

## Required fixture set

Create or deterministically generate small media fixtures with documented provenance. Keep repository/CI weight proportionate.

At minimum cover:

1. CFR video with one audio stream;
2. VFR video with one audio stream;
3. video without audio;
4. source with non-zero or offset timestamps where FFmpeg can generate the condition reproducibly;
5. a prepared replacement clip matching the supported exact-reinsertion contract.

Prefer fixture-generation scripts/commands from FFmpeg test sources over committing large binaries when generation is stable on both Ubuntu and Windows. If small binaries are more reliable, record their generation recipe and checksums.

## Real execution acceptance

Run the actual product adapters with real `ffmpeg` and `ffprobe` binaries, not mocked runners.

For `video.extract_range`, prove:

- canonical source path resolution;
- requested integer-microsecond range identity survives;
- requested/context artifacts are real playable video streams;
- observed output durations stay within an explicit evidence-based tolerance;
- VFR handling does not silently impose an undocumented CFR policy;
- audio presence follows the declared extraction policy;
- artifact registration occurs only after successful output probing;
- failure cleanup leaves no registered/partial artifact.

For `video.replace_range`, prove:

- source + exact requested interval + prepared replacement produce one real output video;
- prefix/replacement/suffix ordering is correct using observable fixture evidence, not only filtergraph-string assertions;
- source/replacement geometry and audio policy are enforced;
- output duration matches the D-022 formula within an explicit evidence-based tolerance;
- no hidden retiming is introduced to make an incompatible replacement pass;
- failure cleanup remains atomic.

## CI requirements

- install/provision FFmpeg explicitly in the test job rather than assuming a runner image detail;
- run the real-media suite on Ubuntu and Windows;
- keep existing fast mocked unit/API suites unchanged for contract-level feedback;
- make the real-media test a named required evidence gate before Stage 4A mechanical work is treated as production-proven;
- preserve useful failure diagnostics without writing absolute host paths or secrets into portable project state.

## Investigation output

Use the real fixtures to answer whether the current whole-output FFV1/FLAC reinsertion is acceptable only as a correctness intermediate or already creates unacceptable size/runtime behavior even on representative inputs.

If evidence shows the current model is unsuitable for repeated edits, the following slice should become a scoped non-destructive media-edit state/refactor. If not, record the evidence and proceed without inventing that refactor prematurely.

## Scope control

Do not combine this slice with:

- `RangeContinuityBrief`;
- a VLM/generative provider;
- the Stage 4C timeline UI;
- dubbing/music modes;
- Windows installer work;
- a broad FFmpeg abstraction rewrite before the real-media evidence exists.

## Handoff after this slice

Expected decision point:

```text
real-media evidence
  -> if needed: refactor/non-destructive-media-edit-core
  -> otherwise: stage-4-range-continuity-brief
```

The coordinator must record that decision from measured evidence rather than roadmap preference alone.
