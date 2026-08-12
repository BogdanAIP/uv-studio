# D-028 — Accepted targeted edits are canonical decisions, not rendered videos

Status: pending  
Date: 2026-08-12

## Decision

UV Studio stores accepted targeted video edits in a dedicated typed/versioned project document:

```text
timeline/range-edits.json
```

Each accepted decision contains only provider-neutral portable facts:

```text
edit_id
source_path
start_us
end_us
replacement_path
```

The requested interval uses immutable integer microseconds. Source and replacement references are canonical project-relative paths. Provider/model/runtime identity, machine paths, credentials, consent grants and render output paths are not part of canonical edit state.

Accepting or removing an edit is a local storage operation. It must not invoke FFmpeg/FFprobe, a provider, VLM, MCP tool or any paid/remote capability.

Materialization is separate and explicit through semantic capability:

```text
video.render_edits
  -> local_ffmpeg.video_render_edits
```

The render capability loads accepted decisions for one source, validates current media compatibility, and projects all non-overlapping accepted replacements in one deterministic FFmpeg filter-graph pass into a UV Studio-owned FFV1/FLAC artifact.

## State rules

- edit IDs are unique within the document;
- decisions are stored in deterministic `(source_path, start_us, end_us, edit_id)` order;
- overlapping accepted ranges on one source fail closed;
- touching boundaries are allowed;
- a source/replacement reference must resolve to an existing regular project file before a decision is persisted;
- media compatibility such as stream layout, resolution, duration and AV alignment is checked at explicit render time, not at acceptance time;
- read-modify-write acceptance/removal is serialized under the Project Store lock and persisted with the same atomic fsync + replace primitive used by canonical project JSON.

## Rationale

D-027 proved that D-021/D-022 FFmpeg mechanics are correct as a deterministic render layer, but whole-output FFV1 is unsuitable as canonical repeated-edit state. The measured eight-second compressed fixture expanded by 4.824x when a one-second replacement caused a complete FFV1 materialization on both Ubuntu and Windows.

The appropriate correction is therefore a state-layer change rather than weakening media correctness. Accepted edits should reference unchanged source media and replacement media until a preview/export/render actually needs a composed file.

Keeping compatibility checks at render time also prevents acceptance from becoming hidden heavy media analysis. A user may persist a replacement decision immediately; if the current replacement is technically incompatible, explicit render fails clearly without corrupting canonical state or producing a registered partial artifact.

## Capability boundary

`video.render_edits` is local + free + deterministic and is registered through the normal product Capability Registry. It therefore uses the same SelectionPolicy and capability-execution HTTP path as existing local media operations. No special render endpoint bypasses the capability boundary.

The package-level `LocalFFmpegAdapter` is now a compositional facade: existing range/probe/assemble behavior remains delegated to the proven range adapter, while edit-state rendering is an operation handler rather than another subclass in an adapter-on-adapter inheritance chain.

## Archive behavior

The portable project archive already contains the entire canonical project tree with per-file SHA-256 records. `timeline/range-edits.json` therefore round-trips with the project without provider-specific archive logic.

This slice proves export -> import -> fresh ProjectStore reopen yields the exact typed edit decisions. A malformed timeline document fails closed when opened through `RangeEditStateStore`.

Pre-commit archive semantic validation for every future typed project document remains a separate archive-hardening concern; the archive already validates paths, sizes, hashes, project identity and project schema before commit.

## Consequences

1. Multiple accepted short edits remain lightweight until explicit materialization.
2. The original source remains the stable media base instead of being replaced after every edit.
3. Stage 4B RangeContinuityBrief can attach bounded intelligence to exact accepted edit ranges without depending on a rendered-file-as-state model.
4. Stage 4C UI can distinguish `accepted decision` from `rendered preview/export` explicitly.
5. Existing D-021/D-022 mechanics remain available as deterministic correctness/render primitives.
6. Overlap semantics are intentionally conservative; richer track/layer conflict models require a later explicit decision rather than implicit overwrite behavior.

## Acceptance evidence required

Before this decision becomes accepted, the exact final PR #25 review head must pass all five required Ubuntu/Windows checks and demonstrate:

- unit tests for typed state, strict JSON, ordering, overlap, missing references and archive round-trip;
- API tests for accept/read/remove and fail-closed invalid requests;
- real media proof that accepting two edits creates no render artifact;
- one explicit `video.render_edits` call produces the expected two-edit content order in one render artifact;
- an existing but technically incompatible replacement can be accepted without media analysis and then fails clearly at explicit render;
- frontend lint, zero high-severity npm audit and production build remain green.
