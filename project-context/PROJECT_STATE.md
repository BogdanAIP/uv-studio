# Project State

<!-- uv-active-slice: stage-4-replacement-review-gate -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Replacement review gate

**Last verified `main` baseline:** `919baba0a7497dd799a453ee2e5470b9531cf25e`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

The engineering path for a targeted existing-video replacement now reaches a project-owned candidate without requiring whole-video regeneration:

```text
targeted range intent
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> ReplacementCandidate (D-031)
  -> evidence-based review
  -> AcceptedRangeEdit (D-028)
  -> explicit one-pass render/export
```

Stage 4A already proves exact microsecond extraction/reinsertion and non-destructive accepted edit state on real media. Stage 4B now has provider-neutral Brief, Plan and Candidate contracts, including sample-first optional generation and trusted project-owned MCP outputs.

## Active slice

`stage-4-replacement-review-gate` closes the remaining domain safety boundary before Stage 4C UI work.

Required behavior:

- only a current `full` ReplacementCandidate may receive a final replacement review;
- review state is project-owned under `reviews/`, portable and provider-neutral;
- review binds the exact candidate, target and approved-plan digest rather than re-resolving caller-supplied paths;
- review criteria map exactly to the current `RangeContinuityBrief.review_targets`;
- mechanical validation remains separate from human/model observations and inferences;
- observations cite bounded current Brief evidence and/or the exact candidate artifact;
- `approved`, `rejected` and `needs_revision` are explicit durable verdicts;
- an approved verdict requires every required review target to pass;
- rejected/needs-revision reviews remain inspectable history and never create accepted edit state;
- acceptance revalidates the current Candidate/Plan/Brief/review binding under one project lock and uses the candidate's exact artifact path/range;
- the legacy caller-controlled HTTP create-edit route must not bypass Candidate + Review approval;
- optional model-assisted analysis continues through the existing semantic Capability Registry and D-017 authorization rather than being embedded in review state; manual/local evidence entry remains first-class.

## Full-repository audit summary

The repository has a strong provider-neutral backend foundation and cross-platform CI, but user-outcome completion lags engineering completion:

- Stage 0–3.5 foundations are established: upstream pin/provenance, Project Store/archive, recipes, semantic capabilities, fail-closed selection, one-shot external authorization, MCP/native adapters, runtime security and owned dependency gates;
- Stage 4A mechanical range editing is real-media tested on Ubuntu and Windows;
- Stage 4B is one review gate away from a complete domain chain;
- the current Projects frontend exposes project metadata/readiness/archive operations but not the Stage 4 timeline/preview/review/accept workflow;
- Stage 4C therefore remains the highest-value user-facing continuation after this review gate.

## Remaining cross-cutting gaps

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- general free-form project JSON fields still need recursive portability hardening;
- the UV-owned compatibility `/api/stages` catalog still exposes transitional VideoClaw-oriented metadata and should be retired when no derived screen needs it;
- Stage 4C needs timeline/range selection, preview-in-context, visible Brief/Plan/Candidate/Review state, explicit acceptance/rejection and export, plus frontend/E2E coverage;
- broader real-world codec/device fixtures remain incremental hardening;
- later roadmap stages remain: dubbing/translation, optional linked-shot continuity, music-video mode, additional recipes, and Windows packaging/release hardening.
