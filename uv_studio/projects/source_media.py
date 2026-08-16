"""Canonical project-owned source media registration for the UV Studio editor."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .media_integrity import MediaIntegrityError, verify_registered_media_bytes
from .models import ProjectDocument, ProjectReference, ProjectValidationError
from .store import ProjectStore, ProjectStoreError

_MAX_ORIGINAL_NAME_LENGTH = 255
_SAFE_EXTENSION_RE = re.compile(r"^\.[A-Za-z0-9]{1,16}$")
_SOURCE_MEDIA_KINDS = frozenset({"video", "audio", "image"})


class SourceMediaError(ProjectValidationError):
    pass


class SourceMediaNotFound(SourceMediaError):
    pass


def normalize_original_filename(value: str) -> str:
    if not isinstance(value, str):
        raise SourceMediaError("source filename must be a string")
    if "\x00" in value or any(ord(char) < 32 for char in value):
        raise SourceMediaError("source filename contains control characters")
    normalized = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not normalized or normalized in {".", ".."}:
        raise SourceMediaError("source filename must not be empty")
    if len(normalized) > _MAX_ORIGINAL_NAME_LENGTH:
        raise SourceMediaError(f"source filename must be <= {_MAX_ORIGINAL_NAME_LENGTH} characters")
    return normalized


def _portable_extension(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    return suffix if _SAFE_EXTENSION_RE.fullmatch(suffix) else ""


def _media_kind(value: str) -> str:
    if not isinstance(value, str) or value not in _SOURCE_MEDIA_KINDS:
        raise SourceMediaError(
            f"source media kind must be one of {sorted(_SOURCE_MEDIA_KINDS)!r}"
        )
    return value


@dataclass(frozen=True)
class AllocatedSourceMedia:
    source_id: str
    relative_path: str
    absolute_path: Path
    original_name: str


class ProjectSourceMediaStore:
    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def allocate(self, project_id: str, original_filename: str) -> AllocatedSourceMedia:
        original_name = normalize_original_filename(original_filename)
        self.project_store.load_project(project_id)
        source_id = f"src_{uuid.uuid4().hex}"
        relative_path = f"sources/{source_id}{_portable_extension(original_name)}"
        try:
            absolute_path = self.project_store.resolve_project_file(
                project_id,
                relative_path,
                must_exist=False,
                allowed_roots=("sources",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise SourceMediaError(str(exc)) from exc
        if absolute_path.exists() or absolute_path.is_symlink():
            raise SourceMediaError("allocated source path already exists")
        return AllocatedSourceMedia(source_id, relative_path, absolute_path, original_name)

    def register(
        self,
        project_id: str,
        allocation: AllocatedSourceMedia,
        *,
        metadata: Mapping[str, Any],
        media_kind: str = "video",
    ) -> ProjectDocument:
        if not isinstance(allocation, AllocatedSourceMedia):
            raise SourceMediaError("allocation must be AllocatedSourceMedia")
        media_kind = _media_kind(media_kind)
        if not allocation.absolute_path.is_file() or allocation.absolute_path.is_symlink():
            raise SourceMediaError("source media must exist as a regular project file before registration")
        reference = ProjectReference(
            id=allocation.source_id,
            kind=media_kind,
            path=allocation.relative_path,
            metadata=dict(metadata),
        )
        with self.project_store._lock:
            project = self.project_store.load_project(project_id)
            if any(item.id == reference.id for item in (*project.sources, *project.artifacts)):
                raise SourceMediaError(f"duplicate source reference id: {reference.id}")
            return self.project_store.update_project(
                project_id, sources=project.sources + (reference,)
            )

    def get(
        self,
        project_id: str,
        source_id: str,
        *,
        expected_kind: str = "video",
    ) -> ProjectReference:
        expected_kind = _media_kind(expected_kind)
        project = self.project_store.load_project(project_id)
        for reference in project.sources:
            if reference.id == source_id:
                if reference.kind != expected_kind:
                    raise SourceMediaError(
                        f"source reference {source_id!r} is not registered as {expected_kind} media"
                    )
                return reference
        raise SourceMediaNotFound(source_id)

    def resolve(
        self,
        project_id: str,
        source_id: str,
        *,
        expected_kind: str = "video",
    ) -> tuple[ProjectReference, Path]:
        reference = self.get(project_id, source_id, expected_kind=expected_kind)
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                reference.path,
                must_exist=True,
                allowed_roots=("sources",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise SourceMediaError(str(exc)) from exc
        if not path.is_file() or path.is_symlink():
            raise SourceMediaError("registered source media is not a regular project file")
        return reference, path

    def resolve_verified(
        self,
        project_id: str,
        source_id: str,
        *,
        expected_kind: str = "video",
    ) -> tuple[ProjectReference, Path]:
        reference, path = self.resolve(
            project_id, source_id, expected_kind=expected_kind
        )
        try:
            verify_registered_media_bytes(path, reference.metadata)
        except MediaIntegrityError as exc:
            raise SourceMediaError(str(exc)) from exc
        return reference, path
