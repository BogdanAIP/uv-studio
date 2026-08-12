# Stage 4A Real-Media Evidence

Date: 2026-08-12  
Slice: `test-real-media-golden`  
PR: #24

## Purpose

This evidence answers two separate questions:

1. Are the current D-021/D-022 exact range extraction and prepared-replacement reinsertion mechanics actually correct on real encoded media?
2. Is whole-output FFV1/FLAC composition suitable as the durable state model for repeated short edits?

The first question is a correctness gate. The second is an architecture/state-model gate and must not be inferred from mocked subprocess tests.

## Test environment

Real fixtures are generated during CI and processed through the actual `LocalFFmpegAdapter` using installed `ffmpeg` and `ffprobe` binaries.

| Platform | Toolchain |
|---|---|
| Ubuntu | FFmpeg/FFprobe 6.1.1-3ubuntu5 |
| Windows | FFmpeg/FFprobe 9.0 essentials build (gyan.dev) |

FFmpeg is explicitly provisioned by the application CI job on both platforms rather than assumed from the runner image.

## Correctness evidence

### CFR + audio extraction and reinsertion

A 4-second blue source with one FLAC audio stream is edited by replacing project time 1.0–2.0 seconds with a 1-second red clip with one FLAC audio stream.

Observed:

- exact requested range remains `1_000_000..2_000_000` microseconds;
- requested extraction is approximately 1 second;
- 0.5-second before/after context artifacts are produced and probed before registration;
- final output contains one video + one audio stream;
- final output duration is 4.001 s on Ubuntu and 4.000 s on Windows;
- pixel samples prove prefix/replacement/suffix ordering: blue at 0.5 s, red at 1.5 s, blue at 2.5 s.

### VFR + audio extraction

The source intentionally drops alternating frames during the first half and keeps all frames during the second half.

Both Ubuntu and Windows observe the same frame interval set before and after extraction:

```text
33 ms, 34 ms, 66 ms, 67 ms
```

The requested 0.5–2.5 second extraction therefore preserves observable variable frame timing instead of silently imposing one constant frame interval.

### No-audio path

A source and replacement with no audio remain video-only after extraction and reinsertion on both platforms. No synthetic or unexpected audio stream appears.

### Non-zero timestamp source

A three-segment source is muxed with a `1.250000` second output timestamp offset.

Observed on both platforms:

- ffprobe video `start_time` = `1_250_000` microseconds;
- project request remains zero-based at `750_000..1_750_000` microseconds;
- extracted content begins in the expected blue segment and later reaches the green segment.

This proves that portable project ranges are interpreted relative to source content rather than being silently shifted to absolute mux timestamps.

### Real rollback

The rollback test allows the first real FFmpeg extraction output to be created, then injects failure into the second FFmpeg operation.

Observed on both platforms:

- two FFmpeg calls occurred;
- no artifact remained registered in `project.json`;
- the project `artifacts/` directory was empty after failure.

This validates atomic cleanup with a real produced media file, not only a fake-runner path.

## Whole-output FFV1 measurement

The initial blue-source fixture was already FFV1, so its ~1.0x output/source size ratio was not useful for judging ordinary compressed input. A separate measurement therefore uses a deterministic 8-second 320x180 30-fps MPEG-4 source and a 1-second matching MPEG-4 replacement.

The current `video.replace_range` implementation re-encodes the complete 8-second result as FFV1.

| Platform | Source | Output | Ratio | Reinsertion |
|---|---:|---:|---:|---:|
| Ubuntu | 713,056 B | 3,440,122 B | **4.824x** | 389 ms |
| Windows | 713,058 B | 3,440,072 B | **4.824x** | 397 ms |

The output duration remained exactly 8 seconds on both platforms and the codec changed from MPEG-4 to FFV1 as expected.

## Interpretation

### Mechanical result

The current extraction/reinsertion contract is valid as a deterministic correctness/render path for the tested cross-platform baseline:

- exact integer-microsecond identity survives;
- CFR/VFR behavior is observable and correct;
- audio/no-audio policy is enforced;
- non-zero source timestamps do not redefine project coordinates;
- actual content ordering is correct;
- rollback is atomic with real output files.

No adapter defect was exposed by these representative deterministic fixtures.

### State-model result

Whole-output FFV1 is **not suitable as the durable repeated-edit state model**.

The evidence is already strong on a deliberately tiny fixture: replacing only 1 second in an 8-second compressed 320x180 source rewrites the complete video and produces a file 4.824 times the compressed source size on both independent FFmpeg builds.

The measured sub-second runtime at this tiny resolution is not evidence that full re-encoding scales acceptably to long 1080p/4K sources. The architectural problem is more fundamental: each accepted short edit would materialize another complete lossless rendition even though the unchanged source regions are already represented by the original file.

No exact size/time multiplier is extrapolated to larger media from this fixture. The measured cross-platform rewrite + 4.824x expansion is sufficient to reject FFV1 whole-output files as canonical repeated-edit state.

## Decision supported by this evidence

Keep the current FFV1/FLAC reinsertion path as:

- deterministic correctness oracle;
- local intermediate/render path where explicitly requested;
- testable fallback for final composition mechanics.

Before Stage 4B adds durable continuity/intelligence state, introduce a provider-neutral **non-destructive edit-decision state** that stores source + exact range + accepted replacement references without materializing a new complete lossless video for every accepted edit.

Rendering remains explicit for preview/export. This is a state-model refactor, not a return to unsafe packet-copy concatenation and not an excuse to weaken D-021/D-022 exactness.

## Coverage boundary

This deterministic baseline does not claim exhaustive coverage of phone recordings, OBS variants, AAC priming, H.264/H.265 GOP edge cases or every container. Those can extend the permanent fixture set as concrete failures are discovered.

The evidence is sufficient for the current decision because it proves the product's own range semantics across two FFmpeg generations and separately measures the repeated-edit storage model that was under question.
