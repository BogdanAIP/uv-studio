"""Bind generation tasks to one Shot and validate final Stage-16 provenance.

A generation task may depend on an earlier task that creates its input Shot, so the
Shot cannot always be validated as a planner-time target. Deferred validation is
therefore permitted only when the task's dependency closure creates that same Shot.
The final Planner also rejects already-known invalid canonical prerequisites before
Plan persistence while preserving dependency-created Scene/Shot/Take/track/clip
chains. The public Stage-16 AgentTaskStore accepts terminal trace evidence only when
it is the exact durable Stage-15 trace correlated to the immutable Agent Task.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping, Sequence

from uv_studio.projects.timeline import TimelineError

from .harness import AgentTraceStore
from .models import AgentTraceRecord, AgentTraceStatus, portable_json, stable_digest
from .orchestration import (
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_generation_policy import (
    AgentPlanner as _GenerationPolicyAgentPlanner,
    AgentTaskCoordinator as _GenerationPolicyAgentTaskCoordinator,
)
from .stage16_runtime import (
    AgentPlanStore,
    AgentSkillCatalog,
    AgentTaskStore as _RuntimeAgentTaskStore,
    _typed_correlation_reference,
)


_DEPENDENCY_PROVISIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "production.create_scene": (("scene", "scene_id"),),
    "production.create_shot": (("shot", "shot_id"),),
    "production.register_take": (("take", "take_id"),),
    # accept_take creates the requested video track when it does not already exist.
    "production.accept_take": (("track", "track_id"), ("clip", "clip_id")),
    "timeline.create_track": (("track", "track_id"),),
    "timeline.add_clip": (("clip", "clip_id"),),
}

_EXCLUSIVE_OUTPUTS: dict[str, tuple[tuple[str, str], ...]] = {
    "production.create_scene": (("scene", "scene_id"),),
    "production.create_shot": (("shot", "shot_id"),),
    "production.register_take": (("take", "take_id"),),
    "production.accept_take": (("clip", "clip_id"),),
    "timeline.create_track": (("track", "track_id"),),
    "timeline.add_clip": (("clip", "clip_id"),),
}


class _GenerationTargetContext:
    """Delegate context building while supplying one execution-only Shot target."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self._bound_shot_id: ContextVar[str | None] = ContextVar(
            f"uv_agent_generation_target_{id(self)}",
            default=None,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    @contextmanager
    def bind(self, shot_id: str | None) -> Iterator[None]:
        token = self._bound_shot_id.set(shot_id)
        try:
            yield
        finally:
            self._bound_shot_id.reset(token)

    def build(self, project_id: str, shot_id: str | None = None):
        effective_shot_id = shot_id if shot_id is not None else self._bound_shot_id.get()
        return self._base.build(project_id, shot_id=effective_shot_id)


