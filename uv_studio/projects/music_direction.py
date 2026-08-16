"""Provider-neutral music-direction timing plan and deterministic rhythm audit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .models import ProjectValidationError, validate_identifier
from .music_map import MusicMapError, MusicMapState, MusicMapStore
from .store import ProjectStore, ProjectStoreError

MUSIC_DIRECTION_SCHEMA_VERSION = 1
MUSIC_DIRECTION_PATH = "timeline/music-direction.json"
MAX_MUSIC_SHOTS = 512
MAX_SYNC_MARKERS_PER_SHOT = 32
MAX_RHYTHM_AUDIT_TOLERANCE_US = 1_000_000
DEFAULT_RHYTHM_AUDIT_TOLERANCE_US = 120_000
_TRANSITIONS = frozenset({"cut", "dissolve", "fade", "match_cut", "other"})


class MusicDirectionError(ProjectValidationError):
    """Invalid, stale, or unsafe music-direction state."""


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    missing = allowed.difference(data)
    if unknown:
        raise MusicDirectionError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    if missing:
        raise MusicDirectionError(f"{kind} is missing fields: {sorted(missing)!r}")


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise MusicDirectionError(str(exc)) from exc


def _text(value: Any, *, field_name: str, maximum: int = 4000) -> str:
    if not isinstance(value, str):
        raise MusicDirectionError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise MusicDirectionError(f"{field_name} must not be empty")
    if len(normalized) > maximum:
        raise MusicDirectionError(f"{field_name} must be <= {maximum} characters")
    return normalized


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise MusicDirectionError(f"{field_name} must be a 64-character sha256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MusicDirectionError(f"{field_name} must be hexadecimal sha256") from exc
    return value.lower()


def _nonnegative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MusicDirectionError(f"{field_name} must be a non-negative integer")
    return value


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MusicDirectionError(f"{field_name} must be a positive integer")
    return value


def _canonical_sha(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True)
class MusicShotPlan:
    shot_id: str
    order: int
    start_us: int
    end_us: int
    intent: str
    sync_marker_ids: tuple[str, ...] = ()
    transition_out: str = "cut"

    def __post_init__(self) -> None:
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="music shot_id"))
        object.__setattr__(self, "order", _nonnegative_int(self.order, field_name="music shot order"))
        object.__setattr__(
            self, "start_us", _nonnegative_int(self.start_us, field_name="music shot start_us")
        )
        object.__setattr__(self, "end_us", _positive_int(self.end_us, field_name="music shot end_us"))
        if self.end_us <= self.start_us:
            raise MusicDirectionError("music shot end_us must be greater than start_us")
        object.__setattr__(self, "intent", _text(self.intent, field_name="music shot intent"))
        marker_ids = tuple(
            _identifier(item, field_name="music shot sync_marker_id") for item in self.sync_marker_ids
        )
        if len(marker_ids) > MAX_SYNC_MARKERS_PER_SHOT:
            raise MusicDirectionError(
                f"music shot sync_marker_ids must contain at most {MAX_SYNC_MARKERS_PER_SHOT} items"
            )
        if len(marker_ids) != len(set(marker_ids)):
            raise MusicDirectionError("music shot sync_marker_ids must be unique")
        if not isinstance(self.transition_out, str) or self.transition_out not in _TRANSITIONS:
            raise MusicDirectionError(
                f"music shot transition_out must be one of {sorted(_TRANSITIONS)!r}"
            )
        object.__setattr__(self, "sync_marker_ids", marker_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "order": self.order,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "intent": self.intent,
            "sync_marker_ids": list(self.sync_marker_ids),
            "transition_out": self.transition_out,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicShotPlan":
        if not isinstance(data, Mapping):
            raise MusicDirectionError("music shot plan must be an object")
        allowed = {
            "shot_id",
            "order",
            "start_us",
            "end_us",
            "intent",
            "sync_marker_ids",
            "transition_out",
        }
        _strict_fields(data, allowed=allowed, kind="music shot plan")
        if not isinstance(data["sync_marker_ids"], list):
            raise MusicDirectionError("music shot sync_marker_ids must be a list")
        return cls(
            shot_id=data["shot_id"],
            order=data["order"],
            start_us=data["start_us"],
            end_us=data["end_us"],
            intent=data["intent"],
            sync_marker_ids=tuple(data["sync_marker_ids"]),
            transition_out=data["transition_out"],
        )


@dataclass(frozen=True)
class MusicDirectionState:
    music_map_revision_sha256: str
    shots: tuple[MusicShotPlan, ...]
    schema_version: int = MUSIC_DIRECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != MUSIC_DIRECTION_SCHEMA_VERSION
        ):
            raise MusicDirectionError(
                f"unsupported music-direction schema: {self.schema_version!r}"
            )
        object.__setattr__(
            self,
            "music_map_revision_sha256",
            _sha256(self.music_map_revision_sha256, field_name="music_map_revision_sha256"),
        )
        shots = tuple(sorted(self.shots, key=lambda item: item.order))
        if not shots:
            raise MusicDirectionError("music direction requires at least one shot")
        if len(shots) > MAX_MUSIC_SHOTS:
            raise MusicDirectionError(f"music direction may contain at most {MAX_MUSIC_SHOTS} shots")
        if not all(isinstance(item, MusicShotPlan) for item in shots):
            raise MusicDirectionError("music direction shots contain invalid values")
        ids = [item.shot_id for item in shots]
        if len(ids) != len(set(ids)):
            raise MusicDirectionError("music direction shot IDs must be unique")
        orders = [item.order for item in shots]
        if orders != list(range(len(shots))):
            raise MusicDirectionError("music direction shot order must be contiguous from zero")
        for previous, current in zip(shots, shots[1:]):
            if previous.end_us != current.start_us:
                raise MusicDirectionError("music direction shots must form one contiguous timeline")
        all_sync_ids = [marker_id for shot in shots for marker_id in shot.sync_marker_ids]
        if len(all_sync_ids) != len(set(all_sync_ids)):
            raise MusicDirectionError("a music sync marker may be assigned to at most one shot")
        object.__setattr__(self, "shots", shots)

    def identity_dict(self) -> dict[str, Any]:
        return {
            "music_map_revision_sha256": self.music_map_revision_sha256,
            "shots": [item.to_dict() for item in self.shots],
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
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicDirectionState":
        if not isinstance(data, Mapping):
            raise MusicDirectionError("music direction must be an object")
        allowed = {
            "schema_version",
            "music_map_revision_sha256",
            "shots",
            "revision_sha256",
        }
        _strict_fields(data, allowed=allowed, kind="music direction")
        if not isinstance(data["shots"], list):
            raise MusicDirectionError("music direction shots must be a list")
        value = cls(
            schema_version=data["schema_version"],
            music_map_revision_sha256=data["music_map_revision_sha256"],
            shots=tuple(MusicShotPlan.from_dict(item) for item in data["shots"]),
        )
        if _sha256(data["revision_sha256"], field_name="revision_sha256") != value.revision_sha256:
            raise MusicDirectionError("stored music-direction revision does not match plan contents")
        return value


@dataclass(frozen=True)
class RhythmAuditTarget:
    target_id: str
    kind: str
    time_us: int

    def to_dict(self) -> dict[str, Any]:
        return {"target_id": self.target_id, "kind": self.kind, "time_us": self.time_us}


class MusicDirectionStore:
    """Atomic project-owned music direction state bound to one exact Music Map revision."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.music_maps = MusicMapStore(project_store)

    def _path(self, project_id: str):
        return self.project_store.resolve_project_file(
            project_id, MUSIC_DIRECTION_PATH, allowed_roots=("timeline",)
        )

    def load(
        self, project_id: str, *, validate_current: bool = False
    ) -> MusicDirectionState | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            state = MusicDirectionState.from_dict(raw)
        except MusicDirectionError:
            raise
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise MusicDirectionError(f"invalid music-direction state: {path}: {exc}") from exc
        if validate_current:
            self.validate_current(project_id, state)
        return state

    def set_direction(
        self,
        project_id: str,
        *,
        music_map_revision_sha256: str,
        shots: tuple[MusicShotPlan, ...],
    ) -> MusicDirectionState:
        with self.project_store._lock:
            music_map = self.music_maps.load(project_id, validate_current=True)
            if music_map is None:
                raise MusicDirectionError("music direction requires a current Music Map")
            expected = _sha256(
                music_map_revision_sha256, field_name="music_map_revision_sha256"
            )
            if expected != music_map.revision_sha256:
                raise MusicDirectionError(
                    "music direction was prepared against a stale Music Map revision"
                )
            state = MusicDirectionState(
                music_map_revision_sha256=music_map.revision_sha256,
                shots=shots,
            )
            self._validate_against_map(state, music_map)
            self._save(project_id, state)
            return state

    def clear(self, project_id: str) -> None:
        with self.project_store._lock:
            path = self._path(project_id)
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise ProjectStoreError("could not remove music-direction state") from exc

    def validate_current(
        self, project_id: str, state: MusicDirectionState | None = None
    ) -> None:
        state = state if state is not None else self.load(project_id)
        if state is None:
            return
        music_map = self.music_maps.load(project_id, validate_current=True)
        if music_map is None:
            raise MusicDirectionError("music direction has no current Music Map")
        if state.music_map_revision_sha256 != music_map.revision_sha256:
            raise MusicDirectionError("music direction is stale for the current Music Map revision")
        self._validate_against_map(state, music_map)

    def rhythm_audit(
        self,
        project_id: str,
        *,
        tolerance_us: int = DEFAULT_RHYTHM_AUDIT_TOLERANCE_US,
    ) -> dict[str, Any]:
        if (
            isinstance(tolerance_us, bool)
            or not isinstance(tolerance_us, int)
            or tolerance_us < 0
            or tolerance_us > MAX_RHYTHM_AUDIT_TOLERANCE_US
        ):
            raise MusicDirectionError(
                f"tolerance_us must be an integer in [0, {MAX_RHYTHM_AUDIT_TOLERANCE_US}]"
            )
        state = self.load(project_id, validate_current=True)
        if state is None:
            raise MusicDirectionError("rhythm audit requires a current music direction")
        music_map = self.music_maps.load(project_id, validate_current=True)
        assert music_map is not None
        targets = self._audit_targets(music_map)
        marker_by_id = {item.marker_id: item for item in music_map.markers}

        cuts: list[dict[str, Any]] = []
        for shot in state.shots[:-1]:
            explicit = [
                RhythmAuditTarget(
                    target_id=marker.marker_id,
                    kind=marker.kind,
                    time_us=marker.time_us,
                )
                for marker_id in shot.sync_marker_ids
                for marker in (marker_by_id[marker_id],)
            ]
            candidates = explicit or targets
            target = min(
                candidates,
                key=lambda item: (abs(shot.end_us - item.time_us), item.time_us, item.target_id),
            ) if candidates else None
            if target is None:
                cuts.append(
                    {
                        "shot_id": shot.shot_id,
                        "cut_time_us": shot.end_us,
                        "target": None,
                        "delta_us": None,
                        "abs_delta_us": None,
                        "aligned": False,
                    }
                )
                continue
            delta = shot.end_us - target.time_us
            cuts.append(
                {
                    "shot_id": shot.shot_id,
                    "cut_time_us": shot.end_us,
                    "target": target.to_dict(),
                    "delta_us": delta,
                    "abs_delta_us": abs(delta),
                    "aligned": abs(delta) <= tolerance_us,
                }
            )

        deltas = [item["abs_delta_us"] for item in cuts if item["abs_delta_us"] is not None]
        aligned_count = sum(1 for item in cuts if item["aligned"])
        return {
            "music_map_revision_sha256": music_map.revision_sha256,
            "music_direction_revision_sha256": state.revision_sha256,
            "tolerance_us": tolerance_us,
            "cuts": cuts,
            "summary": {
                "cut_count": len(cuts),
                "aligned_count": aligned_count,
                "unaligned_count": len(cuts) - aligned_count,
                "all_aligned": aligned_count == len(cuts),
                "max_abs_delta_us": max(deltas) if deltas else None,
            },
        }

    @staticmethod
    def _validate_against_map(state: MusicDirectionState, music_map: MusicMapState) -> None:
        shots = state.shots
        if shots[0].start_us != music_map.excerpt.start_us:
            raise MusicDirectionError("music direction must start at the selected excerpt start")
        if shots[-1].end_us != music_map.excerpt.end_us:
            raise MusicDirectionError("music direction must end at the selected excerpt end")
        marker_by_id = {item.marker_id: item for item in music_map.markers}
        for shot in shots:
            if shot.start_us < music_map.excerpt.start_us or shot.end_us > music_map.excerpt.end_us:
                raise MusicDirectionError("music direction shot must stay inside the selected excerpt")
            for marker_id in shot.sync_marker_ids:
                marker = marker_by_id.get(marker_id)
                if marker is None:
                    raise MusicDirectionError(
                        f"music direction references unknown sync marker {marker_id!r}"
                    )
                if marker.time_us < shot.start_us or marker.time_us > shot.end_us:
                    raise MusicDirectionError(
                        f"sync marker {marker_id!r} must fall within its assigned shot or boundary"
                    )

    @staticmethod
    def _audit_targets(music_map: MusicMapState) -> tuple[RhythmAuditTarget, ...]:
        targets = [
            RhythmAuditTarget(marker.marker_id, marker.kind, marker.time_us)
            for marker in music_map.markers
        ]
        for section in music_map.sections:
            if section.start_us != music_map.excerpt.start_us:
                targets.append(
                    RhythmAuditTarget(
                        f"section_{section.section_id}_start",
                        "section_boundary",
                        section.start_us,
                    )
                )
            if section.end_us != music_map.excerpt.end_us:
                targets.append(
                    RhythmAuditTarget(
                        f"section_{section.section_id}_end",
                        "section_boundary",
                        section.end_us,
                    )
                )
        deduped: dict[tuple[str, int], RhythmAuditTarget] = {}
        for target in targets:
            deduped[(target.target_id, target.time_us)] = target
        return tuple(
            sorted(deduped.values(), key=lambda item: (item.time_us, item.kind, item.target_id))
        )

    def _save(self, project_id: str, state: MusicDirectionState) -> None:
        try:
            self.project_store._atomic_write_json(self._path(project_id), state.to_dict())
        except OSError as exc:
            raise ProjectStoreError("could not persist music-direction state") from exc
