"""UV Studio task recipe definitions and registry."""

from .builtin import (
    BUILTIN_RECIPES as _LEGACY_BUILTIN_RECIPES,
    VIDEOCLAW_PIPELINE_BINDINGS,
)
from .dubbing import DUBBING
from .models import (
    RECIPE_SCHEMA_VERSION,
    PolicyMode,
    ProductionPolicy,
    RecipeDefinition,
    RecipeStep,
    RecipeUIHints,
    RecipeValidationError,
)
from .registry import DuplicateRecipe, RecipeRegistry, RecipeRegistryError, UnknownRecipe

BUILTIN_RECIPES = (*_LEGACY_BUILTIN_RECIPES, DUBBING)


def build_builtin_registry() -> RecipeRegistry:
    """Return the supported UV task catalog, including Product Recovery recipes."""

    return RecipeRegistry(BUILTIN_RECIPES)


__all__ = [
    "BUILTIN_RECIPES",
    "DUBBING",
    "VIDEOCLAW_PIPELINE_BINDINGS",
    "RECIPE_SCHEMA_VERSION",
    "DuplicateRecipe",
    "PolicyMode",
    "ProductionPolicy",
    "RecipeDefinition",
    "RecipeRegistry",
    "RecipeRegistryError",
    "RecipeStep",
    "RecipeUIHints",
    "RecipeValidationError",
    "UnknownRecipe",
    "build_builtin_registry",
]
