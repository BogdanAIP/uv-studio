"""Canonical input workspace for composition-first Stage 8 recipes.

This state stores only recipe inputs and exact project-owned media bindings. It is
not a timeline, generation plan, provider configuration or second project engine.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .models import ProjectDocument, ProjectValidationError
from .source_media import ProjectSourceMediaStore, SourceMediaError, SourceMediaNotFound
from .store import ProjectNotFound, ProjectStore, ProjectStoreError

STAGE8_WORKSPACE_SCHEMA_VERSION = 1
_STAGE8_WORKSPACES_EXTENSION = "stage8_recipe_workspaces"
_SUPPORTED_RECIPES = frozenset(
    {"general_video", "story_video", "commercial_product", "free_project", "narrated_video"}
)
_ALLOWED_SOURCE_KINDS = frozenset({"image", "video", "audio"})
_MAX_SOURCE_BINDINGS = 200
_MAX_BRIEF_LENGTH = 20_000
_MAX_SCRIPT_LENGTH = 200_000


class Stage8WorkspaceError(ProjectValidationError):
    pass


class Stage8WorkspaceNotFound(Stage8WorkspaceError):
    pass


def _text(value: Any, *, field_name: str, max_length: int, required: bool) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise Stage8WorkspaceError(f"{field_name} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise Stage8WorkspaceError(f"{field_name} must not be empty for this recipe")
    if len(normalized) > max_length:
        raise Stage8WorkspaceError(f"{field_name} must be <= {max_length} characters")
    return normalized


def _sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_role(recipe_id: str, kind: str) -> str:
    if recipe_id == "general_video":
        return {
            "image": "general_image",
            "video": "general_video",
            "audio": "general_audio",
        }[kind]
    if recipe_id == "story_video":
        return {"image": "story_image", "video": "story_video", "audio": "story_audio"}[kind]
    if recipe_id == "commercial_product":
        return {
            "image": "product_image",
            "video": "product_video",
            "audio": "commercial_audio",
        }[kind]
    if recipe_id == "narrated_video":
        return {
            "image": "narrated_image",
            "video": "narrated_video",
            "audio": "narrated_reference_audio",
        }[kind]
    return kind


@dataclass(frozen=True)
class Stage8SourceBinding:
    source_id: str
    kind: str
    role: str
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id:
            raise Stage8WorkspaceError("workspace source_id must be a non-empty string")
        if self.kind not in _ALLOWED_SOURCE_KINDS:
            raise Stage8WorkspaceError(f"unsupported workspace source kind: {self.kind!r}")
        if not isinstance(self.role, str) or not self.role:
            raise Stage8WorkspaceError("workspace source role must be non-empty")
        if not isinstance(self.path, str) or not self.path.startswith("sources/"):
            raise Stage8WorkspaceError("workspace source path must be project-owned source media")
        if not isinstance(self.sha256, str) or len(self.sha256) != 64:
            raise Stage8WorkspaceError("workspace source sha256 must be a 64-character digest")
        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes <= 0
        ):
            raise Stage8WorkspaceError(
                "workspace source size_bytes must be a positive integer"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "kind": self.kind,
            "role": self.role,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Stage8SourceBinding":
        if not isinstance(value, Mapping):
            raise Stage8WorkspaceError("workspace source binding must be an object")
        allowed = {"source_id", "kind", "role", "path", "sha256", "size_bytes"}
        unknown = set(value).difference(allowed)
        if unknown:
            raise Stage8WorkspaceError(
                f"unsupported workspace source fields: {sorted(unknown)!r}"
            )
        try:
            return cls(
                source_id=value["source_id"],
                kind=value["kind"],
                role=value["role"],
                path=value["path"],
                sha256=value["sha256"],
                size_bytes=value["size_bytes"],
            )
        except KeyError as exc:
            raise Stage8WorkspaceError(
                f"missing workspace source field: {exc.args[0]}"
            ) from exc


@dataclass(frozen=True)
class Stage8RecipeWorkspace:
    recipe_id: str
    brief: str
    script: str
    sources: tuple[Stage8SourceBinding, ...]
    revision_sha256: str
    schema_version: int = STAGE8_WORKSPACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != STAGE8_WORKSPACE_SCHEMA_VERSION:
            raise Stage8WorkspaceError(
                f"unsupported Stage 8 workspace schema_version: {self.schema_version!r}"
            )
        if self.recipe_id not in _SUPPORTED_RECIPES:
            raise Stage8WorkspaceError(
                f"unsupported Stage 8 workspace recipe: {self.recipe_id!r}"
            )
        object.__setattr__(
            self,
            "brief",
            _text(
                self.brief,
                field_name="brief",
                max_length=_MAX_BRIEF_LENGTH,
                required=self.recipe_id != "free_project",
            ),
        )
        object.__setattr__(
            self,
            "script",
            _text(
                self.script,
                field_name="script",
                max_length=_MAX_SCRIPT_LENGTH,
                required=False,
            ),
        )
        object.__setattr__(self, "sources", tuple(self.sources))
        if len(self.sources) > _MAX_SOURCE_BINDINGS:
            raise Stage8WorkspaceError(
                f"workspace supports at most {_MAX_SOURCE_BINDINGS} source bindings"
            )
        ids = [item.source_id for item in self.sources]
        if len(set(ids)) != len(ids):
            raise Stage8WorkspaceError("workspace source bindings must be unique")
        expected = self.compute_revision()
        if self.revision_sha256 != expected:
            raise Stage8WorkspaceError(
                "workspace revision_sha256 does not match canonical content"
            )

    def revision_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recipe_id": self.recipe_id,
            "brief": self.brief,
            "script": self.script,
            "sources": [item.to_dict() for item in self.sources],
        }

    def compute_revision(self) -> str:
        return _sha256(self.revision_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.revision_payload(), "revision_sha256": self.revision_sha256}

    @classmethod
    def build(
        cls,
        *,
        recipe_id: str,
        brief: str,
        script: str,
        sources: Sequence[Stage8SourceBinding],
    ) -> "Stage8RecipeWorkspace":
        normalized_brief = _text(
            brief,
            field_name="brief",
            max_length=_MAX_BRIEF_LENGTH,
            required=recipe_id != "free_project",
        )
        normalized_script = _text(
            script,
            field_name="script",
            max_length=_MAX_SCRIPT_LENGTH,
            required=False,
        )
        source_tuple = tuple(sources)
        payload = {
            "schema_version": STAGE8_WORKSPACE_SCHEMA_VERSION,
            "recipe_id": recipe_id,
            "brief": normalized_brief,
            "script": normalized_script,
            "sources": [item.to_dict() for item in source_tuple],
        }
        return cls(
            recipe_id=recipe_id,
            brief=normalized_brief,
            script=normalized_script,
            sources=source_tuple,
            revision_sha256=_sha256(payload),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Stage8RecipeWorkspace":
        if not isinstance(value, Mapping):
            raise Stage8WorkspaceError("Stage 8 workspace must be an object")
        allowed = {
            "schema_version",
            "recipe_id",
            "brief",
            "script",
            "sources",
            "revision_sha256",
        }
        unknown = set(value).difference(allowed)
        if unknown:
            raise Stage8WorkspaceError(
                f"unsupported Stage 8 workspace fields: {sorted(unknown)!r}"
            )
        try:
            raw_sources = value["sources"]
            if not isinstance(raw_sources, list):
                raise Stage8WorkspaceError("workspace sources must be an array")
            return cls(
                schema_version=value["schema_version"],
                recipe_id=value["recipe_id"],
                brief=value["brief"],
                script=value["script"],
                sources=tuple(Stage8SourceBinding.from_dict(item) for item in raw_sources),
                revision_sha256=value["revision_sha256"],
            )
        except KeyError as exc:
            raise Stage8WorkspaceError(
                f"missing Stage 8 workspace field: {exc.args[0]}"
            ) from exc


def _current_recipe(project: ProjectDocument) -> str:
    if project.recipe_id not in _SUPPORTED_RECIPES:
        raise Stage8WorkspaceError(
            "Stage 8 recipe workspace is available only for general_video, story_video, "
            "commercial_product, free_project or narrated_video"
        )
    return project.recipe_id


def _workspace_map(project: ProjectDocument) -> dict[str, Any]:
    raw = project.extensions.get(_STAGE8_WORKSPACES_EXTENSION, {})
    if not isinstance(raw, Mapping):
        raise Stage8WorkspaceError("stored Stage 8 workspace collection is malformed")
    return dict(raw)


def get_stage8_workspace(
    store: ProjectStore, project_id: str
) -> Stage8RecipeWorkspace | None:
    project = store.load_project(project_id)
    recipe_id = _current_recipe(project)
    raw = _workspace_map(project).get(recipe_id)
    if raw is None:
        return None
    workspace = Stage8RecipeWorkspace.from_dict(raw)
    if workspace.recipe_id != recipe_id:
        raise Stage8WorkspaceError(
            "stored workspace recipe does not match current project recipe"
        )

    media = ProjectSourceMediaStore(store)
    for binding in workspace.sources:
        try:
            reference, _ = media.resolve_verified(
                project_id,
                binding.source_id,
                expected_kind=binding.kind,
            )
        except (SourceMediaError, SourceMediaNotFound) as exc:
            raise Stage8WorkspaceError(str(exc)) from exc
        if (
            reference.path != binding.path
            or reference.metadata.get("sha256") != binding.sha256
            or reference.metadata.get("size_bytes") != binding.size_bytes
            or binding.role != _source_role(recipe_id, binding.kind)
        ):
            raise Stage8WorkspaceError(
                "stored Stage 8 source binding is stale or corrupted"
            )
    return workspace


def save_stage8_workspace(
    store: ProjectStore,
    project_id: str,
    *,
    brief: str,
    script: str,
    source_ids: Sequence[str],
) -> Stage8RecipeWorkspace:
    project = store.load_project(project_id)
    recipe_id = _current_recipe(project)
    if not isinstance(source_ids, Sequence) or isinstance(source_ids, (str, bytes)):
        raise Stage8WorkspaceError("source_ids must be an array")
    if len(source_ids) > _MAX_SOURCE_BINDINGS:
        raise Stage8WorkspaceError(
            f"source_ids supports at most {_MAX_SOURCE_BINDINGS} items"
        )
    if any(not isinstance(item, str) or not item for item in source_ids):
        raise Stage8WorkspaceError("every source_id must be a non-empty string")
    if len(set(source_ids)) != len(source_ids):
        raise Stage8WorkspaceError("source_ids must be unique")

    by_id = {item.id: item for item in project.sources}
    media = ProjectSourceMediaStore(store)
    bindings: list[Stage8SourceBinding] = []
    for source_id in source_ids:
        reference = by_id.get(source_id)
        if reference is None:
            raise Stage8WorkspaceError(
                f"source_id {source_id!r} is not registered in this project"
            )
        if reference.kind not in _ALLOWED_SOURCE_KINDS:
            raise Stage8WorkspaceError(
                f"source_id {source_id!r} is not image/video/audio media"
            )
        try:
            verified, _ = media.resolve_verified(
                project_id,
                source_id,
                expected_kind=reference.kind,
            )
        except (SourceMediaError, SourceMediaNotFound) as exc:
            raise Stage8WorkspaceError(str(exc)) from exc
        sha256 = verified.metadata.get("sha256")
        size_bytes = verified.metadata.get("size_bytes")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise Stage8WorkspaceError(
                f"source_id {source_id!r} has no trusted sha256"
            )
        if (
            isinstance(size_bytes, bool)
            or not isinstance(size_bytes, int)
            or size_bytes <= 0
        ):
            raise Stage8WorkspaceError(
                f"source_id {source_id!r} has no trusted size_bytes"
            )
        bindings.append(
            Stage8SourceBinding(
                source_id=verified.id,
                kind=verified.kind,
                role=_source_role(recipe_id, verified.kind),
                path=verified.path,
                sha256=sha256,
                size_bytes=size_bytes,
            )
        )

    workspace = Stage8RecipeWorkspace.build(
        recipe_id=recipe_id,
        brief=brief,
        script=script,
        sources=bindings,
    )
    extensions = dict(project.extensions)
    workspaces = _workspace_map(project)
    workspaces[recipe_id] = workspace.to_dict()
    extensions[_STAGE8_WORKSPACES_EXTENSION] = workspaces
    try:
        store.update_project(project_id, extensions=extensions)
    except (ProjectNotFound, ProjectStoreError, ProjectValidationError) as exc:
        raise Stage8WorkspaceError(str(exc)) from exc
    return workspace
