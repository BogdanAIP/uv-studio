# Project State

<!-- uv-active-slice: stage-4-replacement-review-gate -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4B — Replacement review gate

**Last verified `main` baseline:** `919baba0a7497dd799a453ee2e5470b9531cf25e`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

The engineering path for a targeted existing-video replacement has a complete provider-neutral domain chain:

```text
targeted range intent
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> ReplacementCandidate (D-031)
  -> evidence-based ReplacementReview (D-032)
  -> AcceptedRangeEdit (D-028)
  -> explicit one-pass render/export
```

Stage 4A proves exact microsecond extraction/reinsertion and non-destructive accepted edit state on real media. Stage 4B adds bounded continuity evidence, approved method planning, candidate preparation and an independent review gate before acceptance.

## Active slice result

`stage-4-replacement-review-gate` closes the remaining domain safety boundary before Stage 4C UI work.

Implemented boundaries:

- only a current `full` ReplacementCandidate may receive a final replacement review;
- review state is project-owned under `reviews/`, portable and provider-neutral;
- review binds exact candidate metadata, target, approved-plan digest and SHA-256 of the candidate artifact bytes;
- review criteria map exactly to the current `RangeContinuityBrief.review_targets`;
- mechanical validation remains separate from observations/inferences and each target assessment is grounded in the exact candidate artifact;
- `approved`, `rejected` and `needs_revision` are explicit durable verdicts with mechanically consistent assessments;
- rejected/needs-revision and stale reviews remain inspectable history and never create accepted edit state;
- acceptance revalidates Candidate/Plan/Brief/review plus candidate bytes under the project lock and uses only the candidate's exact artifact path/range;
- the legacy caller-controlled HTTP create-edit route no longer bypasses Candidate + Review approval;
- a real prepared candidate is proven through review, acceptance and one-pass render on Ubuntu/Windows without mutating the original source.

Model-assisted review remains optional and fail-closed: generic `media.understand` execution still uses Capability Registry + D-017, but an external reviewer may receive the candidate file only through an offer with an explicit trusted project-file input binding. Current Qwen cloud understand bindings do not have that D-019 contract, so no arbitrary local path is leaked to them.

## Full-repository audit summary

The repository has a strong provider-neutral backend foundation and cross-platform CI, but user-outcome completion still lags engineering completion:

- Stage 0–3.5 foundations are established: upstream pin/provenance, Project Store/archive, recipes, semantic capabilities, fail-closed selection, one-shot external authorization, MCP/native adapters, runtime security and owned dependency gates;
- Stage 4A mechanical range editing and the complete Stage 4B decision chain are real-media tested on Ubuntu and Windows;
- the current Projects frontend exposes project metadata/readiness/archive operations but not the Stage 4 timeline/preview/review/accept workflow;
- Stage 4C is therefore the highest-value next product slice: turn the now-safe backend chain into one coherent targeted-edit user workflow.

## Remaining cross-cutting gaps

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- `project-context/DECISIONS.md` is stale after D-026 even though accepted D-027+ files exist; index maintenance belongs with the D-023 lifecycle/process hardening rather than this product gate;
- general free-form project JSON fields still need recursive portability hardening;
- canonical project references and D-028 accepted edits are path-based rather than globally content-addressed; D-032 pins reviewed candidate bytes at review/accept time, but broader post-accept external file mutation remains an integrity-hardening topic;
- the UV-owned compatibility `/api/stages` catalog still exposes transitional VideoClaw-oriented metadata and should be retired when no derived screen needs it;
- Stage 4C needs timeline/range selection, preview-in-context, visible Brief/Plan/Candidate/Review state, explicit acceptance/rejection and export, plus frontend/E2E coverage;
- broader real-world codec/device fixtures remain incremental hardening;
- later roadmap stages remain: dubbing/translation, optional linked-shot continuity, music-video mode, additional recipes, and Windows packaging/release hardening.
