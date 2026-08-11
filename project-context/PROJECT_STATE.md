# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 4 — Existing Video / Range Edit  
**Active branch:** `stage-4/range-reinsertion-foundation`  
**Main baseline:** `155f2e838e2a564b08775171646ab3b4a8be4349`  
**Open PR:** #19 — deterministic exact range reinsertion foundation  
**PR status:** draft only until the final documentation-frozen head passes the complete Linux/Windows matrix; D-022 is accepted and functional scope is frozen.

## Durable architecture snapshot

```text
Canonical Project
  -> RecipeDefinition / ProductionPolicy
  -> RecipeExecutionPlan
  -> semantic capability_id
  -> CapabilityRegistry
  -> CapabilityOffer
  -> SelectionPolicy
  -> ExecutionPreparation
  -> D-017 one-shot authorization when required
  -> exact execution adapter
      -> local_ffmpeg
          -> media.probe
          -> video.extract_range
          -> video.replace_range        # PR #19
          -> timeline.assemble
      -> mcp.<profile> exact binding
      -> native_videoclaw exact-offer compatibility
  -> canonical artifacts/tasks provenance
```

Existing-video edit identity is product-owned and provider-neutral:

```text
ProjectMediaRange
  -> project-relative source_path
  -> integer start_us / end_us
  -> optional bounded context_before_us / context_after_us
```

No generative provider owns the requested time range or the mechanical extraction/reinsertion semantics.

## Merged milestones on `main`

- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan;
- `7fb0ca88...` — semantic Capability Registry;
- `4cbe383f...` — fail-closed selection + safe local FFprobe/FFmpeg execution;
- `3e2b60329f7b8aa22fec38c012d703e3a8cca26d` — official-SDK direct MCP discovery + explicit semantic bindings;
- `4108db23f7de67293a53d1005a119a015539c0aa` — optional pinned Qwen-MM profile/binding pack (PR #12);
- `416677c4ca758a01b0253c8880b44d44150a8cec` — product-owned execution consent/cost boundary (PR #13);
- `bb7929dbbd8e5bd69bc509d98c58f4a56bb033c5` — authorized exact MCP execution + durable provenance (PR #14);
- `b76c25c0e97f9198bbaab848c2b3e6b99421b9d3` — explicit MCP project-file inputs + allowed-root symlink hardening (PR #15);
- `757cd1ca3831fd5f433a609dfca377a371c6b95e` — exact native VideoClaw Edge TTS execution behind D-017 consent (PR #17);
- `155f2e838e2a564b08775171646ab3b4a8be4349` — exact existing-video range/context extraction foundation (PR #18).

## Stable Stage 4 extraction foundation

PR #18 established D-021 and merged:

```text
video.extract_range
  -> local_ffmpeg.video_extract_range
  -> local + free
```

Key guarantees:

- exact persisted integer-microsecond range;
- fresh FFprobe duration validation;
- source video-stream duration preferred when available;
- bounded context before/after without changing requested range;
- accurate-seek decode/re-encode rather than stream copy;
- Matroska + FFV1 + FLAC lossless editing intermediates;
- `fps_mode=passthrough` rather than hidden CFR normalization;
- UV Studio-owned artifact paths;
- each generated clip re-probed before registration;
- full rollback if any segment fails;
- final PR #18 head passed Ubuntu/Windows unit, API, real HTTP and frontend matrix before merge.

Decision: `project-context/decisions/D-021-exact-media-range-extraction.md`.

## Current PR #19 — deterministic range reinsertion

### Semantic boundary

```text
capability_id = video.replace_range
offer_id      = local_ffmpeg.video_replace_range
locality      = local
cost_class    = free
```

Input:

```text
source_path
replacement_path
start_us
end_us
```

No output path, raw FFmpeg flags, filtergraph, shell command, provider/model or implicit retiming is accepted from the caller.

### Media contract

Both source and replacement are freshly FFprobed.

Current supported shape is intentionally narrow:

- exactly one video stream per input;
- zero or one audio stream per input;
- audio presence must match;
- no subtitle/data/other stream kinds;
- equal video resolution;
- known source/replacement format fields fail closed when they disagree (`pix_fmt`, SAR/color metadata, audio sample format/rate/channels/layout);
- source AV total duration difference <= 250 ms;
- replacement AV total duration difference <= 100 ms;
- AV stream `start_time` must be known and aligned within 10 ms for each input.

This prevents FFmpeg from silently solving incompatible replacement media in ways that would weaken the preservation claim.

### Duration policy

Replacement video is not stretched or trimmed.

```text
abs(replacement_video_duration_us - requested_range_duration_us) <= 100000
```

Anything larger fails before composition.

### Composition

The product-owned filtergraph builds only:

```text
prefix      = source [0, start)
replacement = prepared replacement clip
suffix      = source [end, source_video_duration]
```

Source video/audio timestamps are normalized to zero **before** `trim/atrim`, then each resulting segment is reset again before concat. This makes D-021 range time independent of non-zero encoded input PTS.

When audio exists, corresponding video/audio segment pairs are concatenated together.

Output policy:

```text
container = Matroska
video     = FFV1 level 3
audio     = FLAC when present
fps mode  = passthrough
lifecycle = intermediate
```

“Preserve outside range” means prefix/suffix come only from original source at the exact requested boundaries; the compressed result is not claimed byte-identical because the deterministic filtergraph re-encodes it.

### Output validation/atomicity

UV Studio allocates `artifacts/art_<uuid>.mkv`.

Before registration it requires:

- resolved containment in the artifact root;
- non-symlink, non-empty regular file;
- successful final FFprobe;
- one video stream and declared audio presence;
- unchanged geometry;
- final video duration within 250 ms of:

```text
source_duration - requested_range_duration + replacement_duration
```

Any failure deletes the new result and registers nothing.

### Tests in PR #19

Unit/API coverage includes:

- exact zero-based prefix/replacement/suffix filtergraph boundaries;
- VFR passthrough + FFV1/FLAC output policy;
- replacement duration mismatch/no hidden retiming;
- geometry/audio/unsupported-stream rejection;
- known pixel/audio format mismatch rejection;
- source AV duration mismatch rejection;
- missing/misaligned AV start-time rejection;
- raw output/FFmpeg injection and path escape rejection;
- failed/invalid final output cleanup;
- local/free registry availability requires FFmpeg + FFprobe;
- generic capability API prepare/execute path with no authorization token.

Decision: `project-context/decisions/D-022-deterministic-range-reinsertion.md` — **accepted**.  
Architecture detail: `docs/architecture/RANGE_REINSERTION.md`.

## CI / merge gate

Implementation/handoff head:

```text
b31bbcf9ea8e4d9055a329fc3da7171b9262e174
```

passed GitHub Actions CI run #409 with all four required jobs green:

- Ubuntu bootstrap/unit;
- Windows bootstrap/unit;
- Ubuntu API integration + real HTTP smoke + frontend build;
- Windows API integration + real HTTP smoke + frontend build.

Review threads were empty during audit. D-022 was then changed from proposed to accepted and this state file was synchronized. Those are documentation-only changes, but merge still requires the same 4/4 matrix on the final PR head after those changes.

No further repository file changes should be made before that final matrix unless CI exposes a regression.

## Permanent invariants

1. Recipe semantics never name provider/runtime implementation IDs.
2. Discovery/offer metadata never equals execution permission.
3. `local_free_first` never widens to remote or paid-capable offers.
4. Remote/non-free execution passes D-017 before invocation.
5. Tokens, secrets, raw remote errors and host-only paths never become portable project state.
6. MCP execution remains exact-binding/READY-digest-bound.
7. Native VideoClaw compatibility remains exact-offer-only.
8. Existing-video requested ranges use integer microseconds, not persisted floats or frame-only identity.
9. Extraction/reinsertion validate concrete files immediately before execution.
10. Raw FFmpeg/filtergraph/output-path injection is not part of semantic capability input.
11. VFR timing is not silently normalized to CFR in Stage 4 editing primitives.
12. Partial/invalid outputs never become successful project artifacts.
13. Mechanical reinsertion remains independent of replacement-generation provider.
14. Native Windows remains a required CI baseline.

## Not implemented yet

- provider-neutral continuity/replacement brief model;
- AI-generated replacement scene;
- automatic explicit retiming transform for mismatched replacements;
- VLM/continuity analysis of context before/after;
- prompt construction from local context;
- user-facing timeline range editor;
- final delivery/export codec policy;
- automatic intermediate lifecycle cleanup;
- Stage 5 dubbing and later workflows.

## Next slice after PR #19

After PR #19 is merged with a fully green final matrix, continue Stage 4 with the provider-neutral **range continuity / replacement brief** defined in `NEXT_TASK.md`.

The brief must preserve D-021/D-022 mechanical facts and exact range identity while keeping provider/model execution swappable.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
