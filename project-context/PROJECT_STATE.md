# Project State

<!-- uv-active-slice: stage-4-editor-foundation-spike -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4C foundation spike

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

## Active foundation question

Stage 4C must not begin by inventing another video editor. The active spike determines which mature open-source components can provide editor UX and/or timeline/render mechanics while UV Studio keeps its Project Store, safety boundaries and AI workflow.

The required interaction model is REAPER-like in one important architectural sense: normal GUI actions, user scripts, AI actions and MCP automation must operate through one programmatic UV Studio command layer and therefore produce the same validated project mutations and undo/redo semantics.

Current candidates under executable review are:

- `libopenshot` as a scriptable LGPL editing/render engine, explicitly separate from the GPL OpenShot Qt application;
- MLT as an LGPL scriptable editing/render engine used by established editors;
- OpenCut as a potential MIT-compatible editor UX/component donor, with implemented capability separated from roadmap claims.

The spike permits a hybrid choice (for example an MIT-compatible UI donor plus an LGPL engine adapter) when that minimizes custom code and keeps licensing/upgrade boundaries clear.

## Remaining product gap

Stage 4C still needs a complete user-facing workflow: source-media registration/import, safe preview, timeline/range interaction, visible Brief/Plan/Candidate/Review state, explicit accept/reject/revision, non-destructive timeline state, and render/export without manual API calls.

The foundation spike is intentionally before that implementation so timeline, waveform, player, scripting and engine primitives are reused instead of rewritten.

## Cross-cutting debt retained outside this spike

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- the aggregate decision index is stale after D-026 and needs lifecycle/process maintenance;
- free-form project JSON fields need recursive portability hardening;
- broader accepted-file/content-addressing integrity remains future hardening;
- the compatibility `/api/stages` catalog should be retired when no UV-owned screen needs it;
- broader codec/device fixtures remain incremental hardening.
