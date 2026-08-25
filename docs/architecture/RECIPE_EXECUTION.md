# Recipe Execution — Compatibility Record

**Status:** COMPATIBILITY — not the current application command model  
**Current authority:** `CURRENT_ARCHITECTURE.md` + D-064

Earlier UV Studio exposed recipe execution plans such as `/api/uv/recipes/{recipe_id}/execution-plan` to bridge RecipeDefinition metadata to capability-backed execution.

That seam remains compatibility-only. New Studio behavior must be expressed through UV-owned application/domain commands and tool services, with Project Unit of Work for coordinated mutations and Capability/Adapter execution underneath when required.

## Current rule

Do not build new Production Directions by adding recipe execution steps or growing `/execution-plan` as product truth.

Compatibility code may remain until its callers are migrated. Useful capability mappings and deterministic adapters can be reused behind Studio tools without preserving recipe execution as the user mental model.

The original detailed execution-plan contract remains available in Git history.
