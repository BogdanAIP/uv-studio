# D-022 — Exact range reinsertion is deterministic, duration-bounded and provider-neutral

Status: proposed  
Date: 2026-08-11

## Context

D-021 established an exact provider-neutral edit identity for existing video:

```text
ProjectMediaRange
  -> source_path
  -> start_us
  -> end_us
```

and a deterministic local extraction primitive. The next mechanical requirement is to take a prepared replacement clip and put it back into the exact requested interval without making the reinsertion step depend on the system that produced the replacement.

The reinsertion layer must therefore solve media/timestamp mechanics only. Generative models, prompt construction and provider selection stay above this boundary.

## Proposed decision

Add the semantic capability:

```text
capability_id = video.replace_range
offer_id      = local_ffmpeg.video_replace_range
adapter_id    = local_ffmpeg
locality      = local
cost_class    = free
```

Semantic input is exactly:

```text
source_path
replacement_path
start_us
end_us
```

The source interval is represented by the existing schema-v1 `ProjectMediaRange`; reinsertion does not introduce a second time coordinate system.

## No hidden retiming

The first contract does not stretch, speed-change, pad or trim the replacement to make it fit.

The replacement video duration must match the requested interval within:

```text
100_000 microseconds (100 ms)
```

A larger mismatch fails before FFmpeg composition.

The small tolerance exists only for normal timestamp/frame-boundary differences between encoded media and the exact project range. It is not permission to perform an implicit retime.

If explicit retiming is added later, it must be a separate semantic transformation or an explicit policy input.

## Narrow stream and format contract

The first reinsertion contract intentionally supports a narrow, auditable media shape:

- exactly one video stream in source;
- exactly one video stream in replacement;
- at most one audio stream in each;
- source and replacement must either both have audio or both be silent;
- source and replacement video resolution must match;
- unsupported additional stream kinds such as subtitles/data fail closed rather than being silently discarded.

When FFprobe reports both values, the following source/replacement properties must also match rather than being left to implicit concat negotiation:

```text
video: pix_fmt, sample_aspect_ratio,
       color_range, color_space, color_transfer, color_primaries

audio: sample_fmt, sample_rate, channels, channel_layout
```

Unknown properties are not invented. A known mismatch fails before FFmpeg.

The source audio/video durations must agree within 250 ms. The replacement audio/video durations must agree within 100 ms.

For AV inputs, FFprobe stream `start_time` must be known for both video and audio. Their relative start must agree within:

```text
10_000 microseconds (10 ms)
```

for both source and replacement. A larger or unknown AV start offset fails closed because independently zeroing the streams could otherwise alter lip-sync.

## Mechanical composition

The first implementation uses one product-owned FFmpeg filtergraph rather than caller-provided commands or concat-copy.

Conceptually:

```text
prefix      = source [0, start)
replacement = prepared replacement clip
suffix      = source [end, source_video_duration]

prefix + replacement + suffix -> output
```

`ProjectMediaRange` is zero-based media time. Source video/audio timestamps are therefore normalized **before** range trimming and each resulting segment is normalized again before concat:

```text
video:
  setpts=PTS-STARTPTS
  -> trim(start_us, end_us)
  -> setpts=PTS-STARTPTS

audio:
  asetpts=PTS-STARTPTS
  -> atrim(start_us, end_us)
  -> asetpts=PTS-STARTPTS
```

The replacement is also normalized to a zero start timestamp before concat.

When audio is present, corresponding video/audio segments are concatenated together in one concat filter so the segment relationship is explicit.

The filtergraph is constructed by UV Studio from validated integer microseconds. It is not accepted from API input.

## VFR policy

Canonical project time remains integer microseconds, not frame number.

The output command explicitly uses:

```text
-fps_mode passthrough
```

The first mechanical reinsertion policy therefore does not intentionally normalize a variable-frame-rate input to constant frame rate.

If a future delivery format requires CFR, that must be a separate declared output/export policy.

## Intermediate output policy

The first reinsertion result is still an editing artifact rather than a final delivery encode:

```text
container = Matroska (.mkv)
video     = FFV1 level 3
audio     = FLAC when present
lifecycle = intermediate
```

This avoids deliberately adding a lossy codec stage while Stage 4 editing is still in progress.

This does **not** mean that the compressed output is byte-identical to the original source outside the range. The source is mechanically decoded and re-encoded through the filtergraph.

For this decision, “preserve outside the requested range” means:

> Prefix and suffix are derived only from the original source at the exact D-021 time boundaries and are not regenerated or semantically transformed; any mechanical representation change is limited to the declared local composition/encoding policy.

## Output ownership and validation

The caller cannot provide an output path.

UV Studio allocates:

```text
artifacts/art_<uuid>.mkv
```

After FFmpeg exits successfully, the implementation must still:

1. re-resolve the output through `ProjectStore` inside the allowed artifact root;
2. reject symlink/boundary escape;
3. require a non-empty regular file;
4. re-probe the output with FFprobe;
5. require the declared video/audio stream shape;
6. require the source geometry to remain unchanged;
7. validate final video duration against the declared composition equation.

Expected final video duration is:

```text
source_video_duration_us
- requested_range_duration_us
+ replacement_video_duration_us
```

The first validation tolerance is:

```text
250_000 microseconds (250 ms)
```

A larger discrepancy is a failed composition, not a successful artifact.

## Failure atomicity

The final artifact is registered only after all validation succeeds.

If composition, output resolution, file validation, FFprobe validation or project registration fails:

- the newly allocated output file is removed;
- no final artifact is registered;
- the pre-existing source/replacement files are untouched.

## Security boundary

The API does not accept:

- raw FFmpeg arguments;
- raw filtergraph text;
- shell commands;
- host output paths;
- provider/model identifiers.

All subprocess execution continues through argv with `shell=false` and bounded timeout inherited from the local FFmpeg adapter.

## Non-goals

This decision does not add:

- AI replacement generation;
- automatic replacement retiming;
- style/character continuity analysis;
- provider selection;
- prompt construction;
- dubbing/music workflow;
- final delivery encoding;
- timeline UI.

Those later layers consume `ProjectMediaRange` and `video.replace_range` rather than replacing the deterministic boundary.

## Acceptance gate

Change this decision from `proposed` to `accepted` only after:

- unit tests prove the duration/audio/geometry/timestamp/path/failure contracts;
- the capability API proves token-free local execution;
- final diff/security audit is clean;
- Ubuntu + Windows bootstrap/unit pass;
- Ubuntu + Windows API/HTTP/frontend app-baseline pass on the same frozen head.
