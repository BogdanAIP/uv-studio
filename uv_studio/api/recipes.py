"""HTTP catalog for provider-neutral UV Studio recipes."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, status

from uv_studio.recipes import RecipeRegistry, UnknownRecipe, build_builtin_registry

router = APIRouter(prefix="/api/uv/recipes", tags=["UV Studio Recipes"])


@lru_cache(maxsize=1)
def get_recipe_registry() -> RecipeRegistry:
    return build_builtin_registry()


@router.get("")
def list_recipes() -> list[dict[str, Any]]:
    return [recipe.to_dict() for recipe in get_recipe_registry().list()]


@router.get("/{recipe_id}")
def get_recipe(recipe_id: str) -> dict[str, Any]:
    try:
        return get_recipe_registry().get(recipe_id).to_dict()
    except UnknownRecipe as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        ) from exc
