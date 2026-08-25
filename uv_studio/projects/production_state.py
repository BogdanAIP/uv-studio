"""Bounded canonical storage root for shared/direction production documents."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from uv_studio.projects.models import ProjectValidationError, validate_identifier
from uv_studio.projects.store import ProjectStore, ProjectStoreError

PRODUCTION_ROOT = "production"


class ProductionStateError(ProjectValidationError):
    """A canonical production document is malformed or unsafe."""


class ProductionDocumentNotFound(ProductionStateError):
    pass


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not portable")


def _validate_document(document: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ProductionStateError("production document must be a JSON object")
    schema_version = document.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version <= 0
    ):
        raise ProductionStateError(
            "production document schema_version must be a positive integer"
        )
    payload = dict(document)
    try:
        json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ProductionStateError(
            "production document must contain strict portable JSON values"
        ) from exc
    return payload


class ProductionDocumentStore:
    """Persistence seam only; concrete Scene/Shot/etc. models validate their own schema."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    @staticmethod
    def _document_id(document_id: str) -> str:
        try:
            return validate_identifier(document_id, field_name="production document_id")
        except ProjectValidationError as exc:
            raise ProductionStateError(str(exc)) from exc

    def _path(self, project_id: str, document_id: str):
        document_id = self._document_id(document_id)
        try:
            return self.project_store.resolve_project_file(
                project_id,
                f"{PRODUCTION_ROOT}/{document_id}.json",
                allowed_roots=(PRODUCTION_ROOT,),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ProductionStateError(str(exc)) from exc

    def load(self, project_id: str, document_id: str) -> dict[str, Any]:
        self.project_store.load_project(project_id)
        path = self._path(project_id, document_id)
        if not path.exists():
            raise ProductionDocumentNotFound(document_id)
        if not path.is_file() or path.is_symlink():
            raise ProductionStateError("production document path must be a regular file")
        try:
            raw = json.loads(
                path.read_text(encoding="utf-8"),
                parse_constant=_reject_nonfinite_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProductionStateError("production document is malformed JSON") from exc
        except OSError as exc:
            raise ProductionStateError("production document could not be read") from exc
        if not isinstance(raw, Mapping):
            raise ProductionStateError("production document must be a JSON object")
        return _validate_document(raw)

    def save(
        self,
        project_id: str,
        document_id: str,
        document: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = _validate_document(document)
        with self.project_store._lock:
            self.project_store.load_project(project_id)
            try:
                self.project_store._atomic_write_json(
                    self._path(project_id, document_id),
                    payload,
                )
            except ProjectStoreError as exc:
                raise ProductionStateError(str(exc)) from exc
        return payload
