# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 4 — Existing Video / Range Edit  
**Active branch:** `stage-4/range-edit-foundation`  
**Main baseline:** `757cd1ca3831fd5f433a609dfca377a371c6b95e`  
**Open PR:** #18 — exact existing-video range extraction foundation  
**PR status:** draft while final Linux/Windows CI and final diff audit are completed.

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
          -> timeline.assemble
      -> mcp.<profile> exact binding
      -> native_videoclaw exact-offer compatibility
  -> canonical artifacts/tasks provenance
```

Existing-video editing now has a product-owned exact time contract:

```text
ProjectMediaRange
  -> project-relative source_path
  -> integer start_us / end_us
  -> bounded context_before_us / context_after_us
  -> resolve against freshly probed source_duration_us
  -> requested range remains unchanged
  -> context clamps to source boundaries
```

Permanent rules:

- discovery/availability is not execution permission;
- local failure never silently widens into remote or paid execution;
- raw host paths and raw FFmpeg commands are not generic capability inputs;
- machine commands, resolved secrets and authorization tokens are not portable project state;
- Qwen-MM and OpenClaw are optional peer integrations;
- native VideoClaw compatibility never means arbitrary vendored function execution;
- existing-video edit identity is provider-neutral and must not depend on a generative model;
- native Windows remains a first-class baseline.

## Merged milestones on `main`

- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan;
- `7fb0ca88...` — semantic Capability Registry;
- `4cbe383f...` — fail-closed selection + safe local FFprobe/FFmpeg execution;
- `3e2b60329f7b8aa22fec38c012d703e3a8cca26d` — official-SDK direct MCP discovery + explicit semantic bindings;
- `4108db23f7de67293a53d1005a119a015539c0aa` — optional pinned Qwen-MM profile/binding pack (PR #12);
- `416677c4ca758a01b0253c8880b44d44150a8cec` — product-owned execution consent/cost boundary (PR #13);
- `bb7929dbbd8e5bd69bc509d98c58f4a56bb033c5` — authorized exact MCP `call_tool()` + durable provenance (PR #14);
- `b76c25c0e97f9198bbaab848c2b3e6b99421b9d3` — explicit MCP project-file inputs + allowed-root symlink hardening (PR #15);
- `757cd1ca3831fd5f433a609dfca377a371c6b95e` — exact native VideoClaw Edge TTS execution behind D-017 consent (PR #17).

## Stable Stage 3 boundary

### Local deterministic execution

Stable local/free capabilities before Stage 4:

```text
local_ffmpeg.media_probe       -> media.probe
local_ffmpeg.timeline_assemble -> timeline.assemble
```

### External execution

D-017 authorization remains transport-independent:

```text
remote_execution  -> remote/hybrid locality
external_cost     -> potentially_paid/paid
unknown_cost      -> external price estimate unknown
```

One-shot grants are process-local, short-lived and exact-input-bound. Tokens are never archived.

Direct MCP execution remains exact-binding + READY-configuration-digest-bound. Explicit `MCPProjectFileInput` is the only generic MCP project-file translation mechanism; generic exposable roots are `sources`, `assets`, `artifacts`, `exports`. Resolved symlinks cannot cross a binding's allowed-root boundary.

Native VideoClaw compatibility is exact-offer-only. `native_videoclaw.edge_tts -> speech.synthesize` is the first executable native offer, remains remote/free, requires `remote_execution` consent and is optional through `requirements-edge-tts.txt`.

## Current PR #18 — Stage 4 exact range/context extraction

### 1. Exact portable time model

Added `uv_studio/projects/media_ranges.py` with schema-v1 `ProjectMediaRange`.

Canonical fields:

```text
source_path
start_us
end_us
context_before_us
context_after_us
```

Rules:

- integer microseconds only; booleans/floats are rejected;
- `start_us >= 0`;
- `end_us > start_us`;
- source path is canonical project-relative;
- each context side is bounded to 30 seconds;
- requested range is preserved exactly;
- context is clamped only during resolution against the actual source duration;
- `end_us` must not exceed the freshly probed source duration.

Frame number is not the canonical identity because VFR media must remain representable without forcing a constant-frame-rate timeline.

Decision: `project-context/decisions/D-021-exact-media-range-extraction.md`.

### 2. Exact FFprobe duration

`media.probe` keeps compatibility field:

```text
duration_sec
```

and now also returns:

```text
duration_us
```

`duration_us` is parsed with decimal arithmetic rather than binary floating point. If container-format duration is unavailable, the probe falls back to the maximum valid stream duration.

Stage 4 validation uses the integer value.

### 3. New semantic capability

Registered:

```text
capability_id = video.extract_range
offer_id      = local_ffmpeg.video_extract_range
adapter_id    = local_ffmpeg
locality      = local
cost_class    = free
```

The offer is `AVAILABLE` only when both FFmpeg and FFprobe are present.

Therefore `local_free_first` may select/execute the operation without an authorization token and cannot widen into a remote model merely because local extraction fails.

### 4. Extraction contract

Input contains only semantic fields:

```text
source_path
start_us
end_us
context_before_us
context_after_us
```

Caller cannot provide:

- output path;
- raw FFmpeg arguments;
- codec override;
- shell command.

Execution:

1. resolves source through Project Store approved readable roots;
2. probes the concrete source;
3. requires a video stream and known positive duration;
4. validates requested end against real duration;
5. derives non-empty context-before/requested/context-after segments;
6. allocates UV Studio-owned `artifacts/art_<uuid>.mkv` paths;
7. extracts each segment with argv + `shell=false` and bounded timeout;
8. validates each created file is non-empty;
9. registers all artifacts in one project update only after every planned segment succeeds.

Any segment failure removes every planned output from that execution and registers nothing.

### 5. Truthful precision / intermediate policy

Stage 4 extraction does not use stream copy.

FFmpeg receives input `-ss` and output `-t` expressed with the `us` duration unit and performs decode/re-encode. The truthful precision claim is:

```text
accurate-seek decode/re-encode to requested media timestamps,
subject to actual decoded frame/sample timestamps
```

UV Studio does not claim an arbitrary visual frame boundary at every microsecond.

For VFR sources the command explicitly uses:

```text
-fps_mode passthrough
```

to avoid implicit frame duplication/drop caused by CFR conversion.

Editing intermediates use:

```text
container = Matroska (.mkv)
video     = FFV1 level 3
audio     = FLAC when present
lifecycle = intermediate
```

This avoids intentionally adding a lossy encode before later analysis/replacement/reinsertion. It is not a final-delivery codec policy.

### 6. Context artifacts

One execution may create:

```text
context_before
requested
context_after
```

Zero-length context at a source boundary is omitted.

All are canonical project video artifacts. `CapabilityExecutionResult.artifact` identifies the primary requested-range artifact; structured output also exposes portable paths for context artifacts.

Metadata records only portable source/range/role/policy facts, never host absolute paths.

### 7. Tests added

Unit coverage includes:

- microsecond round-trip and schema validation;
- negative/reversed/bool/float rejection;
- path traversal/absolute-path rejection;
- bounded context and boundary clamping;
- exact source-duration containment;
- FFprobe decimal -> integer microseconds;
- stream-duration fallback;
- FFV1/FLAC extraction argv;
- explicit `fps_mode=passthrough` for VFR-safe timing;
- no-context single-artifact behavior;
- non-video/out-of-duration rejection before FFmpeg;
- output-path/raw-FFmpeg injection rejection;
- partial multi-segment rollback;
- zero-byte output rejection;
- local/free registry availability requires both FFmpeg + FFprobe.

API coverage includes:

- prepare-execution reports no consent for the local/free range offer;
- `local_free_first` executes the exact range capability without a token;
- requested/context artifacts remain project-relative through the HTTP capability boundary.

## CI status

PR #18 CI has already shown the new unit suite green on Ubuntu on the current implementation line; earlier implementation heads also passed Windows unit and Ubuntu API coverage. Documentation/VFR-hardening changes moved the final head again, so merge acceptance still requires the complete four-job matrix on one final commit:

- Ubuntu bootstrap/unit;
- Windows bootstrap/unit;
- Ubuntu API integration + HTTP smoke + frontend build;
- Windows API integration + HTTP smoke + frontend build.

Do not merge PR #18 until all four are green on the same frozen head and the final diff/review audit is clean.

## Not implemented yet

Stage 4 still does **not** include:

- replacement clip reinsertion into the original source;
- generative replacement;
- prompt construction;
- VLM continuity analysis;
- timeline UI selection controls;
- final delivery codec policy;
- automatic lifecycle cleanup of intermediate range/context artifacts.

Later layers must reuse the exact `ProjectMediaRange` identity rather than inventing provider-specific timing semantics.

## Current invariants

1. Recipe semantics never name provider/runtime-specific implementation IDs.
2. Discovery/offer metadata never equals execution permission.
3. `local_free_first` never widens to remote or paid-capable offers.
4. Remote/non-free execution passes D-017 before invocation.
5. Tokens, secrets, raw remote errors and host-only paths never become portable project state.
6. MCP execution remains exact-binding/READY-digest-bound.
7. Native VideoClaw compatibility remains exact-offer-only.
8. Existing-video requested ranges use integer microseconds, not persisted floats or frame-only identity.
9. Context is bounded and cannot silently widen/change the requested interval.
10. Range execution validates against a freshly probed real source duration.
11. Range outputs are UV Studio-owned and raw FFmpeg/output-path injection is impossible through the semantic payload.
12. Range extraction is transcode-based accurate seek; stream copy cannot be substituted while keeping the same precision claim.
13. VFR extraction explicitly preserves frame timestamps rather than silently normalizing to CFR.
14. Partial/empty range outputs never become successful project artifacts.
15. Native Windows remains a required CI baseline.

## Next slice after PR #18

After PR #18 is merged with one fully green final matrix, continue Stage 4 with a **deterministic reinsertion contract**:

```text
source video
+ exact ProjectMediaRange
+ replacement clip
-> canonical edited output
```

The reinsertion slice must prove that content outside the requested range is preserved under an explicit codec/timestamp policy. It must not use concat-copy unless compatibility is actually verified, and it must remain independent of any generative replacement provider. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
