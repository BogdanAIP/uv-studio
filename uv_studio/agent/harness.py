"""Context, existing-authority catalog, policy projection, trace and bounded execution."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Mapping

from uv_studio.capabilities.authorization import OneShotAuthorizationStore, prepare_execution
from uv_studio.capabilities.models import (
    CapabilityEffects,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.editor.timeline_commands import (
    AddClipCommand,
    CreateTrackCommand,
    MoveClipCommand,
    RemoveClipCommand,
    TimelineCommandService,
    TrimClipCommand,
)
from uv_studio.generation.jobs import GenerationJobManager
from uv_studio.generation.models import GenerationContract, ModelRegistry
from uv_studio.generation.service import GenerationExecutor, GenerationService
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import require_modern_studio_identity
from uv_studio.projects.models import utc_now_iso
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore
from uv_studio.projects.timeline import TimelineStore

from .models import (
    AgentActionDefinition,
    AgentContextSnapshot,
    AgentHarnessError,
    AgentPolicyProjection,
    AgentPortableStateError,
    AgentTraceRecord,
    AgentTraceStatus,
    AgentUnknownAction,
    agent_trace_from_dict,
    portable_json,
    safe_error_message,
    stable_digest,
)

_MAX_CONTEXT_REFERENCES = 100
_MAX_CONTEXT_JOBS = 100
_MAX_CONTEXT_MODELS = 100


def _mutating(*, timeline: bool = False, destructive: bool = False) -> CapabilityEffects:
    return CapabilityEffects(
        mutates_project=True,
        mutates_timeline=timeline,
        destructive=destructive,
        reversible=True,
    )


_BUILTIN_ACTIONS = (
    AgentActionDefinition(
        action_id="generation.submit",
        title="Submit named generation",
        description="Submit one named-model generation request through GenerationService and D-017.",
        authority="uv_studio.generation.service.GenerationService.submit",
        input_fields=(
            "shot_id",
            "model_id",
            "inputs",
            "contract",
            "idempotency_key",
            "authorization_token",
        ),
        requires_model=True,
    ),
    AgentActionDefinition(
        action_id="production.accept_take",
        title="Accept take",
        description="Accept an existing Take through ProductionSemanticService and canonical Timeline projection.",
        authority="uv_studio.production.commands.ProductionSemanticService.accept_take",
        input_fields=(
            "take_id",
            "timeline_start_us",
            "duration_us",
            "source_start_us",
            "track_id",
            "clip_id",
        ),
        effects=_mutating(timeline=True),
    ),
    AgentActionDefinition(
        action_id="production.create_scene",
        title="Create scene",
        description="Create a shared production Scene through ProductionSemanticService.",
        authority="uv_studio.production.commands.ProductionSemanticService.create_scene",
        input_fields=("scene_id", "title", "summary"),
        effects=_mutating(),
    ),
    AgentActionDefinition(
        action_id="production.create_shot",
        title="Create shot",
        description="Create a shared production Shot through ProductionSemanticService.",
        authority="uv_studio.production.commands.ProductionSemanticService.create_shot",
        input_fields=("shot_id", "scene_id", "intent", "reference_ids"),
        effects=_mutating(),
    ),
    AgentActionDefinition(
        action_id="production.register_take",
        title="Register take",
        description="Register an existing project-owned visual reference as a Take.",
        authority="uv_studio.production.commands.ProductionSemanticService.register_take",
        input_fields=("take_id", "shot_id", "reference_id", "label", "notes"),
        effects=_mutating(),
    ),
    AgentActionDefinition(
        action_id="timeline.add_clip",
        title="Add Timeline clip",
        description="Add a clip through the canonical TimelineCommandService.",
        authority="uv_studio.editor.timeline_commands.TimelineCommandService.add_clip",
        input_fields=(
            "track_id",
            "reference_id",
            "timeline_start_us",
            "duration_us",
            "source_start_us",
            "clip_id",
        ),
        effects=_mutating(timeline=True),
    ),
    AgentActionDefinition(
        action_id="timeline.create_track",
        title="Create Timeline track",
        description="Create a track through the canonical TimelineCommandService.",
        authority="uv_studio.editor.timeline_commands.TimelineCommandService.create_track",
        input_fields=("kind", "title", "track_id"),
        effects=_mutating(timeline=True),
    ),
    AgentActionDefinition(
        action_id="timeline.move_clip",
        title="Move Timeline clip",
        description="Move an existing clip through the canonical TimelineCommandService.",
        authority="uv_studio.editor.timeline_commands.TimelineCommandService.move_clip",
        input_fields=("clip_id", "timeline_start_us"),
        effects=_mutating(timeline=True),
    ),
    AgentActionDefinition(
        action_id="timeline.remove_clip",
        title="Remove Timeline clip",
        description="Remove an existing clip through the canonical TimelineCommandService.",
        authority="uv_studio.editor.timeline_commands.TimelineCommandService.remove_clip",
        input_fields=("clip_id",),
        effects=_mutating(timeline=True, destructive=True),
    ),
    AgentActionDefinition(
        action_id="timeline.trim_clip",
        title="Trim Timeline clip",
        description="Trim an existing clip through the canonical TimelineCommandService.",
        authority="uv_studio.editor.timeline_commands.TimelineCommandService.trim_clip",
        input_fields=("clip_id", "source_start_us", "duration_us"),
        effects=_mutating(timeline=True),
    ),
)


class AgentContextBuilder:
    """Build compact observations only from canonical UV-owned state."""

    def __init__(
        self,
        project_store: ProjectStore,
        model_registry: ModelRegistry,
        job_manager: GenerationJobManager | None = None,
    ) -> None:
        self.project_store = project_store
        self.model_registry = model_registry
        self.jobs = job_manager or GenerationJobManager(project_store)
        self.production = ProductionSemanticService(project_store)
        self.timelines = TimelineStore(project_store)

    @staticmethod
    def _bounded(items: list[Any], limit: int) -> tuple[list[Any], int]:
        return items[:limit], max(0, len(items) - limit)

    def build(
        self,
        project_id: str,
        *,
        shot_id: str | None = None,
    ) -> AgentContextSnapshot:
        project = self.project_store.load_project(project_id)
        identity = require_modern_studio_identity(project)
        production = self.production.state(project_id)
        timeline = self.timelines.load(project_id, validate_references=False)

        target_kind = "project"
        target_id = project.project_id
        shot_payload: dict[str, Any] | None = None
        scene_payload: dict[str, Any] | None = None
        take_payloads: list[dict[str, Any]] = []
        if shot_id is not None:
            shot = production.shot(shot_id)
            scene = production.scene(shot.scene_id)
            target_kind = "shot"
            target_id = shot.shot_id
            shot_payload = shot.to_dict()
            scene_payload = {
                "scene_id": scene.scene_id,
                "title": scene.title,
                "summary": scene.summary,
            }
            take_payloads = [
                {
                    "take_id": take.take_id,
                    "reference_id": take.reference_id,
                    "label": take.label,
                }
                for take in (production.take(take_id) for take_id in shot.take_ids)
            ]

        references = [
            {"id": item.id, "kind": item.kind, "path": item.path}
            for item in sorted(
                (*project.sources, *project.artifacts),
                key=lambda item: item.id,
            )
        ]
        references, references_omitted = self._bounded(
            references,
            _MAX_CONTEXT_REFERENCES,
        )

        tracks = [
            {
                "track_id": track.track_id,
                "kind": track.kind,
                "title": track.title,
                "clip_ids": [clip.clip_id for clip in track.clips],
            }
            for track in timeline.tracks
        ]

        model_items = [
            self.model_registry.describe(model.model_id)
            for model in self.model_registry.list()
        ]
        model_items, models_omitted = self._bounded(
            model_items,
            _MAX_CONTEXT_MODELS,
        )

        job_items = [
            {
                "job_id": job.job_id,
                "request_digest": job.request_digest,
                "status": job.status.value,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "attempts": [
                    {
                        "attempt_id": attempt.attempt_id,
                        "retry_index": attempt.retry_index,
                        "status": attempt.status.value,
                        "output_reference_id": attempt.output_reference_id,
                        "take_id": attempt.take_id,
                    }
                    for attempt in job.attempts
                ],
            }
            for job in self.jobs.list(project_id)
        ]
        job_items, jobs_omitted = self._bounded(job_items, _MAX_CONTEXT_JOBS)

        content = {
            "project": {
                "project_id": project.project_id,
                "title": project.title,
                "direction_id": identity.direction_id,
                "updated_at": project.updated_at,
                "references": references,
                "references_omitted": references_omitted,
            },
            "production": {
                "scene_count": len(production.scenes),
                "shot_count": len(production.shots),
                "take_count": len(production.takes),
                "target_scene": scene_payload,
                "target_shot": shot_payload,
                "target_takes": take_payloads,
            },
            "timeline": {
                "timeline_id": timeline.timeline_id,
                "track_count": len(timeline.tracks),
                "tracks": tracks,
            },
            "models": {
                "items": model_items,
                "omitted": models_omitted,
            },
            "jobs": {
                "items": job_items,
                "omitted": jobs_omitted,
            },
        }
        return AgentContextSnapshot(
            project_id=project.project_id,
            target_kind=target_kind,
            target_id=target_id,
            content=content,
        )


class AgentActionCatalog:
    """Deterministic metadata over existing UV-owned execution authorities."""

    def __init__(self, model_registry: ModelRegistry) -> None:
        self.model_registry = model_registry
        self._actions = {
            item.action_id: item
            for item in sorted(_BUILTIN_ACTIONS, key=lambda value: value.action_id)
        }

    def list(self) -> tuple[AgentActionDefinition, ...]:
        return tuple(self._actions.values())

    def get(self, action_id: str) -> AgentActionDefinition:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise AgentUnknownAction(action_id) from exc

    def policy(
        self,
        *,
        project_id: str,
        action_id: str,
        model_id: str | None = None,
    ) -> AgentPolicyProjection:
        action = self.get(action_id)
        if not action.requires_model:
            return AgentPolicyProjection(
                action_id=action.action_id,
                available=True,
                reason="local existing UV command authority",
                locality=LocalityClass.LOCAL.value,
                cost_class=CostClass.FREE.value,
                authorization_required=False,
                consent_required=(),
                effects=action.effects,
            )

        if model_id is None:
            return AgentPolicyProjection(
                action_id=action.action_id,
                available=False,
                reason="model_id is required for named generation policy",
                locality="unknown",
                cost_class="unknown",
                authorization_required=False,
                consent_required=(),
                effects=action.effects,
            )

        model = self.model_registry.get(model_id)
        capabilities = self.model_registry.capability_registry
        offer = capabilities.get_offer(model.offer_id)
        effects = capabilities.effects_for_offer(offer.offer_id)
        preparation = prepare_execution(
            project_id=project_id,
            offer=offer,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={},
        )
        return AgentPolicyProjection(
            action_id=action.action_id,
            available=offer.availability is OfferAvailability.AVAILABLE,
            reason=offer.reason,
            locality=offer.locality.value,
            cost_class=offer.cost_class.value,
            authorization_required=preparation.authorization_required,
            consent_required=tuple(item.value for item in preparation.consent_required),
            effects=effects,
            model_id=model.model_id,
            capability_id=model.capability_id,
            offer_id=offer.offer_id,
        )


class AgentTraceStore:
    """Append-only Agent execution history under the existing project tasks/ authority."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def append(self, record: AgentTraceRecord) -> Path:
        if not isinstance(record, AgentTraceRecord):
            raise AgentPortableStateError("trace append requires AgentTraceRecord")
        with self.project_store._lock:
            self.project_store.load_project(record.project_id)
            path = self.records.path(record.project_id, record.trace_id)
            if path.exists() or path.is_symlink():
                raise AgentPortableStateError(
                    f"Agent trace already exists: {record.trace_id!r}"
                )
            return self.records.write(
                record.project_id,
                record.trace_id,
                record.to_dict(),
            )

    def list(self, project_id: str) -> tuple[AgentTraceRecord, ...]:
        with self.project_store._lock:
            project_dir = self.project_store.project_directory(project_id)
            traces: list[AgentTraceRecord] = []
            for path in sorted(
                (project_dir / "tasks").glob("agent_trace_*.json"),
                key=lambda item: item.name,
            ):
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    record = agent_trace_from_dict(raw)
                except (
                    OSError,
                    ValueError,
                    json.JSONDecodeError,
                    AgentPortableStateError,
                ) as exc:
                    raise AgentPortableStateError(
                        f"invalid Agent trace record {path.name!r}: {exc}"
                    ) from exc
                if record.project_id != project_id or record.trace_id != path.stem:
                    raise AgentPortableStateError("Agent trace record identity mismatch")
                traces.append(record)
            traces.sort(key=lambda item: (item.created_at, item.trace_id))
            return tuple(traces)


