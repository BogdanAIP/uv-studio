"""Evidence-bound final review gate for Stage 7 Music Video Mode."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .media_integrity import MediaIntegrityError, verify_registered_media_bytes
from .models import ProjectValidationError, compatibility_recipe_id, validate_identifier
from .music_assembly import MusicAssemblyError, MusicAssemblyStore
from .music_direction import MusicDirectionError, MusicDirectionStore
from .music_map import MusicMapError, MusicMapStore
from .store import ProjectStore, ProjectStoreError

MUSIC_VIDEO_REVIEW_SCHEMA_VERSION = 1
MUSIC_VIDEO_REVIEW_PATH = "reviews/music-video-review.json"
MUSIC_VIDEO_RELEASE_MIN_DURATION_US = 20_000_000
MUSIC_VIDEO_RELEASE_MAX_DURATION_US = 30_000_000
_EXPECTED_CAPABILITY_ID = "video.render_music_video"
_EXPECTED_COMPOSITION_MODE = "music_assembly_visual_concat_with_exact_master_song_excerpt"
_RENDER_DURATION_TOLERANCE_US = 180_000
_VERDICTS = frozenset({"approved", "needs_revision", "rejected"})
_OUTCOMES = frozenset({"pass", "fail", "uncertain"})


class MusicVideoReviewError(ProjectValidationError):
    """Invalid, stale or insufficient final Music Video review evidence."""


def _sha(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise MusicVideoReviewError(f"{field} must be a 64-character sha256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MusicVideoReviewError(f"{field} must be hexadecimal sha256") from exc
    return value.lower()


def _identifier(value: Any, *, field: str) -> str:
    try:
        return validate_identifier(value, field_name=field)
    except ProjectValidationError as exc:
        raise MusicVideoReviewError(str(exc)) from exc


def _duration(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MusicVideoReviewError(f"canonical render metadata requires positive {field}")
    return value


@dataclass(frozen=True)
class MusicVideoReview:
    artifact_id: str
    artifact_path: str
    artifact_sha256: str
    music_map_revision_sha256: str
    music_direction_revision_sha256: str
    music_assembly_revision_sha256: str
    verdict: str
    transition_outcome: str
    evidence: dict[str, Any]
    note: str | None = None
    schema_version: int = MUSIC_VIDEO_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MUSIC_VIDEO_REVIEW_SCHEMA_VERSION:
            raise MusicVideoReviewError("unsupported Music Video review schema")
        object.__setattr__(self, "artifact_id", _identifier(self.artifact_id, field="artifact_id"))
        if not isinstance(self.artifact_path, str) or not self.artifact_path.startswith("artifacts/"):
            raise MusicVideoReviewError("review artifact_path must stay under artifacts/")
        object.__setattr__(self, "artifact_sha256", _sha(self.artifact_sha256, field="artifact_sha256"))
        for field in (
            "music_map_revision_sha256", "music_direction_revision_sha256", "music_assembly_revision_sha256"
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))
        if self.verdict not in _VERDICTS:
            raise MusicVideoReviewError("invalid Music Video review verdict")
        if self.transition_outcome not in _OUTCOMES:
            raise MusicVideoReviewError("invalid transition review outcome")
        if not isinstance(self.evidence, dict):
            raise MusicVideoReviewError("review evidence must be an object")
        if self.note is not None:
            if not isinstance(self.note, str) or not self.note.strip() or len(self.note.strip()) > 4000:
                raise MusicVideoReviewError("review note must be non-empty <= 4000 chars or null")
            object.__setattr__(self, "note", self.note.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "artifact_path": self.artifact_path,
            "artifact_sha256": self.artifact_sha256,
            "music_map_revision_sha256": self.music_map_revision_sha256,
            "music_direction_revision_sha256": self.music_direction_revision_sha256,
            "music_assembly_revision_sha256": self.music_assembly_revision_sha256,
            "verdict": self.verdict,
            "transition_outcome": self.transition_outcome,
            "evidence": self.evidence,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicVideoReview":
        if not isinstance(data, Mapping):
            raise MusicVideoReviewError("Music Video review must be an object")
        allowed = {
            "schema_version", "artifact_id", "artifact_path", "artifact_sha256",
            "music_map_revision_sha256", "music_direction_revision_sha256",
            "music_assembly_revision_sha256", "verdict", "transition_outcome", "evidence", "note",
        }
        if set(data) != allowed:
            raise MusicVideoReviewError("Music Video review fields do not match schema")
        return cls(**{key: data[key] for key in allowed})


class MusicVideoReviewStore:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.maps = MusicMapStore(store)
        self.directions = MusicDirectionStore(store)
        self.assemblies = MusicAssemblyStore(store)

    def _path(self, project_id: str):
        return self.store.resolve_project_file(
            project_id, MUSIC_VIDEO_REVIEW_PATH, allowed_roots=("reviews",)
        )

    def load(self, project_id: str, *, validate_current: bool = False) -> MusicVideoReview | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        try:
            review = MusicVideoReview.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except MusicVideoReviewError:
            raise
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise MusicVideoReviewError(f"invalid Music Video review state: {exc}") from exc
        if validate_current:
            self._current_evidence(project_id, review.artifact_id, expected=review)
        return review

    def review(
        self,
        project_id: str,
        *,
        artifact_id: str,
        verdict: str,
        transition_outcome: str,
        note: str | None = None,
    ) -> MusicVideoReview:
        if verdict not in _VERDICTS:
            raise MusicVideoReviewError("invalid Music Video review verdict")
        if transition_outcome not in _OUTCOMES:
            raise MusicVideoReviewError("invalid transition review outcome")
        with self.store._lock:
            evidence = self._current_evidence(project_id, artifact_id)
            required_pass = (
                evidence["release_duration"]["outcome"] == "pass"
                and evidence["rhythm_alignment"]["outcome"] == "pass"
                and evidence["master_audio_binding"]["outcome"] == "pass"
                and evidence["visual_assembly_binding"]["outcome"] == "pass"
                and evidence["render_output_binding"]["outcome"] == "pass"
                and transition_outcome == "pass"
            )
            if verdict == "approved" and not required_pass:
                raise MusicVideoReviewError(
                    "approved Music Video review requires 20–30 s duration, aligned rhythm, exact master/assembly/render bindings and passing transition review"
                )
            review = MusicVideoReview(
                artifact_id=evidence["binding"]["artifact_id"],
                artifact_path=evidence["binding"]["artifact_path"],
                artifact_sha256=evidence["binding"]["artifact_sha256"],
                music_map_revision_sha256=evidence["binding"]["music_map_revision_sha256"],
                music_direction_revision_sha256=evidence["binding"]["music_direction_revision_sha256"],
                music_assembly_revision_sha256=evidence["binding"]["music_assembly_revision_sha256"],
                verdict=verdict,
                transition_outcome=transition_outcome,
                evidence=evidence,
                note=note,
            )
            try:
                self.store._atomic_write_json(self._path(project_id), review.to_dict())
            except OSError as exc:
                raise ProjectStoreError("could not persist Music Video review") from exc
            return review

    def _current_evidence(
        self,
        project_id: str,
        artifact_id: str,
        *,
        expected: MusicVideoReview | None = None,
    ) -> dict[str, Any]:
        project = self.store.load_project(project_id)
        if compatibility_recipe_id(project) != "music_video":
            raise MusicVideoReviewError("final Music Video review is only valid for music_video")
        music_map = self.maps.load(project_id, validate_current=True)
        direction = self.directions.load(project_id, validate_current=True)
        assembly = self.assemblies.load(project_id, validate_current=True)
        if music_map is None or direction is None or assembly is None:
            raise MusicVideoReviewError("final review requires current Music Map, Director and Assembly")
        artifact_id = _identifier(artifact_id, field="artifact_id")
        matches = [item for item in project.artifacts if item.id == artifact_id and item.kind == "video"]
        if len(matches) != 1:
            raise MusicVideoReviewError("final review requires exactly one registered video artifact")
        artifact = matches[0]
        metadata = artifact.metadata
        if metadata.get("lifecycle") != "music_video_render":
            raise MusicVideoReviewError("final review accepts only canonical music_video_render artifacts")
        if metadata.get("capability_id") != _EXPECTED_CAPABILITY_ID:
            raise MusicVideoReviewError("final review artifact was not produced by video.render_music_video")
        if metadata.get("composition_mode") != _EXPECTED_COMPOSITION_MODE:
            raise MusicVideoReviewError("final review artifact has an unexpected Music Video composition mode")
        path = self.store.resolve_project_file(
            project_id, artifact.path, must_exist=True, allowed_roots=("artifacts",)
        )
        try:
            identity = verify_registered_media_bytes(path, metadata)
        except MediaIntegrityError as exc:
            raise MusicVideoReviewError(str(exc)) from exc
        binding = {
            "artifact_id": artifact.id,
            "artifact_path": artifact.path,
            "artifact_sha256": identity.sha256,
            "music_map_revision_sha256": music_map.revision_sha256,
            "music_direction_revision_sha256": direction.revision_sha256,
            "music_assembly_revision_sha256": assembly.revision_sha256,
        }
        if metadata.get("music_map_revision_sha256") != music_map.revision_sha256:
            raise MusicVideoReviewError("render artifact is stale for current Music Map")
        if metadata.get("music_direction_revision_sha256") != direction.revision_sha256:
            raise MusicVideoReviewError("render artifact is stale for current Music Director")
        if metadata.get("music_assembly_revision_sha256") != assembly.revision_sha256:
            raise MusicVideoReviewError("render artifact is stale for current Music Assembly")
        if metadata.get("song_reference_id") != music_map.song.reference_id:
            raise MusicVideoReviewError("render artifact master-song reference is stale")
        if metadata.get("song_sha256") != music_map.song.sha256:
            raise MusicVideoReviewError("render artifact master-song binding is stale")
        if metadata.get("song_excerpt") != music_map.excerpt.to_dict():
            raise MusicVideoReviewError("render artifact excerpt no longer matches current Music Map")
        if metadata.get("visual_bindings") != [item.to_dict() for item in assembly.bindings]:
            raise MusicVideoReviewError("render artifact visual bindings no longer match current Music Assembly")
        video_duration_us = _duration(
            metadata.get("actual_output_video_duration_us"), field="actual_output_video_duration_us"
        )
        audio_duration_us = _duration(
            metadata.get("actual_output_audio_duration_us"), field="actual_output_audio_duration_us"
        )
        expected_duration_us = music_map.excerpt.duration_us
        if abs(video_duration_us - expected_duration_us) > _RENDER_DURATION_TOLERANCE_US:
            raise MusicVideoReviewError("render artifact video duration no longer matches current excerpt")
        if abs(audio_duration_us - expected_duration_us) > _RENDER_DURATION_TOLERANCE_US:
            raise MusicVideoReviewError("render artifact audio duration no longer matches current excerpt")
        if expected is not None:
            expected_binding = {
                "artifact_id": expected.artifact_id,
                "artifact_path": expected.artifact_path,
                "artifact_sha256": expected.artifact_sha256,
                "music_map_revision_sha256": expected.music_map_revision_sha256,
                "music_direction_revision_sha256": expected.music_direction_revision_sha256,
                "music_assembly_revision_sha256": expected.music_assembly_revision_sha256,
            }
            if binding != expected_binding:
                raise MusicVideoReviewError("stored Music Video review is stale for current project state")
        rhythm = self.directions.rhythm_audit(project_id)
        return {
            "binding": binding,
            "release_duration": {
                "outcome": "pass" if MUSIC_VIDEO_RELEASE_MIN_DURATION_US <= expected_duration_us <= MUSIC_VIDEO_RELEASE_MAX_DURATION_US else "fail",
                "duration_us": expected_duration_us,
                "required_min_us": MUSIC_VIDEO_RELEASE_MIN_DURATION_US,
                "required_max_us": MUSIC_VIDEO_RELEASE_MAX_DURATION_US,
            },
            "rhythm_alignment": {
                "outcome": "pass" if rhythm["summary"]["all_aligned"] else "fail",
                "summary": rhythm["summary"],
                "tolerance_us": rhythm["tolerance_us"],
            },
            "master_audio_binding": {
                "outcome": "pass",
                "song_reference_id": music_map.song.reference_id,
                "song_sha256": music_map.song.sha256,
                "excerpt": music_map.excerpt.to_dict(),
            },
            "visual_assembly_binding": {
                "outcome": "pass",
                "binding_count": len(assembly.bindings),
                "shot_ids": [item.shot_id for item in assembly.bindings],
            },
            "render_output_binding": {
                "outcome": "pass",
                "capability_id": _EXPECTED_CAPABILITY_ID,
                "composition_mode": _EXPECTED_COMPOSITION_MODE,
                "actual_output_video_duration_us": video_duration_us,
                "actual_output_audio_duration_us": audio_duration_us,
            },
        }
