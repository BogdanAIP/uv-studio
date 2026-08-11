# Next Task

Updated: 2026-08-11

## Primary target

After PR #17 is merged with the full Linux/Windows matrix green, begin the first **Stage 4 — Existing Video / Range Edit** foundation.

The first Stage 4 slice must stay deterministic and local. Do not add generative replacement yet. Establish a correct project-owned representation of a requested media range and safe FFmpeg primitives for extracting that range plus its surrounding context.

## Why this is next

Stage 3 now has the execution boundaries needed by product workflows:

- canonical Project Store;
- provider-neutral recipes/capabilities;
- fail-closed local/free selection;
- product-owned D-017 external consent;
- exact MCP execution and project-file translation;
- first exact native compatibility execution (`native_videoclaw.edge_tts`).

The roadmap explicitly requires Stage 4 to edit only a requested interval of an existing video without regenerating the whole source. The next useful product capability is therefore not another provider integration; it is a trustworthy range-edit substrate that later local or generative replacements can share.

## Required implementation

### 1. Project-owned range representation

Add a small versioned model for an exact interval in a source media file.

It must represent at least:

```text
source_path
start
end
```

Requirements:

- canonical project-relative `source_path`;
- no negative time;
- `end > start`;
- validate against probed source duration before execution;
- avoid persisted binary floating-point ambiguity; prefer a deterministic integer time unit (for example microseconds) or another explicitly serialized exact representation;
- no provider/model/runtime identity in the range model.

Do not make frame number the only canonical representation because projects may contain variable-frame-rate media. Frame/time metadata may be added as derived evidence later.

### 2. Explicit context window

Stage 4 needs context before and after the requested edit so later replacement generation/review can preserve continuity.

Define bounded optional context durations, for example:

```text
context_before
context_after
```

The resolved context range must clamp to `[0, source_duration]` rather than underflow/overflow.

Persist the requested range separately from derived context boundaries so the user's requested interval is never silently changed.

### 3. Deterministic local extraction capability

Add a provider-neutral semantic capability for extracting a project video interval and a `local_ffmpeg` offer for it.

The API must accept only semantic fields, not raw FFmpeg flags.

Minimum behavior:

- input video only from approved readable project roots;
- requested range validated against real `media.probe` duration;
- output path owned by UV Studio under `artifacts/`;
- no overwrite;
- subprocess argv only, `shell=false`;
- bounded timeout;
- partial output removed on failure;
- successful output registered as a canonical video artifact;
- artifact metadata records the portable source path and exact requested range.

For correctness, do not claim frame-accurate cutting if the chosen FFmpeg mode only seeks to keyframes. Either use a re-encode path with an explicit bounded codec policy or document/test the actual precision guarantee.

### 4. Context extraction

Using the same validated range model, create deterministic artifacts for:

```text
context_before clip
requested_range clip
context_after clip
```

where the context clips are non-empty.

These are production inputs for later analysis/replacement, not three independent user-selected edits.

Do not persist machine-only absolute paths.

### 5. Keep reinsertion contract separate

Design the reinsertion/replacement semantic contract in this slice, but implement it only if the exact media/codec behavior can be made truthful and regression-tested without silently changing source characteristics.

The eventual contract must take:

```text
source video
exact requested range
replacement clip
```

and produce one canonical output while preserving content outside the requested range.

Do not fake this with concat-copy if stream compatibility or timestamp behavior makes the result unreliable. A controlled re-encode is preferable to a falsely lossless claim.

### 6. No generative work in this slice

Explicit non-goals:

- no AI-generated replacement scene;
- no provider selection work;
- no prompt generation;
- no VLM continuity review yet;
- no dubbing/music-specific behavior;
- no UI timeline editor yet unless a minimal API contract needs representation testing.

This slice creates the deterministic foundation those later workflows depend on.

## Tests required

At minimum prove:

1. invalid/negative/reversed ranges are rejected;
2. ranges beyond source duration fail clearly;
3. context windows clamp correctly at source start/end;
4. project traversal and raw host paths are rejected;
5. caller cannot inject raw FFmpeg options;
6. extraction uses argv with `shell=false`;
7. output path is UV Studio-owned and stays under `artifacts/`;
8. partial output is removed on FFmpeg failure;
9. successful extraction creates a canonical video artifact with portable range metadata;
10. source/project absolute paths do not enter portable metadata;
11. local-free selection remains local/free and token-free;
12. Windows and Linux unit/API CI remain green;
13. at least one generated tiny local fixture validates real FFmpeg/FFprobe behavior when FFmpeg is available in CI, or the existing subprocess seam is used deterministically if the CI image guarantee is insufficient.

## Architecture questions to settle during implementation

- exact persisted time unit/serialization;
- truthful cut precision guarantee and whether extraction re-encodes;
- deterministic output codec/container policy for Stage 4 artifacts;
- whether context artifacts are first-class `ProjectReference`s or task-intermediate artifacts with explicit lifecycle;
- exact semantic IDs for extraction and later replacement.

Resolve these from the current code/tests and FFmpeg behavior; record a new decision if the choice becomes durable.

## Expected files

Likely changes:

- project-owned range model/module;
- built-in semantic capability/offer definitions;
- `uv_studio/capabilities/adapters/local_ffmpeg.py`;
- capability execution tests;
- range model/unit tests;
- API tests if a project-scoped range endpoint is added;
- architecture documentation/decision;
- `project-context/PROJECT_STATE.md`;
- this file.

## Gate before starting

Do not begin this Stage 4 slice from an unmerged or red PR #17. First confirm:

- PR #17 exact final head has all four required CI jobs green;
- PR #17 review threads are resolved;
- PR #17 is merged to `main`;
- new Stage 4 branch is created from that merged `main`.