class AgentPlanner(_GenerationPolicyAgentPlanner):
    """Require resolvable canonical prerequisites, with bounded deferred creation."""

    @staticmethod
    def _provision_value(spec: Any, field_name: str) -> Any:
        if spec.action_id == "production.accept_take" and field_name == "track_id":
            return spec.inputs.get("track_id", "production_video")
        return spec.inputs.get(field_name)

    @staticmethod
    def _dependency_task_ids(plan: AgentPlanRecord, spec: Any) -> set[str]:
        by_id = {task.task_id: task for task in plan.tasks}
        pending = list(spec.dependencies)
        visited: set[str] = set()
        while pending:
            dependency_id = pending.pop()
            if dependency_id in visited:
                continue
            visited.add(dependency_id)
            dependency = by_id[dependency_id]
            pending.extend(dependency.dependencies)
        return visited

    @classmethod
    def _dependency_producer(
        cls,
        plan: AgentPlanRecord,
        spec: Any,
        entity_kind: str,
        identity: str,
    ) -> Any | None:
        by_id = {task.task_id: task for task in plan.tasks}
        for dependency_id in cls._dependency_task_ids(plan, spec):
            dependency = by_id[dependency_id]
            for produced_kind, field_name in _DEPENDENCY_PROVISIONS.get(
                dependency.action_id,
                (),
            ):
                if produced_kind != entity_kind:
                    continue
                if cls._provision_value(dependency, field_name) == identity:
                    return dependency
        return None

    @classmethod
    def _dependency_creates_shot(
        cls,
        plan: AgentPlanRecord,
        spec: Any,
        shot_id: str,
    ) -> bool:
        return cls._dependency_producer(plan, spec, "shot", shot_id) is not None

    @classmethod
    def _validate_unique_planned_outputs(cls, plan: AgentPlanRecord) -> None:
        seen: dict[tuple[str, str], str] = {}
        for spec in plan.tasks:
            for entity_kind, field_name in _EXCLUSIVE_OUTPUTS.get(spec.action_id, ()):
                identity = cls._provision_value(spec, field_name)
                if not isinstance(identity, str) or not identity:
                    continue
                key = (entity_kind, identity)
                previous = seen.get(key)
                if previous is not None:
                    raise AgentPlanningError(
                        f"plan creates duplicate {entity_kind} identity {identity!r} "
                        f"in tasks {previous!r} and {spec.task_id!r}"
                    )
                seen[key] = spec.task_id

    def _validate_canonical_prerequisites(
        self,
        *,
        project_id: str,
        plan: AgentPlanRecord,
    ) -> None:
        self._validate_unique_planned_outputs(plan)

        project = self.harness.project_store.load_project(project_id)
        production = self.harness.production.state(project_id)
        timeline = self.harness.timeline.timelines.load(
            project_id,
            validate_references=False,
        )

        scene_ids = {item.scene_id for item in production.scenes}
        shot_by_id = {item.shot_id: item for item in production.shots}
        take_by_id = {item.take_id: item for item in production.takes}
        track_by_id = {item.track_id: item for item in timeline.tracks}
        clip_by_id = {
            clip.clip_id: (track, clip)
            for track in timeline.tracks
            for clip in track.clips
        }
        reference_by_id = {
            item.id: item
            for item in (*project.sources, *project.artifacts)
        }
        planned_acceptance_by_shot: dict[str, str] = {}

        def require_existing_or_dependency(
            spec: Any,
            *,
            entity_kind: str,
            identity: str,
            current_ids: set[str],
            field_name: str,
        ) -> Any | None:
            if identity in current_ids:
                return None
            producer = self._dependency_producer(
                plan,
                spec,
                entity_kind,
                identity,
            )
            if producer is None:
                raise AgentPlanningError(
                    f"action {spec.action_id!r} {field_name} {identity!r} must already "
                    "exist or be created by its dependency closure"
                )
            return producer

        def require_reference(spec: Any, reference_id: str) -> Any:
            reference = reference_by_id.get(reference_id)
            if reference is None:
                raise AgentPlanningError(
                    f"action {spec.action_id!r} media reference {reference_id!r} "
                    "must already be registered in the project"
                )
            return reference

        for spec in plan.tasks:
            action_id = spec.action_id
            if action_id == "production.create_scene":
                scene_id = spec.inputs["scene_id"]
                if scene_id in scene_ids:
                    raise AgentPlanningError(
                        f"production.create_scene scene already exists: {scene_id!r}"
                    )
                continue

            if action_id == "production.create_shot":
                shot_id = spec.inputs["shot_id"]
                if shot_id in shot_by_id:
                    raise AgentPlanningError(
                        f"production.create_shot shot already exists: {shot_id!r}"
                    )
                require_existing_or_dependency(
                    spec,
                    entity_kind="scene",
                    identity=spec.inputs["scene_id"],
                    current_ids=scene_ids,
                    field_name="scene_id",
                )
                for reference_id in spec.inputs.get("reference_ids", ()):
                    require_reference(spec, reference_id)
                continue

            if action_id == "production.register_take":
                take_id = spec.inputs["take_id"]
                if take_id in take_by_id:
                    raise AgentPlanningError(
                        f"production.register_take take already exists: {take_id!r}"
                    )
                require_existing_or_dependency(
                    spec,
                    entity_kind="shot",
                    identity=spec.inputs["shot_id"],
                    current_ids=set(shot_by_id),
                    field_name="shot_id",
                )
                reference_id = spec.inputs["reference_id"]
                reference = require_reference(spec, reference_id)
                if reference.kind not in {"image", "video"}:
                    raise AgentPlanningError(
                        "production.register_take reference must be image/video; "
                        f"{reference_id!r} is {reference.kind!r}"
                    )
                try:
                    self.harness.timeline.timelines.reference(
                        project_id,
                        reference_id,
                        project=project,
                    )
                except TimelineError as exc:
                    raise AgentPlanningError(
                        f"production.register_take reference is unavailable: {exc}"
                    ) from exc
                continue

            if action_id == "production.accept_take":
                take_id = spec.inputs["take_id"]
                producer = require_existing_or_dependency(
                    spec,
                    entity_kind="take",
                    identity=take_id,
                    current_ids=set(take_by_id),
                    field_name="take_id",
                )
                if take_id in take_by_id:
                    shot_id = take_by_id[take_id].shot_id
                elif producer is not None and producer.action_id == "production.register_take":
                    shot_id = producer.inputs["shot_id"]
                else:
                    shot_id = None
                if shot_id in shot_by_id and shot_by_id[shot_id].accepted_take_id is not None:
                    raise AgentPlanningError(
                        f"production.accept_take shot {shot_id!r} already accepts take "
                        f"{shot_by_id[shot_id].accepted_take_id!r}"
                    )
                if shot_id is not None:
                    previous_acceptance = planned_acceptance_by_shot.get(shot_id)
                    if previous_acceptance is not None:
                        raise AgentPlanningError(
                            f"plan accepts Shot {shot_id!r} more than once in tasks "
                            f"{previous_acceptance!r} and {spec.task_id!r}"
                        )
                    planned_acceptance_by_shot[shot_id] = spec.task_id

                track_id = spec.inputs.get("track_id", "production_video")
                track = track_by_id.get(track_id)
                if track is not None and track.kind != "video":
                    raise AgentPlanningError(
                        "production.accept_take requires a video track; "
                        f"{track_id!r} is {track.kind!r}"
                    )
                if track is None:
                    planned_track = next(
                        (
                            item
                            for item in plan.tasks
                            if item.action_id == "timeline.create_track"
                            and item.inputs.get("track_id") == track_id
                        ),
                        None,
                    )
                    dependency_ids = self._dependency_task_ids(plan, spec)
                    if (
                        planned_track is not None
                        and planned_track.task_id not in dependency_ids
                    ):
                        raise AgentPlanningError(
                            f"production.accept_take track {track_id!r} is also created by "
                            f"task {planned_track.task_id!r}; that creator must be in its "
                            "dependency closure"
                        )
                    if (
                        planned_track is not None
                        and planned_track.task_id in dependency_ids
                        and planned_track.inputs.get("kind") != "video"
                    ):
                        raise AgentPlanningError(
                            "production.accept_take requires a video track; dependency "
                            f"task {planned_track.task_id!r} creates {track_id!r} as "
                            f"{planned_track.inputs.get('kind')!r}"
                        )

                clip_id = spec.inputs.get("clip_id")
                if clip_id is not None and clip_id in clip_by_id:
                    raise AgentPlanningError(
                        f"production.accept_take clip already exists: {clip_id!r}"
                    )
                continue

            if action_id == "timeline.create_track":
                track_id = spec.inputs.get("track_id")
                if track_id is not None and track_id in track_by_id:
                    raise AgentPlanningError(
                        f"timeline.create_track track already exists: {track_id!r}"
                    )
                continue

            if action_id == "timeline.add_clip":
                track_id = spec.inputs["track_id"]
                track = track_by_id.get(track_id)
                producer = require_existing_or_dependency(
                    spec,
                    entity_kind="track",
                    identity=track_id,
                    current_ids=set(track_by_id),
                    field_name="track_id",
                )
                if track is not None:
                    track_kind = track.kind
                elif producer is not None and producer.action_id == "timeline.create_track":
                    track_kind = producer.inputs["kind"]
                elif producer is not None and producer.action_id == "production.accept_take":
                    track_kind = "video"
                else:
                    track_kind = None

                reference_id = spec.inputs["reference_id"]
                reference = require_reference(spec, reference_id)
                try:
                    self.harness.timeline.timelines.reference(
                        project_id,
                        reference_id,
                        project=project,
                    )
                except TimelineError as exc:
                    raise AgentPlanningError(
                        f"timeline.add_clip reference is unavailable: {exc}"
                    ) from exc
                if track_kind == "video" and reference.kind not in {"video", "image"}:
                    raise AgentPlanningError(
                        f"timeline.add_clip video track {track_id!r} requires image/video "
                        f"reference; {reference_id!r} is {reference.kind!r}"
                    )
                if track_kind == "audio" and reference.kind != "audio":
                    raise AgentPlanningError(
                        f"timeline.add_clip audio track {track_id!r} requires audio "
                        f"reference; {reference_id!r} is {reference.kind!r}"
                    )

                clip_id = spec.inputs.get("clip_id")
                if clip_id is not None and clip_id in clip_by_id:
                    raise AgentPlanningError(
                        f"timeline.add_clip clip already exists: {clip_id!r}"
                    )
                continue

            if action_id in {
                "timeline.move_clip",
                "timeline.remove_clip",
                "timeline.trim_clip",
            }:
                require_existing_or_dependency(
                    spec,
                    entity_kind="clip",
                    identity=spec.inputs["clip_id"],
                    current_ids=set(clip_by_id),
                    field_name="clip_id",
                )

    def build(
        self,
        *,
        project_id: str,
        goal: str,
        proposals: Sequence[AgentPlanStepProposal],
        target_shot_id: str | None = None,
        canonical_references: Sequence[str] = (),
        plan_id: str | None = None,
    ) -> AgentPlanRecord:
        plan = super().build(
            project_id=project_id,
            goal=goal,
            proposals=proposals,
            target_shot_id=target_shot_id,
            canonical_references=canonical_references,
            plan_id=plan_id,
        )
        self._validate_canonical_prerequisites(
            project_id=project_id,
            plan=plan,
        )
        for spec in plan.tasks:
            if spec.action_id != "generation.submit":
                continue
            shot_id = spec.inputs.get("shot_id")
            if not isinstance(shot_id, str) or not shot_id:
                raise AgentPlanningError(
                    "generation.submit lost its required input Shot identity"
                )
            if spec.target_shot_id is not None:
                if spec.target_shot_id != shot_id:
                    raise AgentPlanningError(
                        "generation.submit target_shot_id must match inputs['shot_id']"
                    )
                continue

            try:
                self.harness.production.state(project_id).shot(shot_id)
            except Exception as exc:
                if not self._dependency_creates_shot(plan, spec, shot_id):
                    raise AgentPlanningError(
                        "generation.submit input Shot must already exist or be created "
                        "by its dependency closure"
                    ) from exc
        return plan


