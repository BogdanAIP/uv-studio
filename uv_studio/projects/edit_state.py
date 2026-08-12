"""Typed portable accepted range-edit decisions for canonical UV Studio projects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .media_ranges import ProjectMediaRange
from .models import (
    ProjectValidationError,
    validate_identifier,
    validate_project_relative_path,
)
from .store import ProjectStore, ProjectStoreError

EDIT_STATE_SCHEMA_VERSION = 1
EDIT_STATE_PATH = "timeline/range-edits.json"
_EDIT_INPUT_ROOTS = ("sources", "assets", "artifacts", "exports")


class EditStateError(ProjectValidationError):
    """Invalid or inconsistent canonical edit-decision state."""


class EditStateNotFound(EditStateError):
    pass


@dataclass(frozen=True)
class AcceptedRangeEdit:
    edit_id: str
    source_path: str
    start_us: int
    end_us: int
    replacement_path: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "edit_id",
            validate_identifier(self.edit_id, field_name="edit_id"),
        )
        try:
            requested = ProjectMediaRange(
                source_path=self.source_path,
                start_us=self.start_us,
                end_us=self.end_us,
            )
        except ProjectValidationError as exc:
            raise EditStateError(str(exc)) from exc
        object.__setattr__(self, "source_path", requested.source_path)
        object.__setattr__(self, "start_us", requested.start_us)
        object.__setattr__(self, "end_us", requested.end_us)
        try:
            replacement = validate_project_relative_path(self.replacement_path)
        except ProjectValidationError as exc:
            raise EditStateError(str(exc)) from exc
        object.__setattr__(self, "replacement_path", replacement)
        if replacement == requested.source_path:
            raise EditStateError("replacement_path must not equal source_path")

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "edit_id": self.edit_id,
            "source_path": self.source_path,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "replacement_path": self.replacement_path,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AcceptedRangeEdit":
        if not isinstance(data, Mapping):
            raise EditStateError("accepted range edit must be a JSON object")
        required = ("edit_id", "source_path", "start_us", "end_us", "replacement_path")
        missing = [field for field in required if field not in data]
        if missing:
            raise EditStateError(f"accepted range edit is missing fields: {', '.join(missing)}")
        return cls(
            edit_id=str(data["edit_id"]),
            source_path=str(data["source_path"]),
            start_us=data["start_us"],
            end_us=data["end_us"],
            replacement_path=str(data["replacement_path"]),
        )


@dataclass(frozen=True)
class RangeEditState:
    edits: tuple[AcceptedRangeEdit, ...] = ()
    schema_version: int = EDIT_STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EDIT_STATE_SCHEMA_VERSION:
            raise EditStateError(
                f"unsupported edit-state schema: {self.schema_version!r}; "
                f"supported={EDIT_STATE_SCHEMA_VERSION}"
            )
        edits = tuple(self.edits)
        if not all(isinstance(edit, AcceptedRangeEdit) for edit in edits):
            raise EditStateError("edits must contain AcceptedRangeEdit values")
        ids = [edit.edit_id for edit in edits]
        if len(ids) != len(set(ids)):
            raise EditStateError("edit_id values must be unique")
        canonical = tuple(
            sorted(edits, key=lambda edit: (edit.source_path, edit.start_us, edit.end_us, edit.edit_id))
        )
        self._validate_non_overlapping(canonical)
        object.__setattr__(self, "edits", canonical)

    @staticmethod
    def _validate_non_overlapping(edits: tuple[AcceptedRangeEdit, ...]) -> None:
        previous_by_source: dict[str, AcceptedRangeEdit] = {}
        for edit in edits:
            previous = previous_by_source.get(edit.source_path)
            if previous is not None and edit.start_us < previous.end_us:
                raise EditStateError(
                    "accepted edits for one source must not overlap: "
                    f"{previous.edit_id!r} and {edit.edit_id!r}"
                )
            previous_by_source[edit.source_path] = edit

    def for_source(self, source_path: str) -> tuple[AcceptedRangeEdit, ...]:
        canonical = validate_project_relative_path(source_path)
        return tuple(edit for edit in self.edits if edit.source_path == canonical)

    def add(self, edit: AcceptedRangeEdit) -> "RangeEditState":
        if not isinstance(edit, AcceptedRangeEdit):
            raise EditStateError("add requires an AcceptedRangeEdit")
        return RangeEditState(edits=(*self.edits, edit))

    def remove(self, edit_id: str) -> "RangeEditState":
        normalized = validate_identifier(edit_id, field_name="edit_id")
        remaining = tuple(edit for edit in self.edits if edit.edit_id != normalized)
        if len(remaining) == len(self.edits):
            raise EditStateNotFound(normalized)
        return RangeEditState(edits=remaining)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "edits": [edit.to_dict() for edit in self.edits],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RangeEditState":
        if not isinstance(data, Mapping):
            raise EditStateError("edit-state document must be a JSON object")
        if set(data).difference({"schema_version", "edits"}):
            raise EditStateError(
                f"unsupported edit-state fields: {sorted(set(data).difference({'schema_version', 'edits'}))!r}"
            )
        if "schema_version" not in data:
            raise EditStateError("edit-state document is missing schema_version")
        raw_edits = data.get("edits", [])
        if not isinstance(raw_edits, list):
            raise EditStateError("edit-state edits must be a list")
        return cls(
            schema_version=data["schema_version"],
            edits=tuple(AcceptedRangeEdit.from_dict(item) for item in raw_edits),
        )


class RangeEditStateStore:
    """Atomic typed edit-state persistence under one canonical project timeline file."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _path(self, project_id: str, *, must_exist: bool = False) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                EDIT_STATE_PATH,
                must_exist=must_exist,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise EditStateError(str(exc)) from exc

    def load(self, project_id: str, *, validate_references: bool = True) -> RangeEditState:
        path = self._path(project_id)
        if not path.exists():
            return RangeEditState()
        if not path.is_file() or path.is_symlink():
            raise EditStateError("edit-state path must be a regular project file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise EditStateError("edit-state document is malformed JSON") from exc
        except OSError as exc:
            raise EditStateError("edit-state document could not be read") from exc
        state = RangeEditState.from_dict(data)
        if validate_references:
            self._validate_references(project_id, state)
        return state

    def save(self, project_id: str, state: RangeEditState) -> RangeEditState:
        if not isinstance(state, RangeEditState):
            raise EditStateError("save requires RangeEditState")
        self._validate_references(project_id, state)
        path = self._path(project_id)
        # ProjectStore owns the atomic JSON primitive used by canonical project.json;
        # typed project documents reuse the same fsync + os.replace behavior.
        self.project_store._atomic_write_json(path, state.to_dict())
        return state

    def accept(self, project_id: str, edit: AcceptedRangeEdit) -> RangeEditState:
        current = self.load(project_id)
        updated = current.add(edit)
        return self.save(project_id, updated)

    def remove(self, project_id: str, edit_id: str) -> RangeEditState:
        current = self.load(project_id)
        updated = current.remove(edit_id)
        return self.save(project_id, updated)

    def validate_project(self, project_id: str) -> RangeEditState:
        return self.load(project_id, validate_references=True)

    def _validate_references(self, project_id: str, state: RangeEditState) -> None:
        for edit in state.edits:
            for field_name, relative_path in (
                ("source_path", edit.source_path),
                ("replacement_path", edit.replacement_path),
            ):
                try:
                    resolved = self.project_store.resolve_project_file(
                        project_id,
                        relative_path,
                        must_exist=True,
                        allowed_roots=_EDIT_INPUT_ROOTS,
                    )
                except (ProjectValidationError, ProjectStoreError) as exc:
                    raise EditStateError(
                        f"{field_name} for edit {edit.edit_id!r} is not a valid existing project file: {exc}"
                    ) from exc
                if not resolved.is_file() or resolved.is_symlink():
                    raise EditStateError(
                        f"{field_name} for edit {edit.edit_id!r} must be a regular project file"
                    )
