"""Creation catalog truth for Product Orchestrator-owned journeys.

The recipe registry remains the durable provider-neutral vocabulary. This module
answers the narrower product question: which recipes are currently safe to
advertise for *new* project creation because UV Studio has an authoritative
Product Orchestrator projection and owned visible workspace for them.

Recipes omitted here remain readable/preservable through Project Store, but are
not advertised as creatable until their current workflow is explicitly
recovered. This prevents recipe declarations or old direct panels from being
mistaken for product readiness.
"""

from __future__ import annotations

from .commercial import COMMERCIAL_PRODUCT_RECIPE_ID
from .dubbing import DUBBING_RECIPE_ID
from .general_video import GENERAL_VIDEO_RECIPE_ID
from .narrated import NARRATED_RECIPE_ID
from .story import STORY_RECIPE_ID
from .targeted_edit import TARGETED_EDIT_RECIPE_ID

# The three IDs below are owned by the base Product Orchestrator implementation
# in project_workflow.py (Photo-to-Video, Visualizer and Music Video).
_BASE_ORCHESTRATOR_RECIPE_IDS = frozenset(
    {
        "photo_to_video",
        "visualizer",
        "music_video",
    }
)

CREATABLE_RECIPE_IDS = frozenset(
    {
        TARGETED_EDIT_RECIPE_ID,
        DUBBING_RECIPE_ID,
        GENERAL_VIDEO_RECIPE_ID,
        NARRATED_RECIPE_ID,
        STORY_RECIPE_ID,
        COMMERCIAL_PRODUCT_RECIPE_ID,
        *_BASE_ORCHESTRATOR_RECIPE_IDS,
    }
)


def is_recipe_creatable(recipe_id: str) -> bool:
    """Return whether a recipe is currently safe to advertise for creation."""

    return recipe_id in CREATABLE_RECIPE_IDS