class AgentTaskStore(_RuntimeAgentTaskStore):
    """Public Stage-16 task store with terminal trace provenance validation."""

    @staticmethod
    def _expected_input_digest(spec: Any) -> str:
        return stable_digest(
            {
                "action_id": spec.action_id,
                "inputs": portable_json(spec.inputs, field_name="Agent action inputs"),
            }
        )

    def _validate_terminal_trace(
        self,
        current: AgentTaskRecord,
        target: AgentTaskStatus,
        trace: AgentTraceRecord,
    ) -> None:
        if target not in {AgentTaskStatus.SUCCEEDED, AgentTaskStatus.FAILED}:
            raise AgentTaskStateError(
                "Agent Task trace evidence is only valid for terminal execution transitions"
            )
        if trace.project_id != current.project_id:
            raise AgentTaskStateError("Agent Task trace project provenance mismatch")
        if trace.action_id != current.action_id:
            raise AgentTaskStateError("Agent Task trace action provenance mismatch")

        expected_status = (
            AgentTraceStatus.SUCCEEDED
            if target is AgentTaskStatus.SUCCEEDED
            else AgentTraceStatus.FAILED
        )
        if trace.status is not expected_status:
            raise AgentTaskStateError(
                "Agent Task terminal status does not match Stage-15 trace status"
            )

        plan = AgentPlanStore(self.project_store).get(
            current.project_id,
            current.plan_id,
        )
        spec = plan.task(current.task_id)
        if spec.action_id != current.action_id or spec.skill_id != current.skill_id:
            raise AgentTaskStateError(
                "Agent Task trace validation disagrees with immutable plan identity"
            )

        typed_reference = _typed_correlation_reference(
            current.plan_id,
            current.task_id,
            current.skill_id,
        )
        if typed_reference not in trace.canonical_references:
            raise AgentTaskStateError(
                "Agent Task trace is missing typed task correlation provenance"
            )
        if trace.input_digest != self._expected_input_digest(spec):
            raise AgentTaskStateError("Agent Task trace input provenance mismatch")
        if current.started_at is not None and trace.created_at < current.started_at:
            raise AgentTaskStateError("Agent Task trace predates this execution attempt")

        durable_matches = [
            item
            for item in AgentTraceStore(self.project_store).list(current.project_id)
            if item.trace_id == trace.trace_id
        ]
        if len(durable_matches) != 1 or durable_matches[0] != trace:
            raise AgentTaskStateError(
                "Agent Task trace is not the exact durable Stage-15 trace record"
            )

    def transition(
        self,
        record: AgentTaskRecord,
        status: AgentTaskStatus,
        *,
        trace: AgentTraceRecord | None = None,
        error: Exception | None = None,
    ) -> AgentTaskRecord:
        target = status if isinstance(status, AgentTaskStatus) else AgentTaskStatus(status)
        current = self.get(record.project_id, record.plan_id, record.task_id)
        if current.record_id != record.record_id:
            raise AgentTaskStateError(
                f"stale Agent Task snapshot has replaced record identity: {record.task_id!r}"
            )
        if current != record:
            raise AgentTaskStateError(
                f"stale Agent Task snapshot for {record.task_id!r}; reload durable state"
            )
        allowed = self._ALLOWED_TRANSITIONS[current.status]
        if target not in allowed:
            raise AgentTaskStateError(
                f"invalid Agent Task transition: {current.status.value} -> {target.value}"
            )
        if target is AgentTaskStatus.SUCCEEDED and trace is None:
            raise AgentTaskStateError(
                "succeeded Agent Task transition requires correlated durable trace evidence"
            )
        if trace is not None:
            self._validate_terminal_trace(current, target, trace)
        return super().transition(
            record,
            target,
            trace=trace,
            error=error,
        )


