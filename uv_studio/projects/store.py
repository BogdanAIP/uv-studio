"""Atomic filesystem Project Store for UV Studio."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Mapping, Any

from .migrations import migrate_project_data
from .models import (
    ProjectDocument,
    ProjectReference,
    ProjectValidationError,
    utc_now_iso,
    validate_identifier,
)

PROJECT_FILENAME = "project.json"
PROJECT_DIRECTORIES = (
    "sources",
    "assets",
    "tasks",
    "artifacts",
    "timeline",
    "reviews",
    "exports",
)


class ProjectStoreError(RuntimeError):
    pass


class ProjectNotFound(ProjectStoreError):
    pass


class ProjectAlreadyExists(ProjectStoreError):
    pass


class ProjectStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _project_dir(self, project_id: str) -> Path:
        validate_identifier(project_id, field_name="project_id")
        path = (self.root / project_id).resolve()
        if path.parent != self.root:
            raise ProjectValidationError("project path escaped project root")
        return path

    def project_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / PROJECT_FILENAME

    def create_project(
        self,
        *,
        title: str,
        recipe_id: str = "general_video",
        project_id: str | None = None,
        settings: Mapping[str, Any] | None = None,
        extensions: Mapping[str, Any] | None = None,
    ) -> ProjectDocument:
        project_id = project_id or f"prj_{uuid.uuid4().hex}"
        validate_identifier(project_id, field_name="project_id")
        validate_identifier(recipe_id, field_name="recipe_id")
        now = utc_now_iso()
        document = ProjectDocument(
            project_id=project_id,
            title=title,
            recipe_id=recipe_id,
            created_at=now,
            updated_at=now,
            settings=dict(settings or {}),
            extensions=dict(extensions or {}),
        )

        with self._lock:
            directory = self._project_dir(project_id)
            if directory.exists():
                raise ProjectAlreadyExists(project_id)
            directory.mkdir(parents=True)
            try:
                for name in PROJECT_DIRECTORIES:
                    (directory / name).mkdir()
                self._atomic_write_json(directory / PROJECT_FILENAME, document.to_dict())
            except Exception:
                self._remove_empty_project(directory)
                raise
        return document

    def load_project(self, project_id: str) -> ProjectDocument:
        path = self.project_path(project_id)
        if not path.is_file():
            raise ProjectNotFound(project_id)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProjectStoreError(f"Malformed project JSON: {path}") from exc
        except OSError as exc:
            raise ProjectStoreError(f"Could not read project: {path}") from exc

        try:
            migrated = migrate_project_data(raw)
            document = ProjectDocument.from_dict(migrated)
        except (ProjectValidationError, TypeError, ValueError) as exc:
            raise ProjectStoreError(f"Invalid project document: {path}: {exc}") from exc
        if document.project_id != project_id:
            raise ProjectStoreError(
                f"Project ID mismatch: directory={project_id!r}, document={document.project_id!r}"
            )
        return document

    def save_project(self, document: ProjectDocument) -> ProjectDocument:
        """Persist a complete project document and refresh updated_at."""
        path = self.project_path(document.project_id)
        if not path.is_file():
            raise ProjectNotFound(document.project_id)
        updated = replace(document, updated_at=utc_now_iso())
        with self._lock:
            self._atomic_write_json(path, updated.to_dict())
        return updated

    def update_project(
        self,
        project_id: str,
        *,
        title: str | None = None,
        recipe_id: str | None = None,
        settings: Mapping[str, Any] | None = None,
        extensions: Mapping[str, Any] | None = None,
        sources: Iterable[ProjectReference] | None = None,
        artifacts: Iterable[ProjectReference] | None = None,
    ) -> ProjectDocument:
        with self._lock:
            current = self.load_project(project_id)
            updated = replace(
                current,
                title=current.title if title is None else title,
                recipe_id=current.recipe_id if recipe_id is None else recipe_id,
                settings=current.settings if settings is None else dict(settings),
                extensions=current.extensions if extensions is None else dict(extensions),
                sources=current.sources if sources is None else tuple(sources),
                artifacts=current.artifacts if artifacts is None else tuple(artifacts),
                updated_at=utc_now_iso(),
            )
            self._atomic_write_json(self.project_path(project_id), updated.to_dict())
            return updated

    def list_projects(self) -> list[ProjectDocument]:
        projects: list[ProjectDocument] = []
        for child in sorted(self.root.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir() or not (child / PROJECT_FILENAME).is_file():
                continue
            try:
                projects.append(self.load_project(child.name))
            except (ProjectValidationError, ProjectStoreError):
                continue
        projects.sort(key=lambda item: item.updated_at, reverse=True)
        return projects

    def _atomic_write_json(self, path: Path, data: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            serialized = json.dumps(
                dict(data),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n"
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except Exception:
            try:
                temp.unlink(missing_ok=True)
            finally:
                raise

    @staticmethod
    def _remove_empty_project(directory: Path) -> None:
        if not directory.exists():
            return
        for child in sorted(directory.rglob("*"), reverse=True):
            try:
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            except OSError:
                pass
        try:
            directory.rmdir()
        except OSError:
            pass
