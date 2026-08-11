# D-021 — Existing-video edit ranges use exact microseconds and lossless local intermediates

Status: accepted  
Date: 2026-08-11

## Decision

The canonical Stage 4 representation of a requested existing-video interval is a provider-neutral project-relative source path plus integer microsecond boundaries:

```text
source_path
start_us
end_us
context_before_us
context_after_us
```

The persisted/user-requested interval is not represented by binary floating point and is not represented only by frame numbers.

The first deterministic mechanical operation is exactly:

```text
capability_id = video.extract_range
offer_id      = local_ffmpeg.video_extract_range
adapter_id    = local_ffmpeg
locality      = local
cost_class    = free
```

It extracts the requested interval and, when requested, bounded context clips immediately before and after it. It does not generate or replace content.

## Why integer microseconds

Video sources may be variable-frame-rate, so a frame index is not a sufficient portable time coordinate. Decimal seconds serialized through ordinary binary floating point also create avoidable equality/rounding ambiguity in authorization, metadata and later range comparisons.

Integer microseconds provide a small deterministic project contract and map directly into FFmpeg duration syntax using the `us` unit.

This does **not** claim that every video can have a visual boundary at an arbitrary microsecond. Actual decoded video and audio boundaries remain constrained by stream timestamps, frame durations and sample timing.

## Range validity

`ProjectMediaRange` schema v1 requires:

- canonical project-relative `source_path`;
- integer `start_us >= 0`;
- integer `end_us > start_us`;
- integer non-negative context durations;
- each context side bounded to 30 seconds;
- requested `end_us <= source_duration_us` after the source is probed.

Boolean values are not accepted as integers.

The requested range is immutable. Context is resolved separately against the real source duration:

```text
context_start_us = max(0, start_us - context_before_us)
context_end_us   = min(source_duration_us, end_us + context_after_us)
```

Therefore clamping near the beginning/end of a source never silently changes the user's requested interval.

## Source-duration authority

Range execution must probe the concrete project file immediately before extraction.

FFprobe's decimal duration is converted to integer microseconds with decimal arithmetic. Existing `duration_sec` output remains for compatibility, but Stage 4 range validation uses `duration_us`.

An unknown/non-positive duration, a non-video source, or a requested end beyond the probed duration fails before FFmpeg extraction begins.

## Accurate-seek claim

Stage 4 extraction deliberately does **not** use stream copy.

FFmpeg input `-ss` is used together with ordinary transcoding. With FFmpeg's default accurate-seek behavior, data from the previous seek point up to the requested timestamp is decoded and discarded rather than preserved as it would be in stream-copy mode.

The truthful guarantee is therefore:

> accurate-seek decode/re-encode to the requested media timestamps, subject to the source stream's actual decoded frame/sample timestamps.

UV Studio does not label this primitive as arbitrary-microsecond frame-accurate editing.

## Intermediate codec/container policy

The first Stage 4 extraction artifacts are editing intermediates, not final exports:

```text
container = Matroska (.mkv)
video     = FFV1 level 3
audio     = FLAC when an audio stream exists
```

Rationale:

- FFV1 is a lossless intra-frame video codec implemented by FFmpeg;
- FLAC is lossless audio;
- the extraction step therefore does not intentionally add another lossy encode before later analysis/replacement/reinsertion;
- intra-frame video is suitable for subsequent deterministic editing at the cost of larger temporary files.

This is an intermediate policy, not the final delivery codec policy. Final export/reinsertion may use a different explicit codec policy later.

If a local FFmpeg build cannot provide the required encoder behavior, execution fails explicitly. The capability offer is available only when both FFmpeg and FFprobe are present; encoder capability probing may be tightened in a later packaging/runtime slice.

## Project output ownership

Callers cannot provide output paths or raw FFmpeg arguments.

UV Studio allocates each output under:

```text
artifacts/art_<uuid>.mkv
```

The operation may produce up to three canonical video artifacts:

```text
context_before
requested
context_after
```

Context artifacts are omitted when their resolved duration is zero.

The `CapabilityExecutionResult.artifact` field points to the primary requested-range artifact. All generated context artifacts are also registered in the canonical project and their portable paths are returned in structured output.

Artifact metadata contains only portable facts such as source project path, exact integer range, role and extraction policy. Absolute host paths are not persisted.

## Failure and atomicity policy

All subprocesses use argument arrays with `shell=false` and bounded timeouts.

If any segment extraction fails or creates an empty/missing file:

- every output planned by this execution is removed;
- no requested/context artifact from that execution is registered in the project.

Project artifact registration occurs only after all requested segments have been created and validated.

## Non-goals of this decision

This slice does not define:

- a generative replacement provider;
- prompt construction;
- VLM continuity analysis;
- reinsertion into the original source;
- a final-export codec policy;
- UI timeline controls;
- a claim of lossless final replacement of arbitrary source codecs.

Those later stages consume the exact provider-neutral range contract established here.

## Consequences

- Stage 4 begins from deterministic source mechanics rather than an AI provider.
- a 5–10 second edit no longer requires treating the whole video as the generation unit;
- later analysis can consume only the requested interval and bounded nearby context;
- later replacement/reinsertion can reuse the same exact range identity;
- VFR media is not forced into frame-number-only project semantics;
- stream-copy cannot be substituted into this extraction primitive while retaining the same precision claim.
