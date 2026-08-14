from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ProjectValidationError, validate_identifier
from .store import ProjectStore, ProjectStoreError

CURRENT_REVIEW_PATH = "reviews/dubbing-review-current.json"


class CurrentReviewError(ProjectValidationError):
    pass


def _id(value: Any, field: str) -> str:
    try:
        return validate_identifier(value, field_name=field)
    except ProjectValidationError as exc:
        raise CurrentReviewError(str(exc)) from exc


class CurrentReviewStore:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def _path(self, project_id: str) -> Path:
        try:
            return self.store.resolve_project_file(
                project_id, CURRENT_REVIEW_PATH, must_exist=False, allowed_roots=("reviews",)
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise CurrentReviewError(str(exc)) from exc

    def load(self, project_id: str) -> dict[str, str]:
        self.store.load_project(project_id)
        path = self._path(project_id)
        if not path.exists():
            return {}
        if not path.is_file() or path.is_symlink():
            raise CurrentReviewError("current review state must be a regular file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CurrentReviewError("current review state could not be read") from exc
        if not isinstance(data, dict) or set(data) != {"schema_version", "current_by_take"}:
            raise CurrentReviewError("current review state has invalid fields")
        if data["schema_version"] != 1 or not isinstance(data["current_by_take"], dict):
            raise CurrentReviewError("unsupported current review state")
        return {_id(k, "take_id"): _id(v, "review_id") for k, v in data["current_by_take"].items()}

    def set_current(self, project_id: str, take_id: str, review_id: str) -> None:
        with self.store._lock:
            values = self.load(project_id)
            values[_id(take_id, "take_id")] = _id(review_id, "review_id")
            self.store._atomic_write_json(
                self._path(project_id),
                {"schema_version": 1, "current_by_take": dict(sorted(values.items()))},
            )

    def resolve_current(self, project_id: str, take_id: str, reviews: tuple[Any, ...]) -> str | None:
        take = _id(take_id, "take_id")
        matching = [item.review_id for item in reviews if item.take_id == take]
        explicit = self.load(project_id).get(take)
        if explicit is not None:
            if explicit not in matching:
                raise CurrentReviewError("current review pointer references missing history")
            return explicit
        return matching[0] if len(matching) == 1 else None
