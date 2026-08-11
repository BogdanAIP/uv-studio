# Deterministic Existing-Video Range Reinsertion

## Purpose

Stage 4 must be able to replace a short interval of an existing video without making the mechanical edit depend on the system that produced the replacement clip.

The semantic boundary is:

```text
source project video
+ exact ProjectMediaRange
+ prepared project replacement video
-> canonical edited project video
```

The current operation is:

```text
video.replace_range
  -> local_ffmpeg.video_replace_range
```

It is a local/free deterministic capability. AI generation, prompting, provider selection and continuity scoring are intentionally outside this module.

## Request contract

```json
{
  "source_path": "sources/source.mkv",
  "replacement_path": "artifacts/replacement.mkv",
  "start_us": 2000000,
  "end_us": 4000000
}
```

Accepted fields are semantic only. The caller cannot supply:

- output path;
- FFmpeg flags;
- filtergraph text;
- shell command;
- codec command string;
- provider/model identity.

The range uses the same schema-v1 integer-microsecond `ProjectMediaRange` introduced by D-021.

## Input validation

Both concrete project files are freshly FFprobed immediately before composition.

The first supported contract is deliberately narrow:

```text
source video streams      = exactly 1
replacement video streams = exactly 1
source audio streams      = 0 or 1
replacement audio streams = same presence as source
other stream kinds        = rejected
video resolution          = equal
```

Known source/replacement format properties that would otherwise be candidates for implicit FFmpeg negotiation must also match:

```text
video: pix_fmt, sample_aspect_ratio,
       color_range, color_space, color_transfer, color_primaries

audio: sample_fmt, sample_rate, channels, channel_layout
```

Unknown properties are not fabricated. Known mismatches fail closed.

For AV files, stream `start_time` values must be known and video/audio start offset must be within 10 ms for each input. Source audio/video total duration may differ by at most 250 ms; replacement audio/video duration may differ by at most 100 ms.

These restrictions can be relaxed later only through an explicit normalization policy with its own tests.

## Replacement duration policy

There is no hidden retiming.

```text
abs(replacement_video_duration_us - requested_range_duration_us)
<= 100000
```

Otherwise execution stops before FFmpeg composition.

A future stretch/speed/trim feature must be a distinct semantic transformation or explicit policy input.

## Timestamp and filtergraph policy

Project range time is zero-based media time. The source streams may still arrive with non-zero encoded timestamps, so each source stream is first normalized before applying the project range:

```text
video: setpts=PTS-STARTPTS -> trim -> setpts=PTS-STARTPTS
audio: asetpts=PTS-STARTPTS -> atrim -> asetpts=PTS-STARTPTS
```

The replacement is likewise reset to a zero timestamp before concat.

The composition is conceptually:

```text
prefix      = source [0, start)
replacement = prepared replacement
suffix      = source [end, source_video_duration]

prefix + replacement + suffix
```

Zero-length prefix/suffix portions are omitted.

When audio exists, video/audio for each segment are passed together to one FFmpeg concat filter. This follows the concat filter's requirement that participating segments start at timestamp zero and keeps related AV segment boundaries explicit.

## VFR policy

`ProjectMediaRange` remains time-based rather than frame-number-based. Reinsertion does not force CFR.

The FFmpeg command uses:

```text
-fps_mode passthrough
```

so frame timestamps are not intentionally duplicated/dropped to create a constant frame rate. If a later delivery/export profile requires CFR, that belongs to the explicit export policy rather than the editing primitive.

## Mechanical output format

The current edited result is still an intermediate:

```text
container = Matroska
video     = FFV1 level 3
audio     = FLAC when present
lifecycle = intermediate
```

The source prefix/suffix are decoded and re-encoded. Therefore “preserved outside the range” does **not** mean byte-identical compressed source packets. It means the outside sections come only from the original source at the requested time boundaries and are not regenerated or semantically altered beyond the declared deterministic local encoding path.

## Output validation

UV Studio owns the output path:

```text
artifacts/art_<uuid>.mkv
```

A successful FFmpeg exit is not sufficient. Before project registration the adapter:

1. re-resolves the output inside the project artifact root;
2. rejects symlink/boundary escape;
3. requires a non-empty regular file;
4. FFprobes the result;
5. requires one video stream and the declared audio presence;
6. requires unchanged video geometry;
7. checks final video duration.

Expected output duration:

```text
source_video_duration_us
- requested_range_duration_us
+ replacement_video_duration_us
```

Allowed final validation deviation:

```text
250000 microseconds
```

A larger difference is a failed operation.

## Atomicity

The final artifact is registered only after validation.

Any composition/validation/project-registration failure deletes the newly allocated result file. The source and replacement inputs are never mutated.

## Capability/API behavior

The offer is:

```text
availability = available only when ffmpeg + ffprobe exist
locality     = local
cost_class   = free
```

Therefore normal execution uses `local_free_first` without D-017 authorization. Local failure never authorizes a remote or paid fallback.

The existing generic project capability endpoint executes the operation; there is no reinsertion-specific transport endpoint.

## Decision

Durable policy and acceptance gate are recorded in:

```text
project-context/decisions/D-022-deterministic-range-reinsertion.md
```
