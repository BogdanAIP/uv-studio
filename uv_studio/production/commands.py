"""Shared production application commands over Stage-12 project transactions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Any

from uv_studio.production.micro_drama import (
    MICRO_DRAMA_DOCUMENT_ID,
    MICRO_DRAMA_PATH,
    MicroDramaDocument,
)
from uv_studio.production.semantics import (
    PRODUCTION_SEMANTICS_DOCUMENT_ID,
    PRODUCTION_SEMANTICS_PATH,
    ProductionSemanticError,
    ProductionSemanticsDocument,
    Scene,
    Shot,
    Take,
)
from uv_studio.projects.identity import require_modern_studio_identity
from uv_studio.projects.models import (
    ProjectDocument,
    ProjectReference,
    ProjectValidationError,
    utc_now_iso,
    validate_identifier,
)
from uv_studio.projects.production_state import (
    ProductionDocumentNotFound,
    ProductionDocumentStore,
)
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore, ProjectStoreError
from uv_studio.projects.timeline import (
    MAIN_TIMELINE_PATH,
    TimelineClip,
    TimelineDocument,
    TimelineError,
    TimelineStore,
    TimelineTrack,
)
from uv_studio.projects.transactions import ProjectUnitOfWork

_ACCEPTED_MEDIA_ROOTS = frozenset({"sources", "assets", "artifacts", "exports"})


@dataclass(frozen=True)
class ProductionCommandResult:
    command: str
    transaction_id: str
    production: ProductionSemanticsDocument
    micro_drama: MicroDramaDocument | None = None
    timeline: TimelineDocument | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "transaction_id": self.transaction_id,
            "production": self.production.to_dict(),
            "micro_drama": (
                None if self.micro_drama is None else self.micro_drama.to_dict()
            ),
            "timeline": None if self.timeline is None else self.timeline.to_dict(),
        }


class ProductionSemanticService:
    """One semantic command surface for GUI, Agent, scripts and MCP callers."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.documents = ProductionDocumentStore(project_store)
        self.uow = ProjectUnitOfWork(project_store)

    def state(self, project_id: str) -> ProductionSemanticsDocument:
        project = self.project_store.load_project(project_id)
        require_modern_studio_identity(project)
        return self._load_semantics(project_id)

    def micro_drama_state(self, project_id: str) -> MicroDramaDocument:
        project = self.project_store.load_project(project_id)
        self._require_micro_drama(project)
        return self._load_micro_drama(project_id)

    def create_scene(
        self,
        project_id: str,
        *,
        scene_id: str,
        title: str,
        summary: str = "",
    ) -> ProductionCommandResult:
        project = self.project_store.load_project(project_id)
        require_modern_studio_identity(project)
        current = self._load_semantics(project_id)
        scene = Scene(scene_id=scene_id, title=title, summary=summary)
        if any(item.scene_id == scene.scene_id for item in current.scenes):
            raise ProductionSemanticError(f"scene already exists: {scene.scene_id!r}")
        updated = ProductionSemanticsDocument(
            scenes=(*current.scenes, scene),
            shots=current.shots,
            takes=current.takes,
        )
        return self._commit_production(
            project_id,
            command="production.create_scene",
            production=updated,
        )

    def create_shot(
        self,
        project_id: str,
        *,
        shot_id: str,
        scene_id: str,
        intent: str,
        reference_ids: tuple[str, ...] = (),
    ) -> ProductionCommandResult:
        project = self.project_store.load_project(project_id)
        require_modern_studio_identity(project)
        current = self._load_semantics(project_id)
        scene = current.scene(scene_id)
        shot = Shot(
            shot_id=shot_id,
            scene_id=scene.scene_id,
            intent=intent,
            reference_ids=reference_ids,
        )
        if any(item.shot_id == shot.shot_id for item in current.shots):
            raise ProductionSemanticError(f"shot already exists: {shot.shot_id!r}")
        for reference_id in shot.reference_ids:
            self._reference(project, reference_id)

        updated_scenes = tuple(
            replace(item, shot_ids=(*item.shot_ids, shot.shot_id))
            if item.scene_id == scene.scene_id
            else item
            for item in current.scenes
        )
        updated = ProductionSemanticsDocument(
            scenes=updated_scenes,
            shots=(*current.shots, shot),
            takes=current.takes,
        )
        return self._commit_production(
            project_id,
            command="production.create_shot",
            production=updated,
        )

    def register_take(
        self,
        project_id: str,
        *,
        take_id: str,
        shot_id: str,
        reference_id: str,
        label: str = "",
        notes: str = "",
    ) -> ProductionCommandResult:
        project = self.project_store.load_project(project_id)
        require_modern_studio_identity(project)
        current = self._load_semantics(project_id)
        shot = current.shot(shot_id)
        take = Take(
            take_id=take_id,
            shot_id=shot.shot_id,
            reference_id=reference_id,
            label=label,
            notes=notes,
        )
        if any(item.take_id == take.take_id for item in current.takes):
            raise ProductionSemanticError(f"take already exists: {take.take_id!r}")
        reference = self._reference(project, take.reference_id)
        self._require_visual_take_reference(project_id, reference)

        updated_shots = tuple(
            replace(item, take_ids=(*item.take_ids, take.take_id))
            if item.shot_id == shot.shot_id
            else item
            for item in current.shots
        )
        updated = ProductionSemanticsDocument(
            scenes=current.scenes,
            shots=updated_shots,
            takes=(*current.takes, take),
        )
        return self._commit_production(
            project_id,
            command="production.register_take",
            production=updated,
        )

    def set_micro_drama_context(
        self,
        project_id: str,
        document: MicroDramaDocument,
    ) -> ProductionCommandResult:
        project = self.project_store.load_project(project_id)
        self._require_micro_drama(project)
        production = self._load_semantics(project_id)
        scene_ids = {item.scene_id for item in production.scenes}
        for item in document.scene_continuity:
            if item.scene_id not in scene_ids:
                raise ProductionSemanticError(
                    "micro-drama continuity references unknown shared scene "
                    f"{item.scene_id!r}"
                )
        result = self.uow.commit(
            project_id,
            command="micro_drama.set_context",
            documents={MICRO_DRAMA_PATH: document.to_dict()},
        )
        return ProductionCommandResult(
            command="micro_drama.set_context",
            transaction_id=result.transaction_id,
            production=production,
            micro_drama=document,
        )

    def accept_take(
        self,
        project_id: str,
        *,
        take_id: str,
        timeline_start_us: int,
        duration_us: int,
        source_start_us: int = 0,
        track_id: str = "production_video",
        clip_id: str | None = None,
    ) -> ProductionCommandResult:
        project = self.project_store.load_project(project_id)
        require_modern_studio_identity(project)
        production = self._load_semantics(project_id)
        take = production.take(take_id)
        shot = production.shot(take.shot_id)
        if shot.accepted_take_id is not None:
            raise ProductionSemanticError(
                f"shot {shot.shot_id!r} already accepts take "
                f"{shot.accepted_take_id!r}; undo or use an explicit replacement "
                "command before accepting another take"
            )

        reference = self._reference(project, take.reference_id)
        self._require_visual_take_reference(project_id, reference)
        self._validate_source_range(
            reference,
            source_start_us=source_start_us,
            duration_us=duration_us,
        )

        try:
            track_id = validate_identifier(track_id, field_name="track_id")
            clip_id = validate_identifier(
                clip_id or f"clip_{uuid.uuid4().hex}",
                field_name="clip_id",
            )
        except ProjectValidationError as exc:
            raise ProductionSemanticError(str(exc)) from exc

        annotated_reference = replace(
            reference,
            metadata={
                **reference.metadata,
                "production_role": "accepted_take",
                "shot_id": shot.shot_id,
                "take_id": take.take_id,
            },
        )
        proposed_project = self._replace_project_reference(
            project,
            reference.id,
            annotated_reference,
        )
        proposed_project = replace(proposed_project, updated_at=utc_now_iso())

        timeline = TimelineStore(self.project_store).load(
            project_id,
            validate_references=False,
        )
        clip = TimelineClip(
            clip_id=clip_id,
            reference_id=reference.id,
            timeline_start_us=timeline_start_us,
            source_start_us=source_start_us,
            duration_us=duration_us,
        )
        updated_timeline = self._add_video_clip(
            timeline,
            track_id=track_id,
            clip=clip,
        )

        updated_shots = tuple(
            replace(
                item,
                accepted_take_id=take.take_id,
                timeline_clip_ids=(*item.timeline_clip_ids, clip.clip_id),
            )
            if item.shot_id == shot.shot_id
            else item
            for item in production.shots
        )
        updated_production = ProductionSemanticsDocument(
            scenes=production.scenes,
            shots=updated_shots,
            takes=production.takes,
        )

        transaction = self.uow.commit(
            project_id,
            command="production.accept_take",
            documents={
                PROJECT_FILENAME: proposed_project.to_dict(),
                PRODUCTION_SEMANTICS_PATH: updated_production.to_dict(),
                MAIN_TIMELINE_PATH: updated_timeline.to_dict(),
            },
        )
        return ProductionCommandResult(
            command="production.accept_take",
            transaction_id=transaction.transaction_id,
            production=updated_production,
            timeline=updated_timeline,
        )

    def _commit_production(
        self,
        project_id: str,
        *,
        command: str,
        production: ProductionSemanticsDocument,
    ) -> ProductionCommandResult:
        result = self.uow.commit(
            project_id,
            command=command,
            documents={PRODUCTION_SEMANTICS_PATH: production.to_dict()},
        )
        return ProductionCommandResult(
            command=command,
            transaction_id=result.transaction_id,
            production=production,
        )

    def _load_semantics(self, project_id: str) -> ProductionSemanticsDocument:
        try:
            raw = self.documents.load(project_id, PRODUCTION_SEMANTICS_DOCUMENT_ID)
        except ProductionDocumentNotFound:
            return ProductionSemanticsDocument()
        return ProductionSemanticsDocument.from_dict(raw)

    def _load_micro_drama(self, project_id: str) -> MicroDramaDocument:
        try:
            raw = self.documents.load(project_id, MICRO_DRAMA_DOCUMENT_ID)
        except ProductionDocumentNotFound:
            return MicroDramaDocument()
        return MicroDramaDocument.from_dict(raw)

    @staticmethod
    def _require_micro_drama(project: ProjectDocument) -> None:
        identity = require_modern_studio_identity(project)
        if identity.direction_id != "micro_drama":
            raise ProductionSemanticError(
                "micro-drama context requires direction_id='micro_drama'; "
                f"got {identity.direction_id!r}"
            )

    @staticmethod
    def _reference(project: ProjectDocument, reference_id: str) -> ProjectReference:
        try:
            reference_id = validate_identifier(reference_id, field_name="reference_id")
        except ProjectValidationError as exc:
            raise ProductionSemanticError(str(exc)) from exc
        for item in (*project.sources, *project.artifacts):
            if item.id == reference_id:
                return item
        raise ProductionSemanticError(
            f"production reference is not registered in project: {reference_id!r}"
        )

    def _require_visual_take_reference(
        self,
        project_id: str,
        reference: ProjectReference,
    ) -> None:
        if reference.kind not in {"image", "video"}:
            raise ProductionSemanticError(
                "take reference must be image/video; "
                f"{reference.id!r} is {reference.kind!r}"
            )
        root = PurePosixPath(reference.path).parts[0]
        if root not in _ACCEPTED_MEDIA_ROOTS:
            raise ProductionSemanticError(
                f"take reference path root is not accepted: {root!r}"
            )
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                reference.path,
                must_exist=True,
                allowed_roots=tuple(sorted(_ACCEPTED_MEDIA_ROOTS)),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ProductionSemanticError(str(exc)) from exc
        if not path.is_file() or path.is_symlink():
            raise ProductionSemanticError(
                "take reference must resolve to a regular project file: "
                f"{reference.id!r}"
            )

    @staticmethod
    def _validate_source_range(
        reference: ProjectReference,
        *,
        source_start_us: int,
        duration_us: int,
    ) -> None:
        if isinstance(source_start_us, bool) or not isinstance(source_start_us, int):
            raise ProductionSemanticError("source_start_us must be an integer")
        if isinstance(duration_us, bool) or not isinstance(duration_us, int):
            raise ProductionSemanticError("duration_us must be an integer")
        if source_start_us < 0:
            raise ProductionSemanticError("source_start_us must be >= 0")
        if duration_us <= 0:
            raise ProductionSemanticError("duration_us must be > 0")
        if reference.kind == "image":
            if source_start_us != 0:
                raise ProductionSemanticError(
                    "accepted still-image take requires source_start_us=0"
                )
            return
        source_duration = reference.metadata.get("duration_us")
        if (
            isinstance(source_duration, bool)
            or not isinstance(source_duration, int)
            or source_duration <= 0
        ):
            raise ProductionSemanticError(
                f"video take {reference.id!r} is missing positive duration_us metadata"
            )
        if source_start_us + duration_us > source_duration:
            raise ProductionSemanticError(
                f"accepted range exceeds source duration for {reference.id!r}"
            )

    @staticmethod
    def _replace_project_reference(
        project: ProjectDocument,
        reference_id: str,
        replacement: ProjectReference,
    ) -> ProjectDocument:
        found = False

        def replace_in(values: tuple[ProjectReference, ...]) -> tuple[ProjectReference, ...]:
            nonlocal found
            result: list[ProjectReference] = []
            for item in values:
                if item.id == reference_id:
                    found = True
                    result.append(replacement)
                else:
                    result.append(item)
            return tuple(result)

        sources = replace_in(project.sources)
        artifacts = replace_in(project.artifacts)
        if not found:
            raise ProductionSemanticError(
                f"project reference disappeared before acceptance: {reference_id!r}"
            )
        return replace(project, sources=sources, artifacts=artifacts)

    @staticmethod
    def _add_video_clip(
        timeline: TimelineDocument,
        *,
        track_id: str,
        clip: TimelineClip,
    ) -> TimelineDocument:
        tracks: list[TimelineTrack] = []
        found = False
        for track in timeline.tracks:
            if track.track_id != track_id:
                tracks.append(track)
                continue
            found = True
            if track.kind != "video":
                raise TimelineError(
                    "accepted production take requires a video track; "
                    f"{track_id!r} is {track.kind!r}"
                )
            tracks.append(replace(track, clips=(*track.clips, clip)))
        if not found:
            tracks.append(
                TimelineTrack(
                    track_id=track_id,
                    kind="video",
                    title="Production Video",
                    clips=(clip,),
                )
            )
        return TimelineDocument(
            timeline_id=timeline.timeline_id,
            tracks=tuple(tracks),
            schema_version=timeline.schema_version,
        )
