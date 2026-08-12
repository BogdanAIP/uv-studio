# Stage 4C editor-foundation spike

This spike selected reusable editor foundations by executable evidence rather than product screenshots or upstream roadmaps.

## Selected composition

D-033 selects a hybrid foundation:

- **MLT** — editing/timeline engine behind a UV Studio-owned adapter;
- **OpenCut Classic** pinned at `cf5e79e919144200294fb9fed22a222592a0aeea` — MIT editor UX/component donor;
- **UV Studio** — canonical Project Store/domain state, Command API, validation/security, AI workflow and accepted-edit lifecycle;
- **UV Studio FFmpeg renderer** — remains authoritative final export initially, until another render path earns parity evidence.

`libopenshot` remains an engine fallback/component source, not the selected primary engine.

## Why MLT won

The Linux MLT probe (`7.22.0`) uses generated real media and passes every required capability in `candidate-matrix.json`, including timeline creation/query, multitrack edits, trim/split/ripple, state serialization and round-trip, external programmatic mutation, preview and real render/export.

A separate Windows deployment probe extracts a SHA-256-pinned official KDE Kdenlive standalone package, locates its relocatable MLT `melt.exe` runtime (`7.40.0`) and bundled FFmpeg, generates media, mutates serialized MLT XML outside the engine process and renders the mutated project successfully. This proves a no-system-install Windows engine path without committing the final product to redistributing the whole Kdenlive application.

## Why libopenshot was not selected

The independent `libopenshot` `0.3.2` probe can perform most ordinary editing and render operations, but its tested Timeline JSON did not cleanly round-trip through `SetJson`, and the serialized clip did not expose a reliable ID for the expected `ApplyJsonDiff` mutation seam. Both are important for the single UV-owned GUI/script/AI/MCP command architecture.

## Why OpenCut Classic is a donor, not the product core

The pinned OpenCut Classic source probe confirms an MIT license and substantial implemented editor/timeline code: timeline state/store, track logic, ruler/scale/zoom, drag, snapping and update/creation helpers. Roadmap-only Editor API/MCP/headless claims are intentionally not credited.

UV Studio will selectively adapt useful editor components behind its own adapter. OpenCut storage, backend, authentication and unrelated application architecture do not become canonical UV Studio dependencies by default.

## Evidence

Workflow run `31608137802` at head `bc0433e0b2781ffca805f8e6644b65cf9a801764` uploaded four evidence bundles:

- MLT Linux: `sha256:dcac97a703bc1433467f81daa2ca75144e70561799fec14d026d409301ecc7ff`
- MLT Windows: `sha256:e864d85c6fc346c27970dea8f38bdf506530acd7a91f8cf644efaa4c4f977644`
- libopenshot: `sha256:babfe823a7d2dda6d903d16cdd7559af3f8dd356ffe1598d0d283f23aa7583c9`
- OpenCut Classic: `sha256:9ddfdfefcd1b719a7c361a26766b71a5cfc9008d87d34b101eec1b21b08a9e46`

The workflow sets `include-hidden-files: true`, so generated source media, rendered outputs, serialized state and JSON reports under `.spike-output` are preserved rather than only appearing in logs.

## Permanent architecture test

The key result is not merely that MLT can render. Stage 4C must expose meaningful editing mutations through one product-owned Command API:

```text
Editor GUI ─┐
User script ├─> UV Studio Command API -> validation/domain transaction -> MLT adapter
AI action   ┤
MCP         ┘
```

Raw MLT/OpenCut state never becomes a bypass around Project Store path rules, D-017 execution authorization, D-032 review approval or D-028 accepted-edit state.
