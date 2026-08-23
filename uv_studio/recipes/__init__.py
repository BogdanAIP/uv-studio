"""UV Studio task recipe definitions, registry and execution planning."""

from .builtin import (
    BUILTIN_RECIPES as _LEGACY_BUILTIN_RECIPES,
    VIDEOCLAW_PIPELINE_BINDINGS,
)
from .dubbing import DUBBING
from .execution import (
    EXECUTION_PLAN_SCHEMA_VERSION,
    CompatibilityTarget,
    ExecutionCompatibility,
    ExecutionInputSlot,
    InputSlotKind,
    RecipeExecutionPlan,
    RuntimeConfigSlot,
    resolve_project_execution,
    resolve_recipe_execution,
)
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
    "EXECUTION_PLAN_SCHEMA_VERSION",
    "RECIPE_SCHEMA_VERSION",
    "CompatibilityTarget",
    "DuplicateRecipe",
    "ExecutionCompatibility",
    "ExecutionInputSlot",
    "InputSlotKind",
    "PolicyMode",
    "ProductionPolicy",
    "RecipeDefinition",
    "RecipeExecutionPlan",
    "RecipeRegistry",
    "RecipeRegistryError",
    "RecipeStep",
    "RecipeUIHints",
    "RecipeValidationError",
    "RuntimeConfigSlot",
    "UnknownRecipe",
    "build_builtin_registry",
    "resolve_project_execution",
    "resolve_recipe_execution",
]
