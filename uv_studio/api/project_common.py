"""Recipe-neutral project API schemas and dependencies shared by Studio surfaces."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from uv_studio.config import projects_root
from uv_studio.projects.identity import classify_project_identity
from uv_studio.projects.models import ProjectDocument
from uv_studio.projects.store import ProjectStore


class ProjectReferencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectIdentityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["modern_direction", "legacy_compatibility", "invalid_recovery"]
    direction_id: str | None = None
    compatibility_kind: Literal[
        "recipe",
        "studio_first",
        "studio_unversioned",
        "production_directions_v2",
    ] | None = None
    reason: str | None = None


class ProjectPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    project_id: str
    title: str
    recipe_id: str
    created_at: str
    updated_at: str
    settings: dict[str, Any] = Field(default_factory=dict)
    sources: list[ProjectReferencePayload] = Field(default_factory=list)
    artifacts: list[ProjectReferencePayload] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)
    product_identity: ProjectIdentityPayload


@lru_cache(maxsize=1)
def get_project_store() -> ProjectStore:
    return ProjectStore(projects_root())


def project_payload(document: ProjectDocument) -> ProjectPayload:
    return ProjectPayload.model_validate(
        {**document.to_dict(), "product_identity": classify_project_identity(document).to_dict()}
    )
