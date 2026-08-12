# Project State

<!-- uv-active-slice: stage-4-range-continuity-brief -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Edit intelligence / RangeContinuityBrief

**Last verified `main` baseline:** `3dcb03ec33600ca361064afcbc6e9121ed800b11`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio has a secure product-owned runtime/dependency boundary, canonical portable projects, semantic capabilities with D-017 authorization, real cross-platform exact range mechanics, and non-destructive accepted replacement decisions under D-028.

Accepted replacements live as lightweight typed `timeline/range-edits.json` decisions and are materialized only by explicit `video.render_edits`; PR #25 proved video-only and audio multi-edit rendering on Ubuntu and Windows without returning to whole-video-render-as-state.

## Active Stage 4B slice

`stage-4-range-continuity-brief` adds a separate typed/versioned provider-neutral continuity/evidence document for a logical targeted edit intent. The brief is deliberately valid **before any replacement or accepted edit exists**.

The corrected product order is:

```text
exact targeted range intent
  -> bounded project evidence
  -> mechanical facts
  -> observations / inferences
  -> continuity constraints
  -> review targets
  -> replacement plan / preparation / generation
  -> review
  -> accepted replacement decision
```

Portable brief target identity is exactly:

```text
edit_id + source_path + start_us + end_us
```

`replacement_path` is not part of continuity identity. If an accepted edit with the same `edit_id` exists later, its source/range must match; another replacement take for the same target may reuse the same brief.

## Invariants for this slice

- a brief can be created and archived before replacement media exists;
- exactly one requested evidence item anchors the target range;
- `before`, `requested` and `after` evidence must reference the target source;
- before/after windows must touch the exact edit boundaries and each evidence span is bounded to 30 seconds;
- source-coordinate reference evidence is allowed only when the reference itself is the target source;
- evidence paths are project-relative regular files when saved/validated;
- mechanical facts are typed separately from observations/inferences and cannot encode provider/model/runtime binding keys;
- observations/inferences carry explicit confidence and known evidence references;
- constraints/review targets reference known evidence IDs only;
- collection sizes are bounded at the domain boundary;
- state remains structurally readable/removable if linked files later become stale, with explicit validation for current project health;
- an absent accepted edit is valid pre-replacement state; a conflicting accepted source/range makes the brief stale;
- archive/export/import/fresh reopen preserves the typed brief exactly without a replacement artifact;
- constructing a valid baseline brief performs no FFmpeg/VLM/provider execution.

## Expected following work

After this contract is proven, continue Stage 4B with `stage-4-replacement-plan-gate`: consume the validated target brief, choose and approve the replacement method/constraints, and only then prepare deterministic or optional generative replacement media.

## Remaining cross-cutting gaps

- D-023 still needs a post-merge/idle lifecycle state and live diff-vs-write-scope enforcement;
- general free-form project JSON fields still need proportionate recursive portability hardening;
- Stage 4C still owns the complete timeline/preview/accept/export UI;
- broader real-media codec/device coverage remains incremental hardening.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