class AgentHarness:
    """Bounded executor that never bypasses existing Studio/Application Commands."""

    def __init__(
        self,
        project_store: ProjectStore,
        model_registry: ModelRegistry,
        *,
        authorizations: OneShotAuthorizationStore | None = None,
        generation_executor: GenerationExecutor | None = None,
    ) -> None:
        self.project_store = project_store
        self.model_registry = model_registry
        self.authorizations = authorizations or OneShotAuthorizationStore()
        self.jobs = GenerationJobManager(project_store)
        self.context = AgentContextBuilder(project_store, model_registry, self.jobs)
        self.catalog = AgentActionCatalog(model_registry)
        self.traces = AgentTraceStore(project_store)
        self.production = ProductionSemanticService(project_store)
        self.timeline = TimelineCommandService(project_store)
        self.generation = GenerationService(
            project_store,
            model_registry,
            self.authorizations,
            executor=generation_executor,
        )

    @staticmethod
    def _traceable_inputs(inputs: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in inputs.items()
            if key != "authorization_token"
        }

    @staticmethod
    def _canonical_result_references(result: Any) -> dict[str, str]:
        refs: dict[str, str] = {}
        for field_name in ("transaction_id", "track_id", "clip_id"):
            value = getattr(result, field_name, None)
            if isinstance(value, str) and value:
                refs[field_name] = value

        job = getattr(result, "job", None)
        if job is not None:
            refs["job_id"] = job.job_id
            attempt = job.current_attempt
            if attempt is not None:
                refs["attempt_id"] = attempt.attempt_id
                if attempt.output_reference_id is not None:
                    refs["output_reference_id"] = attempt.output_reference_id
                if attempt.take_id is not None:
                    refs["take_id"] = attempt.take_id
        return refs

    @staticmethod
    def _canonical_references(
        snapshot: AgentContextSnapshot,
        result_references: Mapping[str, str],
    ) -> tuple[str, ...]:
        values = [snapshot.project_id, snapshot.target_id]
        values.extend(result_references.values())
        # Preserve deterministic first occurrence while avoiding duplicate project target.
        return tuple(dict.fromkeys(values))

    def _policy_for_inputs(
        self,
        *,
        project_id: str,
        action_id: str,
        inputs: Mapping[str, Any],
    ) -> AgentPolicyProjection:
        model_id = inputs.get("model_id")
        return self.catalog.policy(
            project_id=project_id,
            action_id=action_id,
            model_id=model_id if isinstance(model_id, str) else None,
        )

    def _invoke(
        self,
        *,
        project_id: str,
        action_id: str,
        inputs: Mapping[str, Any],
    ) -> Any:
        payload = dict(inputs)
        if action_id == "production.create_scene":
            return self.production.create_scene(project_id, **payload)
        if action_id == "production.create_shot":
            if "reference_ids" in payload:
                payload["reference_ids"] = tuple(payload["reference_ids"])
            return self.production.create_shot(project_id, **payload)
        if action_id == "production.register_take":
            return self.production.register_take(project_id, **payload)
        if action_id == "production.accept_take":
            return self.production.accept_take(project_id, **payload)
        if action_id == "timeline.create_track":
            return self.timeline.create_track(project_id, CreateTrackCommand(**payload))
        if action_id == "timeline.add_clip":
            return self.timeline.add_clip(project_id, AddClipCommand(**payload))
        if action_id == "timeline.move_clip":
            return self.timeline.move_clip(project_id, MoveClipCommand(**payload))
        if action_id == "timeline.trim_clip":
            return self.timeline.trim_clip(project_id, TrimClipCommand(**payload))
        if action_id == "timeline.remove_clip":
            return self.timeline.remove_clip(project_id, RemoveClipCommand(**payload))
        if action_id == "generation.submit":
            contract = payload.get("contract")
            if isinstance(contract, Mapping):
                payload["contract"] = GenerationContract.from_dict(contract)
            return self.generation.submit(project_id=project_id, **payload)
        raise AgentUnknownAction(action_id)

    def execute(
        self,
        *,
        project_id: str,
        action_id: str,
        inputs: Mapping[str, Any],
        target_shot_id: str | None = None,
    ) -> Any:
        if not isinstance(inputs, Mapping):
            raise AgentPortableStateError("Agent action inputs must be a JSON object")

        snapshot = self.context.build(project_id, shot_id=target_shot_id)
        traceable_inputs = self._traceable_inputs(inputs)
        input_digest = stable_digest(
            {
                "action_id": action_id,
                "inputs": portable_json(
                    traceable_inputs,
                    field_name="Agent action inputs",
                ),
            }
        )

        try:
            policy = self._policy_for_inputs(
                project_id=project_id,
                action_id=action_id,
                inputs=inputs,
            )
        except AgentUnknownAction:
            policy = AgentPolicyProjection(
                action_id=action_id,
                available=False,
                reason="unknown action",
                locality="unknown",
                cost_class="unknown",
                authorization_required=False,
                consent_required=(),
                effects=CapabilityEffects(),
            )
            record = AgentTraceRecord(
                trace_id=f"agent_trace_{uuid.uuid4().hex}",
                project_id=project_id,
                created_at=utc_now_iso(),
                context_digest=snapshot.digest,
                action_id=action_id,
                input_digest=input_digest,
                canonical_references=self._canonical_references(snapshot, {}),
                policy=policy,
                status=AgentTraceStatus.FAILED,
                error_type="AgentUnknownAction",
                error_message="unknown action",
            )
            self.traces.append(record)
            raise
        except Exception as exc:
            definition = self.catalog.get(action_id)
            policy = AgentPolicyProjection(
                action_id=action_id,
                available=False,
                reason=safe_error_message(exc),
                locality="unknown",
                cost_class="unknown",
                authorization_required=False,
                consent_required=(),
                effects=definition.effects,
            )
            record = AgentTraceRecord(
                trace_id=f"agent_trace_{uuid.uuid4().hex}",
                project_id=project_id,
                created_at=utc_now_iso(),
                context_digest=snapshot.digest,
                action_id=action_id,
                input_digest=input_digest,
                canonical_references=self._canonical_references(snapshot, {}),
                policy=policy,
                status=AgentTraceStatus.FAILED,
                error_type=exc.__class__.__name__,
                error_message=safe_error_message(exc),
            )
            self.traces.append(record)
            raise

        if not policy.available:
            error = AgentHarnessError(policy.reason)
            record = AgentTraceRecord(
                trace_id=f"agent_trace_{uuid.uuid4().hex}",
                project_id=project_id,
                created_at=utc_now_iso(),
                context_digest=snapshot.digest,
                action_id=action_id,
                input_digest=input_digest,
                canonical_references=self._canonical_references(snapshot, {}),
                policy=policy,
                status=AgentTraceStatus.FAILED,
                error_type=error.__class__.__name__,
                error_message=safe_error_message(error),
            )
            self.traces.append(record)
            raise error

        try:
            result = self._invoke(
                project_id=project_id,
                action_id=action_id,
                inputs=inputs,
            )
        except Exception as exc:
            record = AgentTraceRecord(
                trace_id=f"agent_trace_{uuid.uuid4().hex}",
                project_id=project_id,
                created_at=utc_now_iso(),
                context_digest=snapshot.digest,
                action_id=action_id,
                input_digest=input_digest,
                canonical_references=self._canonical_references(snapshot, {}),
                policy=policy,
                status=AgentTraceStatus.FAILED,
                error_type=exc.__class__.__name__,
                error_message=safe_error_message(exc),
            )
            self.traces.append(record)
            raise

        result_references = self._canonical_result_references(result)
        record = AgentTraceRecord(
            trace_id=f"agent_trace_{uuid.uuid4().hex}",
            project_id=project_id,
            created_at=utc_now_iso(),
            context_digest=snapshot.digest,
            action_id=action_id,
            input_digest=input_digest,
            canonical_references=self._canonical_references(
                snapshot,
                result_references,
            ),
            policy=policy,
            status=AgentTraceStatus.SUCCEEDED,
            result_references=result_references,
        )
        self.traces.append(record)
        return result
