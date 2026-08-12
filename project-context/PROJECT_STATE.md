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

## Stage 4B RangeContinuityBrief — review-ready

`stage-4-range-continuity-brief` adds a separate typed/versioned provider-neutral continuity/evidence document for a logical targeted edit intent. The brief is deliberately valid **before any replacement or accepted edit exists**.

The product order is now:

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
  -> explicit render/export
```

Portable brief target identity is exactly:

```text
edit_id + source_path + start_us + end_us
```

`replacement_path` is not part of continuity identity. If an accepted edit with the same `edit_id` exists later, its source/range must match; another replacement take for the same target may reuse the same brief.

The implemented boundary provides:

- creation and archive round-trip before replacement media exists;
- exactly one requested evidence item anchoring the target range;
- source-bound `before`, `requested` and `after` evidence with exact boundary adjacency;
- bounded 30-second evidence spans and bounded collection counts;
- project-relative evidence references with explicit current-file validation;
- mechanical facts separate from observations/inferences and no runtime/provider-binding fact keys;
- observations/inferences with explicit confidence and evidence references;
- constraints/review targets linked to known evidence only;
- structural readability/removal when files become stale plus explicit current-health validation;
- absent accepted edit as valid pre-replacement state;
- fail-closed conflict when a same-ID accepted edit points at another source/range;
- replacement-only take changes that do not invalidate target continuity knowledge;
- UV-owned CRUD API with no execution surface;
- no FFmpeg/VLM/MCP/provider side effect from baseline brief persistence.

D-029 is accepted.

Draft functional head `0c7053f842bf767e58b9d8564035cbfc20ce6f04` passed all five required checks in CI run #678 (`31589049828`) on Ubuntu and Windows, including unit/API/HTTP, existing real-media Stage 4A regressions, frontend lint, zero high-severity npm audit and production build.

The final state-only review head must repeat the same five required checks before merge.

## Expected following work

After PR #26 merges, continue Stage 4B with `stage-4-replacement-plan-gate`: consume the validated target brief, choose and approve the replacement method/constraints, and only then prepare deterministic or optional generative replacement media.

## Remaining cross-cutting gaps

- D-023 still needs a post-merge/idle lifecycle state and live diff-vs-write-scope enforcement;
- general free-form project JSON fields still need proportionate recursive portability hardening;
- Stage 4C still owns the complete timeline/preview/accept/export UI;
- broader real-media codec/device coverage remains incremental hardening.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
