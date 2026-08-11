"""UV Studio task recipe definitions, registry and execution planning."""

from .builtin import BUILTIN_RECIPES, VIDEOCLAW_PIPELINE_BINDINGS, build_builtin_registry
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

__all__ = [
    "BUILTIN_RECIPES",
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
