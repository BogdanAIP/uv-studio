"""Deterministic registry for UV Studio recipe definitions."""

from __future__ import annotations

from collections.abc import Iterable

from .models import RecipeDefinition, RecipeValidationError, validate_semantic_id


class RecipeRegistryError(RuntimeError):
    pass


class DuplicateRecipe(RecipeRegistryError):
    pass


class UnknownRecipe(RecipeRegistryError):
    pass


class RecipeRegistry:
    def __init__(self, recipes: Iterable[RecipeDefinition] = ()) -> None:
        self._recipes: dict[str, RecipeDefinition] = {}
        for recipe in recipes:
            self.register(recipe)

    def register(self, recipe: RecipeDefinition) -> RecipeDefinition:
        if not isinstance(recipe, RecipeDefinition):
            raise RecipeValidationError("registry accepts only RecipeDefinition values")
        if recipe.recipe_id in self._recipes:
            raise DuplicateRecipe(recipe.recipe_id)
        self._recipes[recipe.recipe_id] = recipe
        return recipe

    def get(self, recipe_id: str) -> RecipeDefinition:
        try:
            normalized = validate_semantic_id(recipe_id, field_name="recipe_id")
        except RecipeValidationError as exc:
            raise UnknownRecipe(recipe_id) from exc
        try:
            return self._recipes[normalized]
        except KeyError as exc:
            raise UnknownRecipe(normalized) from exc

    def contains(self, recipe_id: str) -> bool:
        try:
            self.get(recipe_id)
        except UnknownRecipe:
            return False
        return True

    def list(self) -> tuple[RecipeDefinition, ...]:
        """Return recipes in stable registration order."""
        return tuple(self._recipes.values())

    def ids(self) -> tuple[str, ...]:
        return tuple(self._recipes)
