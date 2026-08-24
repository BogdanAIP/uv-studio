"""UV Studio application services.

Application services coordinate canonical domain state and semantic capabilities
without making HTTP adapters or frontend routes the workflow authority.
"""

from .creative_projects import (
    CREATIVE_EXTENSION_KEY,
    CREATIVE_SCHEMA_VERSION,
    CreativeProjectError,
    CreativeProjectService,
    is_creative_project,
)

__all__ = [
    "CREATIVE_EXTENSION_KEY",
    "CREATIVE_SCHEMA_VERSION",
    "CreativeProjectError",
    "CreativeProjectService",
    "is_creative_project",
]
