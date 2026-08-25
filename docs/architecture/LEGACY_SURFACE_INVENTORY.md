# Legacy Surface Inventory — Historical Audit Record

**Status:** HISTORICAL / MIGRATION EVIDENCE  
**Current authority:** `CURRENT_ARCHITECTURE.md` + D-064

This inventory was created during the Studio v2 migration to identify old VideoClaw, recipe, Stage-workspace and Product Orchestrator surfaces that could conflict with the supported UV-owned shell.

## Current classification rule

Legacy source is not current product authority merely because it remains in the tree or still compiles.

Typical compatibility/migration surfaces include:

- donor-era VideoClaw session/task/sandbox clients and routes;
- Recipe Registry and recipe-specific project identity;
- Product Orchestrator workflow projections;
- Stage 6/8 workspace composition;
- legacy execution-plan paths;
- frontend helpers whose required backend contracts are intentionally not mounted.

## Retirement rule

Do not delete these surfaces merely to make the tree look modern. First prove supported callers have moved to current Project/Production Direction/Studio command boundaries. Then delete or extract the useful primitive in a bounded cleanup.

The original file-by-file Stage 10 inventory remains available in Git history for dependency archaeology.
