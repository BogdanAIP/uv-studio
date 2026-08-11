"""UV Studio task recipe definitions and registry."""

from .builtin import BUILTIN_RECIPES, VIDEOCLAW_PIPELINE_BINDINGS, build_builtin_registry
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

__all__ = [
    "BUILTIN_RECIPES",
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
