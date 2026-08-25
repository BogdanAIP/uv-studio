# Recipe Registry — Compatibility Record

**Status:** COMPATIBILITY — not the v2 product taxonomy  
**Current authority:** `CURRENT_ARCHITECTURE.md` + D-064

The Recipe Registry was the earlier user-facing menu/workflow contract. Historical projects and compatibility APIs may still carry `recipe_id`, and schema v1 still requires neutral recipe metadata.

That does not make recipes the identity of new Studio projects.

## Current rule

New Studio projects use a `ProductionDirection` such as `micro_drama`, `commercial`, `music_video`, `narrated_video`, `dub_battle` or `free_project`. Direction identity is separate from RecipeDefinition execution metadata.

Do not add a new `RecipeDefinition` to ship a product feature or direction.

## Compatibility that remains

- legacy projects may still have meaningful historical `recipe_id` values;
- new Studio projects currently retain neutral `recipe_id=studio_v2` because schema v1 requires it;
- old recipe APIs/registry entries remain until dependency proof permits retirement;
- useful recipe-era media/domain implementations may be reused as Studio tools or direction services.

The original recipe catalog and project->recipe contract are preserved in Git history for migration archaeology.
