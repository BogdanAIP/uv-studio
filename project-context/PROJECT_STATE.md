# Project State

<!-- uv-active-slice: test-real-media-golden -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4A — Mechanical editing foundation / real-media proof

**Last verified `main` baseline:** `9b7e7cc13843aa0875836d8559d9d9492f67f3e5`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio is a local-first, provider-neutral video-production foundation with a product-owned canonical Project Store, Recipe Registry, Production Policy, Capability Registry, explicit D-017 authorization, bounded MCP/local/native adapters and deterministic targeted existing-video mechanics.

Stage 3.5 is now merged. D-025 gives UV Studio the application security boundary, and D-026 gives UV Studio ownership of its core/dev dependency graph. The default application no longer inherits the complete VideoClaw runtime route/dependency surface, and frontend lint/high-severity dependency audit/build are permanent Ubuntu/Windows gates.

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

## Stage 4A status

D-021/D-022 already provide exact integer-microsecond extraction and deterministic prepared-replacement reinsertion contracts, but their detailed media behavior is still proven mainly with fake subprocess runners.

The active slice `test-real-media-golden` turns that mechanical contract into real evidence by generating tiny deterministic media during CI and executing the actual installed `ffmpeg`/`ffprobe` binaries through `LocalFFmpegAdapter`.

Required evidence includes:

- CFR source with audio;
- VFR source with audio and observable variable frame timestamps;
- no-audio source;
- reproducible non-zero/offset timestamp source;
- compatible prepared replacement;
- observable prefix/replacement/suffix ordering;
- duration, geometry and audio-policy validation through real ffprobe;
- real rollback/failure evidence in addition to the existing fast mocked unit contracts;
- output size/runtime measurements for the current whole-output FFV1/FLAC reinsertion policy.

FFmpeg provisioning is explicit in CI on both Ubuntu and Windows rather than treated as an undocumented runner-image assumption.

## Decision after evidence

The current handoff points to `stage-4-range-continuity-brief` only as the expected path if measured real-media evidence does not reveal a mechanical/state-model blocker.

If the real tests show that current whole-output FFV1/FLAC reinsertion is unsuitable even as an intermediate, or expose a structural range/timestamp defect, the coordinator will change the handoff before merge to a scoped media-edit-core refactor. The decision must follow measured evidence, not roadmap preference.

## Remaining cross-cutting gaps

- D-023 still needs an explicit post-merge/idle lifecycle state and live write-scope diff enforcement;
- free-form canonical `settings`, `extensions` and reference `metadata` still need proportionate typed portability enforcement before durable Stage 4B intelligence state is added;
- Stage 4C user timeline/preview/accept/export workflow remains later work.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
