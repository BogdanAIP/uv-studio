# Next Task

<!-- uv-next-slice: product-recovery-repository-hygiene -->

## Goal

Close repository-truth and semantic-contract debt exposed by the post-recovery audit before beginning `narrated_video` orchestration. Keep Product Orchestrator architecture consistent with the completed Photo, Visualizer, Targeted Edit, Dubbing and Music journeys without broad platform rewrites.

## Required direction

- synchronize `PROJECT_STATE.md`, Product Truth Matrix, Product Orchestrator architecture docs and backlog text so they describe Dubbing and Music as completed recovered journeys;
- remove or redirect legacy frontend routes under `/pipelines/standard`, `/pipelines/action-transfer`, `/pipelines/digital-human` and `/sandbox` so obsolete VideoClaw workspaces are not presented as current product routes;
- fix the Dubbing `accept_dubbing_review` semantic action contract so optional `accepted_id` is preserved end-to-end instead of being narrowed to an incompatible request model;
- remove dead/non-operative Music projector code only where behavior is provably unchanged;
- assess strict recursive JSON rejection for `NaN`/`Infinity` and per-project corruption quarantine, implementing only the portion that fits a reviewable narrow slice or explicitly splitting the remainder into the following hardening slice;
- record missing `main` branch protection as an external repository-setting P0; do not pretend code changes can enable it through an unavailable repository-setting API;
- preserve all five recovered Product Orchestrator journeys and all permanent CI checks.

## Completion proof

The slice is complete when repository architecture/product-truth docs agree with the actual recovered routes, obsolete frontend routes no longer expose legacy product surfaces, the Dubbing acceptance request contract is coherent and tested, Music projector cleanup has no behavior regression, and all exact-head permanent Ubuntu/Windows checks pass.

Any strict-JSON/corruption-quarantine work not safely completed in this slice must leave an explicit next hardening contract rather than being silently deferred.

## Entry gate

Begin only from idle `main` after PR #48 Music orchestration is merged and lifecycle closure records Music as authoritative through Product Orchestrator. Do not begin Narrated or Stage 9 packaging until this hygiene slice is reviewed and merged.
