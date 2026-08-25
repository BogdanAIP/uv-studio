"""Atomic filesystem Project Store for UV Studio."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from .identity import assert_project_identity_transition, require_valid_project_identity
from .migrations import migrate_project_data
from .models import (
    ProjectDocument,
    ProjectReference,
    ProjectValidationError,
    utc_now_iso,
    validate_identifier,
    validate_project_relative_path,
)

PROJECT_FILENAME = "project.json"
PROJECT_DIRECTORIES = (
    "sources",
    "assets",
    "tasks",
    "artifacts",
    "production",
    "timeline",
    "history",
    "reviews",
    "exports",
)


class ProjectStoreError(RuntimeError):
    pass


class ProjectNotFound(ProjectStoreError):
    pass


class ProjectAlreadyExists(ProjectStoreError):
    pass


@dataclass(frozen=True)
class ProjectListDiagnostic:
    project_id: str
    path: str
    error: str


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not portable")


def _bounded_error_message(exc: Exception, *, limit: int = 500) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if len(message) <= limit:
        return message
    return message[: limit - 3] + "..."


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

    def project_directory(self, project_id: str) -> Path:
        directory = self._project_dir(project_id)
        if not (directory / PROJECT_FILENAME).is_file():
            raise ProjectNotFound(project_id)
        return directory

    def resolve_project_file(
        self,
        project_id: str,
        relative_path: str,
        *,
        must_exist: bool = False,
        allowed_roots: Iterable[str] | None = None,
    ) -> Path:
        """Resolve a canonical project-relative file without allowing filesystem escape.

        The method is intentionally conservative for writes: the parent directory
        must already exist. Callers cannot create arbitrary directory trees or use
        symlinks to escape the canonical project directory or the caller's explicit
        allowed-root boundary.
        """

        canonical = validate_project_relative_path(relative_path)
        parts = PurePosixPath(canonical).parts
        if not parts:
            raise ProjectValidationError("project-relative file path is empty")

        roots: set[str] | None = None
        if allowed_roots is not None:
            roots = set(allowed_roots)
            unknown_roots = roots.difference(PROJECT_DIRECTORIES)
            if unknown_roots:
                raise ProjectValidationError(
                    f"unknown allowed project roots: {sorted(unknown_roots)!r}"
                )
            if parts[0] not in roots:
                raise ProjectValidationError(
                    f"path root {parts[0]!r} is not allowed for this operation"
                )

        project_dir = self.project_directory(project_id)
        resolved_allowed_roots: tuple[Path, ...] = ()
        if roots is not None:
            allowed_paths: list[Path] = []
            for root in sorted(roots):
                root_path = project_dir / root
                try:
                    resolved_root = root_path.resolve(strict=True)
                except OSError as exc:
                    raise ProjectValidationError(
                        f"allowed project root cannot be resolved: {root!r}"
                    ) from exc
                if resolved_root != root_path:
                    raise ProjectValidationError(
                        f"allowed project root must not be a symlink: {root!r}"
                    )
                allowed_paths.append(resolved_root)
            resolved_allowed_roots = tuple(allowed_paths)

        candidate = project_dir.joinpath(*parts)
        try:
            resolved_parent = candidate.parent.resolve(strict=True)
        except OSError as exc:
            raise ProjectValidationError(
                f"parent directory does not exist inside project: {canonical!r}"
            ) from exc
        if resolved_parent != project_dir and project_dir not in resolved_parent.parents:
            raise ProjectValidationError("project file parent escaped project directory")
        if resolved_allowed_roots and not any(
            resolved_parent == root or root in resolved_parent.parents
            for root in resolved_allowed_roots
        ):
            raise ProjectValidationError("project file parent escaped allowed project roots")

        if candidate.exists() or candidate.is_symlink():
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise ProjectValidationError(f"project file cannot be resolved: {canonical!r}") from exc
            if resolved != project_dir and project_dir not in resolved.parents:
                raise ProjectValidationError("project file escaped project directory")
            if resolved_allowed_roots and not any(
                resolved == root or root in resolved.parents
                for root in resolved_allowed_roots
            ):
                raise ProjectValidationError("project file escaped allowed project roots")
            candidate = resolved
        elif must_exist:
            raise ProjectValidationError(f"project file does not exist: {canonical!r}")

        return candidate

    def create_project(
        self,
        *,
        title: str,
        recipe_id: str,
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
        require_valid_project_identity(document)

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
            raw = json.loads(
                path.read_text(encoding="utf-8"),
                parse_constant=_reject_nonfinite_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProjectStoreError(f"Malformed project JSON: {path}: {exc}") from exc
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
        with self._lock:
            current = self.load_project(document.project_id)
            updated = replace(document, updated_at=utc_now_iso())
            assert_project_identity_transition(current, updated)
            self._atomic_write_json(self.project_path(document.project_id), updated.to_dict())
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
            assert_project_identity_transition(current, updated)
            self._atomic_write_json(self.project_path(project_id), updated.to_dict())
            return updated

    def list_projects(self) -> list[ProjectDocument]:
        projects, _diagnostics = self.list_projects_with_diagnostics()
        return projects

    def list_projects_with_diagnostics(
        self,
    ) -> tuple[list[ProjectDocument], list[ProjectListDiagnostic]]:
        """Return healthy projects while isolating damaged project directories.

        Corrupt project bytes are never rewritten or deleted. Callers that need
        recovery information can inspect the bounded diagnostic list, while the
        stable `list_projects()` contract continues to expose only healthy projects.
        """

        projects: list[ProjectDocument] = []
        diagnostics: list[ProjectListDiagnostic] = []
        for child in sorted(self.root.iterdir(), key=lambda item: item.name.lower()):
            project_path = child / PROJECT_FILENAME
            if not child.is_dir() or not project_path.is_file():
                continue
            try:
                projects.append(self.load_project(child.name))
            except (ProjectValidationError, ProjectStoreError) as exc:
                diagnostics.append(
                    ProjectListDiagnostic(
                        project_id=child.name,
                        path=str(project_path),
                        error=_bounded_error_message(exc),
                    )
                )
        projects.sort(key=lambda item: item.updated_at, reverse=True)
        return projects, diagnostics

    def commit_staged_project(self, staged_project: Path | str, project_id: str) -> Path:
        """Atomically move a fully validated staged project into the canonical store.

        The staged directory must already live somewhere beneath the Project Store
        root so the final directory rename stays on the same filesystem. Callers are
        responsible for validating archive/file contents before invoking this method.
        """
        validate_identifier(project_id, field_name="project_id")
        staged = Path(staged_project).expanduser()
        if staged.is_symlink():
            raise ProjectStoreError("Staged project cannot be a symlink")
        try:
            staged = staged.resolve(strict=True)
        except OSError as exc:
            raise ProjectStoreError(f"Staged project does not exist: {staged}") from exc
        if not staged.is_dir():
            raise ProjectStoreError(f"Staged project is not a directory: {staged}")
        if staged.name != project_id:
            raise ProjectStoreError(
                f"Staged project directory name mismatch: expected={project_id!r} actual={staged.name!r}"
            )
        if staged == self.root or self.root not in staged.parents:
            raise ProjectStoreError("Staged project must live beneath the Project Store root")

        destination = self._project_dir(project_id)
        if staged == destination:
            raise ProjectStoreError("Staged project is already at its canonical destination")

        # Validate the staged canonical document before moving anything.
        staged_store = ProjectStore(staged.parent)
        document = staged_store.load_project(project_id)
        if document.project_id != project_id:
            raise ProjectStoreError("Staged project document ID does not match destination ID")
        require_valid_project_identity(document)

        with self._lock:
            if destination.exists():
                raise ProjectAlreadyExists(project_id)
            try:
                os.replace(staged, destination)
            except OSError as exc:
                raise ProjectStoreError(
                    f"Could not commit staged project {project_id!r} into canonical store"
                ) from exc
        return destination

    def _atomic_write_json(self, path: Path, data: Mapping[str, Any]) -> None:
        try:
            serialized = json.dumps(
                dict(data),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        except (TypeError, ValueError) as exc:
            raise ProjectStoreError(
                f"Project data is not strict portable JSON: {_bounded_error_message(exc)}"
            ) from exc
        self._atomic_write_bytes(path, serialized.encode("utf-8"))

    def _atomic_write_bytes(self, path: Path, data: bytes) -> None:
        """Replace one project-owned file after flushing its complete new bytes."""

        if not isinstance(data, bytes):
            raise ProjectStoreError("atomic project writes require bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("wb") as handle:
                handle.write(data)
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
        for child in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
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