class AgentTaskCoordinator(_GenerationPolicyAgentTaskCoordinator):
    """Final Stage-16 coordinator with one generation Shot and validated task traces."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        current_context = harness.context
        if isinstance(current_context, _GenerationTargetContext):
            self._generation_target_context = current_context
        else:
            self._generation_target_context = _GenerationTargetContext(current_context)
            harness.context = self._generation_target_context
        if planner is None:
            planner = AgentPlanner(
                harness,
                skills=AgentSkillCatalog(harness.catalog),
            )
        if task_store is None:
            task_store = AgentTaskStore(harness.project_store)
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )

    @staticmethod
    def _execution_target_shot_id(spec: Any) -> str | None:
        if spec.action_id != "generation.submit":
            return spec.target_shot_id
        shot_id = spec.inputs.get("shot_id")
        if not isinstance(shot_id, str) or not shot_id:
            raise AgentTaskStateError(
                "durable generation task lost its input Shot identity"
            )
        if spec.target_shot_id is not None and spec.target_shot_id != shot_id:
            raise AgentTaskStateError(
                "durable generation task target Shot does not match its input Shot"
            )
        return shot_id

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        with self.project_store._lock:
            plan = self.plans.get(project_id, plan_id)
            spec = plan.task(task_id)
            target_shot_id = self._execution_target_shot_id(spec)

        with self._generation_target_context.bind(target_shot_id):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                runtime_inputs=runtime_inputs,
            )


__all__ = ["AgentPlanner", "AgentTaskCoordinator", "AgentTaskStore"]
