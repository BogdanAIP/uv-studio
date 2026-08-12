# D-033 — Reuse-first scriptable editor foundation

Status: accepted  
Date: 2026-08-12

## Decision

UV Studio adopts two permanent architecture constraints for the Stage 4C editor and later media-editing work.

First, editor/media infrastructure is **reuse-first and orchestration-first**: a mature, maintained/stable-enough, professional and license-compatible open-source component is integrated before UV Studio writes an equivalent general-purpose primitive. Custom code is reserved for UV-specific orchestration, bounded adapters/integration, canonical domain rules, security, or a documented technical gap.

Second, editor mutations use **one UV Studio-owned Command API**. GUI actions, user scripts, AI actions and MCP automation invoke the same validated command contracts. No caller receives a privileged route that directly mutates canonical timeline/project state.

The selected Stage 4C composition is:

- **MLT** as the editing/timeline engine behind a UV-owned adapter;
- **OpenCut Classic**, pinned at `cf5e79e919144200294fb9fed22a222592a0aeea`, as an MIT editor-UX/component donor for implemented timeline/editor primitives that are useful to UV Studio;
- **UV Studio Project Store and UV domain state remain canonical**;
- the existing UV Studio FFmpeg one-pass path remains the authoritative final accepted-edit export initially. MLT render capability is available and proven, but it is not promoted to canonical export until preview/render parity and product invariants are explicitly tested.

`libopenshot` remains a possible fallback/component source but is not the selected primary editing engine.

## Executable evidence

The repository-owned `editor-foundation-spike` workflow produced reproducible evidence at head `bc0433e0b2781ffca805f8e6644b65cf9a801764`, workflow run `31608137802`.

### MLT on Linux

The Ubuntu probe used MLT Python bindings `7.22.0` with generated real media and passed all 16 required capabilities:

1. open/probe real source media;
2. create a timeline/edit model;
3. add clips;
4. multiple tracks/layers;
5. move/reposition clips;
6. trim in/out;
7. split/cut;
8. ripple/reorder equivalent;
9. query timeline state;
10. serialize/save portable edit state;
11. reload/round-trip state;
12. accept external programmatic mutations suitable for a UV command adapter;
13. expose enough state for UV-owned transaction/undo-redo integration;
14. preview/decode a selected frame;
15. render/export real media;
16. express an exact range-replacement operation without destructive source mutation.

Evidence artifact digest: `sha256:dcac97a703bc1433467f81daa2ca75144e70561799fec14d026d409301ecc7ff`.

### MLT on Windows

Windows deployment was tested from a pinned relocatable KDE Kdenlive standalone package rather than assuming a developer-installed MLT runtime:

- package: `kdenlive-26.04.3_standalone.exe`;
- package SHA-256: `f2dc616c9c29cae261a4e4fc56293f5e88362b8024dc0b8f662c480c97e18df9`;
- discovered `melt.exe` runtime: `7.40.0`;
- bundled FFmpeg generated the source fixture;
- `melt.exe` opened media, consumed serialized MLT XML, accepted a programmatic range mutation, round-tripped the state and produced a real rendered output.

Evidence artifact digest: `sha256:e864d85c6fc346c27970dea8f38bdf506530acd7a91f8cf644efaa4c4f977644`.

This proves a relocatable Windows path. It does **not** require UV Studio to redistribute the entire Kdenlive application as its eventual packaging strategy; final packaging may bundle the minimum compliant MLT runtime after its redistribution notices/dependencies are audited.

### OpenCut Classic

The pinned source probe found:

- MIT license compatibility;
- implemented timeline/editor source rather than roadmap-only declarations;
- 142 timeline-related source files and 39 editor-related files in the inspected revision;
- implemented primitives including timeline store/state, tracks, creation/update pipeline, ruler/scale/zoom, drag behavior and snapping sources.

Evidence artifact digest: `sha256:9ddfdfefcd1b719a7c361a26766b71a5cfc9008d87d34b101eec1b21b08a9e46`.

OpenCut Classic is therefore a **selective donor**, not a new canonical application shell. UV Studio does not inherit its backend, authentication, storage or unrelated product architecture merely because individual editor components are reused.

### libopenshot

The independent `libopenshot` `0.3.2` probe passed ordinary timeline, preview and render operations but failed the full foundation gate:

- clean serialized Timeline JSON round-trip failed in the tested binding;
- the tested serialized clip did not expose a reliable ID for the expected `ApplyJsonDiff` external mutation seam.

Evidence artifact digest: `sha256:babfe823a7d2dda6d903d16cdd7559af3f8dd356ffe1598d0d283f23aa7583c9`.

Because external programmatic mutation and durable state round-trip are central to the shared GUI/script/AI/MCP command architecture, MLT is the stronger primary engine.

## Ownership and adapter boundaries

### UV Studio owns

- Project Store and portable project identity;
- source/asset/artifact/export path rules;
- canonical timeline/edit domain contracts exposed to product callers;
- the Command API, validation and transaction/undo-redo semantics;
- Capability Registry, MCP/native/local/cloud adapters and D-017 authorization;
- Brief → Plan → Candidate → Review → Accept state and invariants;
- accepted-edit identity and non-destructive project state;
- provenance and security policy;
- authoritative final export until another renderer is explicitly promoted by parity evidence.

### MLT owns behind the adapter

- reusable low-level timeline mechanics;
- playlist/tractor/track composition;
- clip positioning, trim/split/ripple mechanics where mapped by the adapter;
- media decode/preview mechanics where useful;
- serialization/render primitives used through bounded UV contracts.

MLT XML or in-memory state is an engine representation, not an alternate public mutation channel. Scripts, AI and MCP do not edit raw MLT project files to bypass UV validation.

### OpenCut Classic contributes selectively

UV Studio may adapt/copy suitable MIT-licensed editor components such as timeline interaction, ruler/zoom, track UX, playhead, dragging, snapping and related state/UI helpers. Every imported/adapted portion must retain the applicable attribution/license notice and remain behind a UV adapter so upstream implementation details do not become canonical project state.

## Acceptance/security boundary

Editor convenience does not weaken the Stage 4B acceptance gate. A user/AI action that proposes replacing existing media still flows through the current UV domain chain:

```text
range intent
  -> RangeContinuityBrief
  -> approved ReplacementPlan
  -> ReplacementCandidate
  -> ReplacementReview
  -> approved review acceptance
  -> AcceptedRangeEdit
  -> explicit final render/export
```

Timeline interaction may create/select/edit the intent and may display candidate/review state, but it cannot directly manufacture an accepted edit.

## Consequences for Stage 4C

Stage 4C implementation now starts from the selected reusable foundation rather than building a bespoke editor stack. The next slice must:

- establish the UV Command API/MLT adapter boundary;
- provide source-media registration/import and safe preview delivery;
- integrate/adapt reusable OpenCut Classic timeline/editor UX rather than duplicating it;
- map integer-microsecond UV range identity to editor positions without losing exact identity;
- route GUI, scripts, AI and MCP through the same commands;
- round-trip non-destructive accepted edits into visible timeline state;
- prove browser/editor preview behavior against authoritative UV render output before claiming parity.

Future transitions, keyframes, masks, audio editing, subtitles, waveform, tracking and similar general editor features should follow the same reuse-first rule: evaluate compatible mature components before custom implementation.
