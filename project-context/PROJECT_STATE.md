# Project State

<!-- uv-active-slice: stage-4-editor-foundation-spike -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4C foundation selection complete; PR #30 still active

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

The targeted existing-video backend path is complete through Stage 4B:

```text
targeted range intent
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> ReplacementCandidate (D-031)
  -> evidence-based ReplacementReview (D-032)
  -> AcceptedRangeEdit (D-028)
  -> explicit one-pass render/export
```

PR #29 merged the independent review gate and removed caller-controlled direct edit acceptance. Exact range mechanics and the Stage 4B decision chain are covered by real-media tests on Ubuntu and Windows.

## Stage 4C foundation selected

D-033 is accepted. Stage 4C will not build another general-purpose video editor stack from scratch.

The selected composition is:

```text
OpenCut Classic-derived editor UX
              |
GUI --------- |
Scripts ------+--> UV Studio Command API --> domain validation/transaction --> MLT adapter
AI -----------|                                         |
MCP ----------|                                         +--> derived preview/edit representation
                                                        |
                                                        +--> UV Project Store remains canonical

approved replacement workflow --> D-032 review --> D-028 AcceptedRangeEdit --> UV FFmpeg final render
```

### Editing engine — MLT

MLT won the executable engine comparison.

- Ubuntu MLT Python binding `7.22.0` passed all 16 required engine capabilities using real generated media: source open, timeline creation/query, multitrack, add/move/trim/split/ripple, serialization, round-trip, external mutation, undo/redo integration surface, preview frame, render/export and exact replacement expression.
- A separate Windows deployment probe extracted a SHA-256-pinned KDE Kdenlive standalone package, found relocatable `melt.exe` `7.40.0` plus bundled FFmpeg, round-tripped and programmatically mutated serialized MLT XML, then rendered real output successfully.
- The Windows result proves a no-system-install runtime path. Eventual packaging may bundle a smaller compliant MLT runtime rather than the whole Kdenlive application.

`libopenshot` remains a fallback/component source, but is not the primary engine because its tested `0.3.2` binding failed the required clean Timeline JSON round-trip and reliable external serialized-mutation seam.

### Editor UX donor — OpenCut Classic

OpenCut Classic is pinned at `cf5e79e919144200294fb9fed22a222592a0aeea` as an MIT source donor. The source probe confirmed implemented timeline/editor primitives including timeline store/state, tracks, creation/update helpers, ruler/scale/zoom, dragging and snapping. Roadmap-only API/MCP/headless promises are not counted as implemented capability.

UV Studio will selectively adapt useful editor code. OpenCut backend/auth/storage architecture does not become UV Studio architecture by default.

### Canonical ownership

UV Studio still owns:

- Project Store and portable project identity;
- source/asset/artifact/export path rules;
- product Command API and transaction/undo-redo semantics;
- Capability Registry and execution authorization;
- Brief -> Plan -> Candidate -> Review -> Accept invariants;
- accepted non-destructive edit state;
- provenance/security policy.

Raw MLT XML or OpenCut state is never a public bypass around these boundaries.

The existing UV FFmpeg one-pass renderer remains authoritative final export initially. MLT rendering is proven, but will not silently replace canonical render truth until preview/render parity is tested.

## Evidence state

`editor-foundation-spike` run `31608137802` at head `bc0433e0b2781ffca805f8e6644b65cf9a801764` completed all four spike jobs successfully and uploaded preserved evidence for:

- MLT Linux;
- MLT Windows relocatable deployment;
- libopenshot;
- OpenCut Classic.

The hidden `.spike-output` artifact issue was fixed with `include-hidden-files: true`.

The ordinary Windows app-baseline also exposed that Chocolatey/BtbN moving package sources are unsuitable as durable CI pins. The active branch now provisions Windows FFmpeg from the same exact SHA-256-pinned KDE standalone package already exercised by the MLT Windows probe. Exact-head ordinary CI must be green before PR #30 leaves draft/review and merges.

## Next product gap

After PR #30 merges, Stage 4C continues as `stage-4-range-edit-user-workflow` using the selected foundation rather than reopening the editor-engine decision.

The complete user-facing path still needs:

- project source registration/import;
- safe Range-capable browser media delivery;
- reusable editor workspace/player/timeline;
- exact timeline range selection mapped to UV integer microseconds;
- one UV Command API callable by GUI/scripts/AI/MCP;
- visible Brief/Plan/Candidate/Review state in the editor;
- candidate-in-context preview and approve/reject/revise;
- accepted non-destructive edits visible on the timeline;
- multiple edits;
- explicit preview/render/export;
- browser E2E and preview-vs-authoritative-render consistency tests.

## Cross-cutting debt retained outside this spike

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- the aggregate decision index is stale after D-026 and needs lifecycle/process maintenance;
- free-form project JSON fields need recursive portability hardening;
- broader accepted-file/content-addressing integrity remains future hardening;
- the compatibility `/api/stages` catalog should be retired when no UV-owned screen needs it;
- broader codec/device fixtures remain incremental hardening.
