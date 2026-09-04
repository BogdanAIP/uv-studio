"""Internal Recipe Registry compatibility provider.

The public ``/api/uv/recipes`` catalog was retired once Production Directions
became the sole supported new-project composition authority. The registry itself
remains internal compatibility data for execution-plan and Product-Orchestrator
surfaces until their separately governed retirement slices.
"""

from __future__ import annotations

from functools import lru_cache

from uv_studio.recipes import RecipeRegistry, build_builtin_registry


@lru_cache(maxsize=1)
def get_recipe_registry() -> RecipeRegistry:
    return build_builtin_registry()
