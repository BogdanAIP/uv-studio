"""Project-owned visual assembly plan for Stage 7 Music Video Mode."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .models import (
    ProjectValidationError,
    compatibility_recipe_id,
    validate_identifier,
    validate_project_relative_path,
)
from .music_direction import MusicDirectionError, MusicDirectionStore
from .source_media import ProjectSourceMediaStore, SourceMediaError, SourceMediaNotFound
from .store import ProjectStore, ProjectStoreError

MUSIC_ASSEMBLY_SCHEMA_VERSION = 1
MUSIC_ASSEMBLY_PATH = "timeline/music-assembly.json"
MAX_MUSIC_ASSEMBLY_BINDINGS = 512


class MusicAssemblyError(ProjectValidationError):
    """Invalid, stale, or unsafe music-video assembly state."""


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    missing = allowed.difference(data)
    if unknown:
        raise MusicAssemblyError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    if missing:
        raise MusicAssemblyError(f"{kind} is missing fields: {sorted(missing)!r}")


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise MusicAssemblyError(str(exc)) from exc


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise MusicAssemblyError(f"{field_name} must be a 64-character sha256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MusicAssemblyError(f"{field_name} must be hexadecimal sha256") from exc
    return value.lower()


def _nonnegative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MusicAssemblyError(f"{field_name} must be a non-negative integer")
    return value


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MusicAssemblyError(f"{field_name} must be a positive integer")
    return value


def _canonical_sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_identity(metadata: Mapping[str, Any]) -> tuple[str, int, int]:
    sha = _sha256(metadata.get("sha256"), field_name="source sha256")
    size = _positive_int(metadata.get("size_bytes"), field_name="source size_bytes")
    duration = _positive_int(metadata.get("duration_us"), field_name="source duration_us")
    return sha, size, duration


@dataclass(frozen=True)
class MusicVisualAssignment:
    shot_id: str
    source_id: str
    source_start_us: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="music assembly shot_id"))
        object.__setattr__(self, "source_id", _identifier(self.source_id, field_name="music assembly source_id"))
        object.__setattr__(
            self,
            "source_start_us",
            _nonnegative_int(self.source_start_us, field_name="music assembly source_start_us"),
        )


@dataclass(frozen=True)
class MusicVisualBinding:
    shot_id: str
    source_id: str
    source_path: str
    source_sha256: str
    source_size_bytes: int
    source_start_us: int
    source_end_us: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="music binding shot_id"))
        object.__setattr__(self, "source_id", _identifier(self.source_id, field_name="music binding source_id"))
        try:
            path = validate_project_relative_path(self.source_path)
        except ProjectValidationError as exc:
            raise MusicAssemblyError(str(exc)) from exc
        if not path.startswith("sources/"):
            raise MusicAssemblyError("music binding source_path must stay under sources/")
        object.__setattr__(self, "source_path", path)
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, field_name="music binding source_sha256"))
        object.__setattr__(
            self,
            "source_size_bytes",
            _positive_int(self.source_size_bytes, field_name="music binding source_size_bytes"),
        )
        object.__setattr__(
            self,
            "source_start_us",
            _nonnegative_int(self.source_start_us, field_name="music binding source_start_us"),
        )
        object.__setattr__(
            self,
            "source_end_us",
            _positive_int(self.source_end_us, field_name="music binding source_end_us"),
        )
        if self.source_end_us <= self.source_start_us:
            raise MusicAssemblyError("music binding source_end_us must be greater than source_start_us")

    def to_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "source_size_bytes": self.source_size_bytes,
            "source_start_us": self.source_start_us,
            "source_end_us": self.source_end_us,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicVisualBinding":
        if not isinstance(data, Mapping):
            raise MusicAssemblyError("music visual binding must be an object")
        allowed = {
            "shot_id",
            "source_id",
            "source_path",
            "source_sha256",
            "source_size_bytes",
            "source_start_us",
            "source_end_us",
        }
        _strict_fields(data, allowed=allowed, kind="music visual binding")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MusicAssemblyState:
    music_direction_revision_sha256: str
    bindings: tuple[MusicVisualBinding, ...]
    schema_version: int = MUSIC_ASSEMBLY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != MUSIC_ASSEMBLY_SCHEMA_VERSION
        ):
            raise MusicAssemblyError(f"unsupported music-assembly schema: {self.schema_version!r}")
        object.__setattr__(
            self,
            "music_direction_revision_sha256",
            _sha256(
                self.music_direction_revision_sha256,
                field_name="music_direction_revision_sha256",
            ),
        )
        bindings = tuple(self.bindings)
        if not bindings:
            raise MusicAssemblyError("music assembly requires at least one visual binding")
        if len(bindings) > MAX_MUSIC_ASSEMBLY_BINDINGS:
            raise MusicAssemblyError(
                f"music assembly may contain at most {MAX_MUSIC_ASSEMBLY_BINDINGS} bindings"
            )
        if not all(isinstance(item, MusicVisualBinding) for item in bindings):
            raise MusicAssemblyError("music assembly bindings contain invalid values")
        ids = [item.shot_id for item in bindings]
        if len(ids) != len(set(ids)):
            raise MusicAssemblyError("music assembly must bind each shot exactly once")
        object.__setattr__(self, "bindings", bindings)

    def identity_dict(self) -> dict[str, Any]:
        return {
            "music_direction_revision_sha256": self.music_direction_revision_sha256,
            "bindings": [item.to_dict() for item in self.bindings],
        }

    @property
    def revision_sha256(self) -> str:
        return _canonical_sha(self.identity_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            **self.identity_dict(),
            "revision_sha256": self.revision_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicAssemblyState":
        if not isinstance(data, Mapping):
            raise MusicAssemblyError("music assembly must be an object")
        allowed = {
            "schema_version",
            "music_direction_revision_sha256",
            "bindings",
            "revision_sha256",
        }
        _strict_fields(data, allowed=allowed, kind="music assembly")
        if not isinstance(data["bindings"], list):
            raise MusicAssemblyError("music assembly bindings must be a list")
        value = cls(
            schema_version=data["schema_version"],
            music_direction_revision_sha256=data["music_direction_revision_sha256"],
            bindings=tuple(MusicVisualBinding.from_dict(item) for item in data["bindings"]),
        )
        if _sha256(data["revision_sha256"], field_name="revision_sha256") != value.revision_sha256:
            raise MusicAssemblyError("stored music-assembly revision does not match plan contents")
        return value


class MusicAssemblyStore:
    """Atomic visual bindings for one exact current Music Director revision."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.directions = MusicDirectionStore(project_store)
        self.sources = ProjectSourceMediaStore(project_store)

    def _path(self, project_id: str):
        return self.project_store.resolve_project_file(
            project_id, MUSIC_ASSEMBLY_PATH, allowed_roots=("timeline",)
        )

    def load(self, project_id: str, *, validate_current: bool = False) -> MusicAssemblyState | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            state = MusicAssemblyState.from_dict(raw)
        except MusicAssemblyError:
            raise
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise MusicAssemblyError(f"invalid music-assembly state: {path}: {exc}") from exc
        if validate_current:
            self.validate_current(project_id, state)
        return state

    def set_assembly(
        self,
        project_id: str,
        *,
        music_direction_revision_sha256: str,
        assignments: tuple[MusicVisualAssignment, ...],
    ) -> MusicAssemblyState:
        with self.project_store._lock:
            project = self.project_store.load_project(project_id)
            if compatibility_recipe_id(project) != "music_video":
                raise MusicAssemblyError("music assembly is only valid for the music_video recipe")
            direction = self.directions.load(project_id, validate_current=True)
            if direction is None:
                raise MusicAssemblyError("music assembly requires a current Music Director plan")
            expected_revision = _sha256(
                music_direction_revision_sha256,
                field_name="music_direction_revision_sha256",
            )
            if expected_revision != direction.revision_sha256:
                raise MusicAssemblyError(
                    "music assembly was prepared against a stale Music Director revision"
                )
            assignment_by_shot: dict[str, MusicVisualAssignment] = {}
            for assignment in assignments:
                if not isinstance(assignment, MusicVisualAssignment):
                    raise MusicAssemblyError("music assembly assignments contain invalid values")
                if assignment.shot_id in assignment_by_shot:
                    raise MusicAssemblyError("music assembly assigns a shot more than once")
                assignment_by_shot[assignment.shot_id] = assignment
            expected_ids = [shot.shot_id for shot in direction.shots]
            if set(assignment_by_shot) != set(expected_ids):
                raise MusicAssemblyError(
                    "music assembly must assign exactly every current Music Director shot"
                )

            bindings: list[MusicVisualBinding] = []
            for shot in direction.shots:
                assignment = assignment_by_shot[shot.shot_id]
                try:
                    reference, _ = self.sources.resolve_verified(
                        project_id, assignment.source_id, expected_kind="video"
                    )
                except (SourceMediaError, SourceMediaNotFound) as exc:
                    raise MusicAssemblyError(str(exc)) from exc
                sha, size, source_duration = _source_identity(reference.metadata)
                shot_duration = shot.end_us - shot.start_us
                source_end_us = assignment.source_start_us + shot_duration
                if source_end_us > source_duration:
                    raise MusicAssemblyError(
                        f"video source {assignment.source_id!r} is too short for shot {shot.shot_id!r}"
                    )
                bindings.append(
                    MusicVisualBinding(
                        shot_id=shot.shot_id,
                        source_id=reference.id,
                        source_path=reference.path,
                        source_sha256=sha,
                        source_size_bytes=size,
                        source_start_us=assignment.source_start_us,
                        source_end_us=source_end_us,
                    )
                )
            state = MusicAssemblyState(
                music_direction_revision_sha256=direction.revision_sha256,
                bindings=tuple(bindings),
            )
            self._save(project_id, state)
            return state

    def clear(self, project_id: str) -> None:
        with self.project_store._lock:
            try:
                self._path(project_id).unlink(missing_ok=True)
            except OSError as exc:
                raise ProjectStoreError("could not remove music-assembly state") from exc

    def validate_current(
        self, project_id: str, state: MusicAssemblyState | None = None
    ) -> None:
        state = state if state is not None else self.load(project_id)
        if state is None:
            return
        project = self.project_store.load_project(project_id)
        if compatibility_recipe_id(project) != "music_video":
            raise MusicAssemblyError("music assembly is only valid for the music_video recipe")
        try:
            direction = self.directions.load(project_id, validate_current=True)
        except MusicDirectionError as exc:
            raise MusicAssemblyError(str(exc)) from exc
        if direction is None:
            raise MusicAssemblyError("music assembly has no current Music Director plan")
        if state.music_direction_revision_sha256 != direction.revision_sha256:
            raise MusicAssemblyError("music assembly is stale for the current Music Director revision")
        expected_ids = [shot.shot_id for shot in direction.shots]
        if [item.shot_id for item in state.bindings] != expected_ids:
            raise MusicAssemblyError("music assembly no longer matches current Music Director shot order")
        shot_by_id = {shot.shot_id: shot for shot in direction.shots}
        for binding in state.bindings:
            try:
                reference, _ = self.sources.resolve_verified(
                    project_id, binding.source_id, expected_kind="video"
                )
            except (SourceMediaError, SourceMediaNotFound) as exc:
                raise MusicAssemblyError(str(exc)) from exc
            sha, size, duration = _source_identity(reference.metadata)
            if reference.path != binding.source_path:
                raise MusicAssemblyError("music assembly source path no longer matches its binding")
            if sha != binding.source_sha256 or size != binding.source_size_bytes:
                raise MusicAssemblyError("music assembly source bytes no longer match their binding")
            shot = shot_by_id[binding.shot_id]
            if binding.source_end_us - binding.source_start_us != shot.end_us - shot.start_us:
                raise MusicAssemblyError("music assembly source interval no longer matches shot duration")
            if binding.source_end_us > duration:
                raise MusicAssemblyError("music assembly source interval exceeds current source duration")

    def _save(self, project_id: str, state: MusicAssemblyState) -> None:
        try:
            self.project_store._atomic_write_json(self._path(project_id), state.to_dict())
        except OSError as exc:
            raise ProjectStoreError("could not persist music-assembly state") from exc
