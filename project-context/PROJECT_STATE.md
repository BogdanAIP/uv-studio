# Project State

<!-- uv-active-slice: stage-4-range-continuity-brief -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Edit intelligence / RangeContinuityBrief

**Last verified `main` baseline:** `3dcb03ec33600ca361064afcbc6e9121ed800b11`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio has a secure product-owned runtime/dependency boundary, canonical portable projects, semantic capabilities with D-017 authorization, real cross-platform exact range mechanics, and non-destructive accepted edit decisions under D-028.

Accepted edits now live as lightweight typed `timeline/range-edits.json` decisions and are materialized only by explicit `video.render_edits`; PR #25 proved video-only and audio multi-edit rendering on Ubuntu and Windows without returning to whole-video-render-as-state.

## Active Stage 4B slice

`stage-4-range-continuity-brief` adds a separate typed/versioned provider-neutral continuity/evidence document attached to an exact accepted edit identity.

The intended structure separates:

```text
exact accepted edit identity
  -> bounded project evidence
  -> mechanical facts
  -> observations / inferences
  -> continuity constraints
  -> review targets
```

The brief must remain useful without a VLM/provider call. Future model-assisted enrichment may populate observations/inferences only through existing capability/D-017 boundaries; provider/model/runtime identity never becomes canonical brief state.

## Invariants for this slice

- exact `edit_id + source_path + start_us + end_us` must match an accepted D-028 edit;
- evidence paths are project-relative regular files;
- source-coordinate evidence windows are bounded and role-consistent around the target edit;
- mechanical facts are typed separately from observations/inferences;
- observations/inferences carry explicit confidence and evidence references;
- constraints/review targets reference known evidence IDs only;
- state remains structurally readable/removable if linked media/edit state later becomes stale, with explicit validation for current project health;
- archive/export/import/fresh reopen preserves the typed brief exactly;
- constructing a valid baseline brief performs no FFmpeg/VLM/provider execution.

## Expected following work

After this contract is proven, continue Stage 4B with `stage-4-replacement-plan-gate`: consume exact edit decisions + continuity briefs to define the approved replacement method/constraints before deterministic or optional generative preparation.

## Remaining cross-cutting gaps

- D-023 still needs a post-merge/idle lifecycle state and live diff-vs-write-scope enforcement;
- general free-form project JSON fields still need proportionate recursive portability hardening;
- Stage 4C still owns the complete timeline/preview/accept/export UI;
- broader real-media codec/device coverage remains incremental hardening.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
