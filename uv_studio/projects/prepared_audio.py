"""Project-owned prepared speech audio for dubbing workflows."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .models import ProjectDocument, ProjectReference, ProjectValidationError
from .source_media import SourceMediaError, normalize_original_filename
from .store import ProjectNotFound, ProjectStore, ProjectStoreError

_SAFE_EXTENSION_RE = re.compile(r"^\.[A-Za-z0-9]{1,16}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PREPARED_SPEECH_ROLE = "prepared-speech"
_ALLOWED_ORIGINS = frozenset({"imported", "recorded", "tts"})


class PreparedAudioError(ProjectValidationError):
    """Invalid or inconsistent project-owned prepared speech media."""


class PreparedAudioNotFound(PreparedAudioError):
    pass


def _original_name(value: str) -> str:
    try:
        return normalize_original_filename(value)
    except SourceMediaError as exc:
        raise PreparedAudioError(str(exc).replace("source filename", "audio filename")) from exc


def _portable_extension(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    return suffix if _SAFE_EXTENSION_RE.fullmatch(suffix) else ""


def _required_sha256(metadata: Mapping[str, Any]) -> str:
    value = metadata.get("sha256")
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise PreparedAudioError("prepared audio metadata requires lowercase sha256")
    return value


def _required_duration_us(metadata: Mapping[str, Any]) -> int:
    value = metadata.get("duration_us")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PreparedAudioError("prepared audio metadata requires positive duration_us")
    return value


def _required_size_bytes(metadata: Mapping[str, Any]) -> int:
    value = metadata.get("size_bytes")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PreparedAudioError("prepared audio metadata requires positive size_bytes")
    return value


def _origin(value: Any) -> str:
    if value not in _ALLOWED_ORIGINS:
        raise PreparedAudioError(f"prepared audio origin must be one of {sorted(_ALLOWED_ORIGINS)!r}")
    return str(value)


@dataclass(frozen=True)
class AllocatedPreparedAudio:
    audio_id: str
    relative_path: str
    absolute_path: Path
    original_name: str


class ProjectPreparedAudioStore:
    """Own prepared speech audio identity under the canonical project assets root."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def allocate(self, project_id: str, original_filename: str) -> AllocatedPreparedAudio:
        original_name = _original_name(original_filename)
        self.project_store.load_project(project_id)
        audio_id = f"aud_{uuid.uuid4().hex}"
        relative_path = f"assets/{audio_id}{_portable_extension(original_name)}"
        try:
            absolute_path = self.project_store.resolve_project_file(
                project_id,
                relative_path,
                must_exist=False,
                allowed_roots=("assets",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise PreparedAudioError(str(exc)) from exc
        if absolute_path.exists() or absolute_path.is_symlink():
            raise PreparedAudioError("allocated prepared audio path already exists")
        return AllocatedPreparedAudio(
            audio_id=audio_id,
            relative_path=relative_path,
            absolute_path=absolute_path,
            original_name=original_name,
        )

    def register(
        self,
        project_id: str,
        allocation: AllocatedPreparedAudio,
        *,
        metadata: Mapping[str, Any],
    ) -> ProjectDocument:
        if not isinstance(allocation, AllocatedPreparedAudio):
            raise PreparedAudioError("allocation must be AllocatedPreparedAudio")
        if not allocation.absolute_path.is_file() or allocation.absolute_path.is_symlink():
            raise PreparedAudioError(
                "prepared audio must exist as a regular project file before registration"
            )
        if not isinstance(metadata, Mapping):
            raise PreparedAudioError("prepared audio metadata must be an object")
        portable = dict(metadata)
        _required_sha256(portable)
        _required_duration_us(portable)
        _required_size_bytes(portable)
        if portable.get("has_audio") is not True:
            raise PreparedAudioError("prepared audio metadata must declare has_audio=true")
        if portable.get("has_video") is True:
            raise PreparedAudioError("prepared speech asset must not contain a video stream")
        portable["origin"] = _origin(portable.get("origin"))
        portable["role"] = _PREPARED_SPEECH_ROLE

        reference = ProjectReference(
            id=allocation.audio_id,
            kind="audio",
            path=allocation.relative_path,
            metadata=portable,
        )
        with self.project_store._lock:
            project = self.project_store.load_project(project_id)
            if any(item.id == reference.id for item in (*project.sources, *project.artifacts)):
                raise PreparedAudioError(f"duplicate prepared audio reference id: {reference.id}")
            return self.project_store.update_project(
                project_id,
                artifacts=project.artifacts + (reference,),
            )

    def get(self, project_id: str, audio_id: str) -> ProjectReference:
        try:
            project = self.project_store.load_project(project_id)
        except (ProjectNotFound, ProjectStoreError):
            raise
        for reference in project.artifacts:
            if reference.id != audio_id:
                continue
            if reference.kind != "audio" or reference.metadata.get("role") != _PREPARED_SPEECH_ROLE:
                raise PreparedAudioError(
                    f"artifact reference {audio_id!r} is not registered as prepared speech audio"
                )
            if not reference.path.startswith("assets/"):
                raise PreparedAudioError("prepared speech audio escaped the assets root")
            _required_sha256(reference.metadata)
            _required_duration_us(reference.metadata)
            return reference
        raise PreparedAudioNotFound(audio_id)

    def resolve(self, project_id: str, audio_id: str) -> tuple[ProjectReference, Path]:
        reference = self.get(project_id, audio_id)
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                reference.path,
                must_exist=True,
                allowed_roots=("assets",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise PreparedAudioError(str(exc)) from exc
        if not path.is_file() or path.is_symlink():
            raise PreparedAudioError("registered prepared audio is not a regular project file")
        return reference, path

    def validate_reference(self, project_id: str, audio_id: str) -> ProjectReference:
        reference, _path = self.resolve(project_id, audio_id)
        return reference
