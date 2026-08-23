# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-repository-hygiene -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **draft** on `product-recovery-repository-hygiene` in PR #49, branched from idle `main` after Music orchestration PR #48 merged as `55b87839f79fa639906c409c9e763d650eaf7c03` and lifecycle closure commit `dc634f5b43eb89b3cbd5e5fa40f507a0f877ca76` returned the repository to idle.

This slice is intentionally narrower than the next product journey. Its purpose is to reconcile repository truth and semantic contracts before further orchestration work, not to redesign Product Orchestrator or resume Stage 9 packaging.

## Completed Product Recovery journeys

The permanent Product Orchestrator has authoritative Class A/B journeys for:

- `photo_to_video -> photo_composition`;
- `visualizer -> audio_visualizer`;
- `free_project -> targeted_edit`;
- `dubbing -> dubbing`;
- `music_video -> music_video`.

Project Store/domain stores remain canonical; Product Orchestrator is current-state projection plus allowed semantic actions.

## Hygiene scope

The audit-backed targets are:

1. synchronize Product Truth Matrix, Product Orchestrator architecture docs and repository backlog/state text with completed Dubbing and Music recovery;
2. remove obsolete frontend routes `/pipelines/standard`, `/pipelines/action-transfer`, `/pipelines/digital-human` and `/sandbox` so old VideoClaw surfaces are no longer addressable as current product routes;
3. fix `accept_dubbing_review` so optional `accepted_id` survives the Product Orchestrator request-validation path instead of being narrowed by the wrong request model;
4. remove dead/non-operative Music projector code only where behavior remains unchanged;
5. assess strict recursive JSON non-finite-number rejection and per-project corruption quarantine;
6. keep missing `main` branch protection recorded as an external repository-setting P0 because the available repository connector does not expose a branch-protection mutation.

## Project Store hardening assessment

The strict-JSON/corruption item does **not** fit safely inside PR #49 and is explicitly split into `project-store-portable-json-hardening` before Narrated recovery.

The current canonical persistence boundary has three coupled behaviors that must be changed and tested together:

- `ProjectDocument.settings`, `extensions` and `ProjectReference.metadata` only require a top-level mapping; nested values are not recursively validated as portable JSON;
- `ProjectStore._atomic_write_json()` uses Python `json.dumps()` without `allow_nan=False`, so `NaN`, `Infinity` and `-Infinity` can be serialized even though they are not portable JSON values;
- project listing is not corruption-isolated: a malformed/invalid project can propagate a store error and prevent healthy projects from being listed.

Because this touches canonical model validation, save/update/import/reopen semantics and project-list recovery behavior, it needs a bounded Project Store contract slice with dedicated tests rather than an opportunistic change in repository hygiene.

## Verification target

Before Review, the exact Draft head must prove:

- architecture/backlog text matches as-built recovered routes;
- obsolete frontend product routes no longer expose legacy workspaces;
- Dubbing `accepted_id` request typing is coherent and covered by API tests;
- Music cleanup has no behavioral regression;
- the Project Store hardening split is explicit and actionable;
- all five permanent Ubuntu/Windows CI checks pass.

This slice does not claim Class C cold-start usability, installed Windows human acceptance or release readiness.

## Next authorized slice

`product-recovery-repository-hygiene` is active in PR #49. `project-context/NEXT_TASK.md` remains this slice's entry/exit contract until merge.

After PR #49 merges and lifecycle returns to idle, the next authorized slice is `project-store-portable-json-hardening`. Narrated orchestration follows only after that persistence hardening slice is reviewed, merged and closed to idle.
