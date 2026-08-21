# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-targeted-edit-orchestration -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-targeted-edit-orchestration` is the active Draft slice on branch `fix/product-recovery-targeted-edit-orchestration`, created from explicit idle `main` after PR #45.

The slice will migrate the existing targeted existing-video editing journey into Product Orchestrator without replacing its durable domain model. It must preserve D-028 non-destructive accepted edits, D-032 evidence-based Review/Accept and D-033 semantic editor ownership.

PR #45 completed Visualizer orchestration and authoritative deterministic workspace routing. Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Current product truth

Photo -> Video and Visualizer are the two deterministic Product Orchestrator reference journeys. Their readiness comes from verified project-owned media plus current executable runtime availability, their relevant workspaces are authoritative, and their semantic actions enforce the fresh projected input contract before execution.

Non-migrated recipes remain fail-closed as `partial` at the Product Orchestrator boundary.

## Targeted edit — existing foundation to preserve

The current targeted-edit chain is real and already spans current UV-owned domains:

```text
project-owned source video
 -> exact range selection + requested change
 -> EditorCommandService / RangeContinuityBrief
 -> ReplacementPlan
 -> ReplacementCandidate
 -> evidence-based ReplacementReview
 -> explicit Accept
 -> AcceptedRangeEdit
 -> bounded render/export
```

The problem is product presentation and orchestration, not absence of backend implementation. The frontend still exposes internal `Brief -> Plan -> Candidate -> Review -> Accept` vocabulary directly and the generic project page still decides editor exposure outside Product Orchestrator for non-migrated recipes.

## Intended slice direction

- project truthful targeted-edit readiness from canonical source/edit/replacement/review state;
- declare a dedicated targeted-edit workspace through `relevant_workspaces` rather than mounting the editor generically for unrelated recipes;
- expose outcome-oriented next actions such as add source, choose fragment/describe change, prepare replacement, review, accept and export;
- keep durable Brief/Plan/Candidate/Review/Accept objects underneath where they protect correctness/provenance;
- allow semantic state/domain actions to delegate to existing UV services/stores without forcing every action through Capability Registry;
- evolve the Product Orchestrator action contract only as needed so domain/state actions are first-class and do not require a fake capability ID;
- enforce the fresh projected input/action contract at the Orchestrator boundary before any mutation or provider dispatch;
- do not create orchestration persistence, a second editor store, raw MLT mutation access or new generic NLE primitives.

`free_project` is the leading candidate for the first targeted-edit Product Orchestrator workspace because its accepted recipe definition is a neutral project that connects only needed existing primitives and explicitly includes editing. This mapping must still be confirmed against the live `/projects` UX and current tests before implementation is finalized.

## Verification policy

The slice must add focused API/browser evidence for blocked/source-ready/range-selected/review/accepted/exportable product states and prove that no Product Orchestrator action bypasses the existing domain trust boundaries.

Existing Class B informed-regression tests remain useful but do not replace later Class C cold-start UI-only evidence or installed Windows acceptance.

## Next handoff

After this slice is reviewed, merged and closed to `idle`, continue with `product-recovery-dubbing-orchestration`: project the existing dubbing domains into truthful prerequisites and outcome-oriented next actions while preserving transcript/translation/speech/alignment/review/render authority boundaries.
