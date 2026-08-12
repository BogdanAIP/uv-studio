# Project State

<!-- uv-active-slice: test-real-media-golden -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4A — Mechanical editing foundation / real-media proof

**Last verified `main` baseline:** `9b7e7cc13843aa0875836d8559d9d9492f67f3e5`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio is a local-first, provider-neutral video-production foundation with a product-owned canonical Project Store, Recipe Registry, Production Policy, Capability Registry, explicit D-017 authorization, bounded MCP/local/native adapters and deterministic targeted existing-video mechanics.

Stage 3.5 is merged. D-025 gives UV Studio the application security boundary, D-026 gives UV Studio ownership of its core/dev dependency graph, and frontend lint/high-severity dependency audit/build are permanent Ubuntu/Windows gates.

The stable product-owned execution path is:

```text
Canonical Project
  -> Recipe / Production Policy
  -> semantic capability
  -> CapabilityOffer
  -> SelectionPolicy
  -> execution preparation
  -> D-017 authorization when required
  -> exact adapter
  -> portable artifact/provenance
```

## Stage 4A real-media result

PR #24 now executes the actual installed FFmpeg/FFprobe binaries through `LocalFFmpegAdapter` on both Ubuntu and Windows. Deterministic fixtures are generated at test time, so no binary media files are committed.

The current evidence proves the existing D-021/D-022 mechanical path across two different FFmpeg generations:

- CFR + audio exact extraction and prepared-replacement reinsertion;
- VFR extraction preserving observable 33/34 ms and 66/67 ms frame intervals;
- no-audio extraction/reinsertion without introducing an audio stream;
- source with `1.250000` second mux timestamp offset while project range coordinates remain zero-based;
- visible blue/red/blue prefix/replacement/suffix ordering by decoded pixel sampling;
- real produced-file rollback leaving no registered or on-disk artifact after a later injected FFmpeg failure.

No mechanical adapter defect was exposed by these deterministic representative fixtures.

## D-027 measured state-model decision

The first correctness fixture compared FFV1 input with FFV1 output and therefore could not answer whether whole-output FFV1 was appropriate for ordinary compressed media.

A separate 8-second 320x180 30-fps MPEG-4 source measurement now provides that evidence:

| Platform | Source | Whole-output FFV1 | Ratio | Reinsertion |
|---|---:|---:|---:|---:|
| Ubuntu | 713,056 B | 3,440,122 B | **4.824x** | 389 ms |
| Windows | 713,058 B | 3,440,072 B | **4.824x** | 397 ms |

The output duration remained exactly 8 seconds on both platforms.

D-027 therefore keeps the current FFV1/FLAC path as a deterministic correctness/render/intermediate mechanism but rejects a complete newly materialized lossless file as canonical state for every accepted short edit.

The next slice is now `stage-4-non-destructive-edit-state`, not RangeContinuityBrief. It will persist provider-neutral source + exact range + accepted replacement edit decisions and render them explicitly only when preview/export requires media materialization.

Complete evidence: `project-context/evidence/STAGE_4A_REAL_MEDIA.md`.

## Following Stage 4 work

After the non-destructive edit-state boundary is proven portable and deterministic, return to `stage-4-range-continuity-brief` for bounded provider-neutral continuity/intelligence state.

Stage 4C still owns the later complete timeline/preview/accept/export user workflow.

## Remaining cross-cutting gaps

- D-023 still needs an explicit post-merge/idle lifecycle state and live write-scope diff enforcement;
- free-form canonical `settings`, `extensions` and reference `metadata` still need proportionate typed portability enforcement before durable Stage 4B intelligence state is added;
- device-specific phone/OBS/AAC-priming/H.264/H.265 GOP fixture coverage remains incremental hardening beyond the deterministic baseline.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
