# Project State

<!-- uv-active-slice: stage-4-range-edit-user-workflow -->

**Updated:** 2026-08-13

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4C targeted range-edit user workflow — PR #31 review

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

The targeted existing-video workflow is implemented end to end through the product UI:

```text
project-owned source import
  -> browser preview + exact integer-microsecond timeline selection
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> ReplacementCandidate (D-031)
  -> evidence-based ReplacementReview (D-032)
  -> AcceptedRangeEdit (D-028)
  -> explicit authoritative FFmpeg render
  -> deterministic H.264/AAC browser-preview projection from that master
```

The UI does not create a second editing model. GUI actions use UV-owned command/workflow contracts, Project Store/domain state remains canonical, and AI/scripts/MCP are required to share the same boundary rather than mutating raw MLT or project JSON.

## Stage 4C reusable foundation

D-033 is accepted and PR #30 is merged. Stage 4C uses:

```text
OpenCut Classic-derived editor UX
              |
GUI --------- |
Scripts ------+--> UV Studio Command API --> domain validation/transaction --> MLT adapter
AI -----------|                                         |
MCP ----------|                                         +--> derived timeline/preview representation
                                                        |
                                                        +--> UV Project Store remains canonical

approved replacement workflow --> D-032 review --> D-028 AcceptedRangeEdit --> UV FFmpeg final render
```

- MLT is the selected editing/timeline engine behind a UV-owned adapter.
- OpenCut Classic commit `cf5e79e919144200294fb9fed22a222592a0aeea` remains the selected MIT editor-UX/component donor.
- UV Project Store/domain state is the single canonical project state.
- raw MLT XML is ephemeral engine input and is not exposed by `/editor/state`; absolute host paths do not cross that API boundary.
- the existing UV FFmpeg one-pass renderer remains authoritative final export; browser MP4 preview is encoded from the authoritative master rather than repeating the edit from source media.

## PR #31 implementation outcome

The normal-user Stage 4C path now includes:

- project-owned streaming source import with media inspection, portable metadata and cleanup on failure;
- ID-based source/artifact HTTP media delivery with byte Range support and no arbitrary host-path API;
- player, reusable timeline, zoom, playhead and exact microsecond range selection;
- AI/change-request panel bound to canonical `select_range` command state;
- visible Brief -> Plan -> Candidate -> Review -> Accept workflow with D-032 approval still mandatory;
- accepted non-destructive edits shown back on the timeline, including multiple edits;
- explicit one-pass authoritative render/export rather than automatic heavy render after acceptance;
- render revision detection so an older master is marked stale when Accepted edits change;
- deterministic `video.preview_artifact` H.264/AAC MP4 projection from the registered authoritative master for browser playback;
- real MLT adapter derived from canonical accepted edits, not a second project file format;
- typed public MLT projection summary while raw XML and resolved machine paths remain adapter-private.

## MLT parity evidence

The Stage 4C integration test deliberately compares the derived MLT timeline against the authoritative FFmpeg render on real encoded media.

During PR #31 this test exposed two real adapter defects that the earlier foundation spike could not detect because the spike only proved a non-empty render:

1. `avformat-novalidate` began with a tiny provisional producer length, causing requested ranges to be clamped. The adapter now provides explicit frame length from already validated UV metadata.
2. replacement producers were serialized after playlist entries that referenced them. MLT resolves producer IDs sequentially while parsing XML, so the replacement entries disappeared and a 6-second composition became 4 seconds. All producers are now declared before the playlist.

After both fixes, the real-media parity suite passes on Ubuntu and Windows. The strict parity fixture uses FFV1/MKV source and replacement media, verifies full duration and samples the expected source/replacement colors at five timeline positions. The authoritative export remains a separate UV FFmpeg path.

## Review gate

PR #31 is ready for review only after its code head proves all required checks on the exact commit. The final review-context commit must then receive the same five required green checks before merge:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

## Next product slice

After PR #31 merges, continue with `stage-5-dubbing-translation` using the same Project Store, Command API, MLT adapter, semantic Capability Registry and explicit review/render boundaries. Do not introduce another timeline/project model for dubbing.

## Cross-cutting debt retained outside this slice

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- the aggregate decision index needs lifecycle/process maintenance;
- broader free-form project JSON fields still need recursive portability hardening outside newly typed boundaries;
- broader accepted-file/content-addressing integrity remains future hardening;
- the compatibility `/api/stages` catalog should be retired when no UV-owned screen needs it;
- broader codec/device fixtures remain incremental hardening.
