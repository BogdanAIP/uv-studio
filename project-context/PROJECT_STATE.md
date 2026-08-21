# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-targeted-edit-orchestration -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-targeted-edit-orchestration` remains the active Draft slice on branch `fix/product-recovery-targeted-edit-orchestration`, based on explicit idle `main` after PR #45.

Implementation is complete enough for final self-review and exact-head CI. The slice has migrated targeted existing-video editing into Product Orchestrator while preserving D-028 non-destructive accepted edits, D-032 evidence-based Review/Accept and D-033 semantic editor ownership.

The lifecycle must not move to `review` until the final documentation/context head has passed every required check and the complete PR diff has been reviewed again. PR #45 remains the last completed slice until #46 is actually merged.

Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Current product truth

Three journeys now have authoritative Product Orchestrator workspace projection:

- `photo_to_video` -> `photo_composition`;
- `visualizer` -> `audio_visualizer`;
- `free_project` -> `targeted_edit`.

Photo -> Video and Visualizer remain deterministic local/free reference journeys. Targeted edit is the first migrated journey whose semantic next actions span durable domain decisions as well as a capability-backed final media operation.

Non-migrated recipes remain fail-closed as `partial`/unavailable at the Product Orchestrator boundary. Their old UV-owned domain panels may remain temporarily reachable as compatibility surfaces, but they are not alternate workflow authority.

## Targeted edit — implemented orchestration

The migrated product chain is:

```text
project-owned source video
 -> ProductWorkflowState targeted_edit workspace
 -> select_target_range
 -> EditorCommandService / RangeContinuityBrief
 -> prepare_replacement
 -> durable ReplacementPlan + full ReplacementCandidate
 -> review_replacement
 -> evidence-based ReplacementReview
 -> accept_replacement
 -> AcceptedRangeEdit
 -> render_accepted_edits
 -> video.render_edits / local FFmpeg
 -> project video artifact
```

The Product Orchestrator owns no persistent workflow state. `Project Store` and the existing domain stores remain canonical.

The UI no longer requires a user-visible technical Plan step. `prepare_replacement` combines Plan approval and Candidate preparation as one semantic operation while retaining the Plan object underneath for correctness/provenance. Previous-Plan capture and installation of the action Plan occur under one short Project Store lock; the expensive media copy remains outside that lock. If Candidate preparation fails, partial artifact registration is removed and the exact previous Plan is restored only when the current valid Plan is still exactly the one installed by this action. A concurrent Plan or Brief mutation is never overwritten by rollback.

Approved Reviews already represented in Accepted state are not re-advertised as executable Accept actions. A previous render remains historical evidence but is `current_outcome` only when its source and exact `edit_ids` still match the current Accepted state.

Product-level readiness follows the current stage rather than merely the presence of an input video. Missing source, required replacement material or required render runtime produces truthful `setup_required`/`unavailable` state. When the exact current Accepted revision already has a matching master, that artifact is reported as the current outcome instead of presenting the project as if another render were still required.

## Workspace isolation and migration compatibility

`free_project` is now authoritative targeted-edit routing. Its normal project page does not also mount:

- the historical Stage 8 Free workspace;
- Dubbing;
- Sequence Continuity.

The compatibility path for old ProjectEditor surfaces is deliberately narrow. Only established one-to-one actions such as range selection, Review, Accept and final render may fall back after a recipe-level 404, and only after a fresh workflow projection explicitly reports `workflow_not_migrated` and contains no `targeted_edit` workspace. A migrated `free_project` cannot hide an Orchestrator failure behind legacy compatibility.

Composite replacement preparation is intentionally **not** part of that fallback. On non-migrated pages the historical Plan approval and Candidate preparation remain two explicit steps until that recipe receives its own Product Orchestrator migration. This avoids pretending multiple old mutations are one atomic semantic action.

This compatibility exists to avoid breaking still-unmigrated domain regressions while Product Truth Recovery proceeds. It is not a second architecture.

## Verification implemented in this slice

Focused API/domain evidence covers:

- empty/source-ready targeted workflow projection;
- verified source identity and tamper fail-closed behavior;
- stage-accurate readiness for missing replacement material, missing render runtime and an already-current master;
- exact allowed edit/replacement pairs;
- semantic range selection;
- combined replacement Plan + Candidate preparation;
- evidence-based Review and explicit Accept;
- capability-backed final render input bounding;
- consumed approved Reviews not being exposed for duplicate Accept;
- stale renders not becoming `current_outcome` after Accepted state changes;
- exact restoration of a real previous Plan when Candidate preparation fails without a concurrent mutation;
- preservation of a concurrent Plan change when Candidate preparation fails, rather than rolling it back.

Browser evidence now separates product responsibilities:

- dedicated `free_project` targeted-edit journey performs import -> range -> replacement -> review -> accept -> render through the real UI and Product Orchestrator semantic actions;
- that targeted journey asserts Dubbing/Continuity/old Free workspace are absent;
- Story/Commercial retain their existing Stage 8 preparation round-trip regression;
- Dubbing + Sequence Continuity retain a separate temporary compatibility regression on non-migrated `general_video` instead of being forced into the targeted-edit project.

These remain Class B informed-regression tests. They do not replace future Class C cold-start product evidence or installed Windows human acceptance.

## Architecture invariants preserved

- no second orchestration persistence or competing Project Store authority;
- no direct raw project/timeline file mutation from Product Orchestrator;
- no remounting of historical VideoClaw backend routes;
- D-017 Capability Registry/authorization boundaries remain in force for capability-backed operations;
- domain actions may have `capability_id = null` only when they delegate to bounded UV-owned semantic/domain services;
- accepted edit state remains non-destructive and evidence-based Review remains mandatory before acceptance;
- no generic NLE expansion or new editor ownership decision is introduced by this slice.

## Remaining recovery work

Targeted edit is now `working_orchestrated` at Class A/B evidence level, but it is not a release-ready claim. Remaining product-wide gaps include readiness-blind recipe creation, non-migrated workspace leakage, missing/partial General/Narrated/Music journeys, Dubbing setup/orchestration, later Class C cold-start journeys and installed-app acceptance.

The next planned slice is `product-recovery-dubbing-orchestration`.

## Next handoff

After this PR passes final exact-head CI, receives final self-review with zero unresolved blocking findings, transitions to `review`, merges, and closes lifecycle to `idle`, continue with `product-recovery-dubbing-orchestration`: project the existing dubbing domains into truthful prerequisites and outcome-oriented next actions while preserving transcript/translation/prepared-speech/alignment/review/render authority boundaries.
