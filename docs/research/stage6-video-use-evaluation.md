# Stage 6 reuse-first evaluation: video-use and bounded sequence inspection

Date: 2026-08-14

## Problem

Stage 6 needs useful continuity context around linked-shot boundaries without forcing whole-video frame ingestion, a provider-specific project model or expensive visual analysis on every clip. It also needs evidence from the produced take before acceptance.

## `browser-use/video-use`

Evaluated upstream: `browser-use/video-use` at commit `92c2b34e44c205cbc2acae7f6ca7c1c219d5dd66`, MIT.

The strongest design ideas are not its editing presets but its information architecture:

- transcript/structured text is the compact primary reasoning surface when speech matters;
- `timeline_view` drills into a bounded time range using sampled frames, waveform and word labels only at decision points;
- agent decisions are separated from deterministic render execution;
- rendered output is inspected again around edit boundaries before presentation;
- the self-review loop is bounded rather than allowed to run indefinitely.

### What Stage 6 adopts

UV Studio adopts the pattern **structured project state + on-demand bounded visual inspection + review of actual output**.

For linked shots, the important boundary is normally the accepted anchor tail versus the candidate take head. A UV-owned TimelineContext therefore needs exact media identity, bounded windows and sampled visual/audio/timeline facts. It does not need to scan or persist every frame.

### What Stage 6 rejects

Direct integration is not appropriate:

- `project.md`, `takes_packed.md` and `edl.json` would compete with UV Project Store/domain state;
- Scribe transcription is directly tied to an ElevenLabs API key;
- helper scripts assume an agent workspace and shell-oriented lifecycle;
- several FFmpeg editing rules are useful defaults for one class of edit but are not universal professional-editor invariants;
- the upstream project has active open work around Windows behavior, path traversal, A/V drift and local Whisper support, so importing the helper layer wholesale would also import unrelated maintenance surface.

No source code is copied. The repository is an architecture/reference donor only.

## PySceneDetect

Evaluated as a credible reusable primitive for automatic shot boundaries. Current 0.7.x is BSD-3-Clause and supports Python/library usage plus VFR-aware processing.

Stage 6 baseline does not require automatic scene segmentation: linked shots and takes are explicit user/project objects, so introducing a detector would add dependency and calibration complexity without serving the core user outcome. If later automatic shot discovery is required, PySceneDetect should receive a reproducible spike before any custom detector is written.

## Selected Stage 6 approach

1. Canonical optional sequence state remains UV-owned and typed.
2. Planned shot continuity and observed accepted-take state are separate.
3. Every take binds exact registered project media bytes.
4. Later shots bind an explicit accepted anchor take; re-anchor is an explicit operation.
5. TimelineContext is derived/transient and bounded; it is not a saved second timeline.
6. Exact candidate/anchor frames are requested on demand through UV endpoints/adapters using the existing deterministic media toolchain.
7. Review records bind the exact plan, anchor and take bytes and can cite bounded local evidence.
8. Optional VLM review uses Capability Registry + D-017; manual review remains sufficient.
9. Existing targeted-edit and dubbing workflows remain unchanged when sequence continuity is not enabled.

## Adoption gate for additional dependencies

No new general media dependency enters Stage 6 merely because it is convenient. Any later candidate must demonstrate a concrete missing primitive on representative Windows/Linux media, license compatibility, maintenance value over FFmpeg/MLT/current UV helpers, and a clean adapter boundary before adoption.
