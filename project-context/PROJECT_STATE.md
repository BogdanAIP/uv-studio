# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-recipe-workspace-reconciliation -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Recipe/workspace reconciliation is active in **Draft** on `fix/product-recovery-recipe-workspace-reconciliation` as PR #56, based on idle `main` `2c53b50c847986c9a9486ed319d245e3d1944f21` after Commercial Product PR #55.

The slice closes the remaining Product Truth mismatch between the provider-neutral recipe registry, the set of recipes advertised for new project creation, Product Orchestrator projections and visible project workspaces.

## Implemented Draft boundary

- the full Recipe Registry remains durable compatibility/product vocabulary;
- the creation catalog now advertises only recipes with a current authoritative Product Orchestrator journey;
- Action Transfer, Digital Human and Performance/lip-sync recipe metadata remains addressable for preserved/imported projects but is not advertised for new creation;
- public create/switch requests fail closed for preserved-only recipes, while archive import remains recovery-permissive;
- visible project workspaces are now mounted only from `workflow.relevant_workspaces`;
- the old generic ProjectEditor + Sequence Continuity + Dubbing fallback is removed;
- the direct `performance_lip_sync` page bypass is removed until that journey is separately recovered;
- `free_project` remains aligned with Targeted Edit ownership and is not broadened into a second generic editor.

## Verification status

Focused API and browser regression proof has been added for creation catalog truth, direct creation rejection and preserved unsupported projects without foreign workspace leakage. Exact Draft-head CI is pending; all five permanent jobs on Ubuntu/Windows are required before transition to Review.

Any older Stage 8 regression that assumes `performance_lip_sync` is still a directly creatable Product-Orchestrator-bypassing surface must be updated to the new fail-closed product boundary rather than weakening creation truth.

Stage 9 remains blocked until Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

If exact Draft and Review evidence closes the remaining P0 Product Truth mismatch, the next slice is `product-usability-class-c-cold-start` for user-equivalent clean-state evidence. Installed Windows human acceptance remains a separate required gate before Stage 9.
