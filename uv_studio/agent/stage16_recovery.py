"""Final Stage-16 planning validation and committed-effect recovery.

This layer stays above the Stage-15 AgentHarness and existing UV mutation authorities.
It closes review gaps without replaying work:

* durable plans validate required inputs and command-level input shapes before persistence;
* foreground execution binds the exact execution-time context into durable correlation
  evidence before any canonical/cost-bearing effect;
* a task that crashes after a canonical transaction/Job commit but before the Stage-15
  success trace reconstructs that trace from authoritative durable evidence.

Production/Timeline correlation is written into the existing ProjectUnitOfWork
prepared journal before canonical bytes change. Generation submission is already
idempotent and durable through GenerationJobManager, so recovery validates the exact
persisted Job request bound to the planned idempotency key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Any, Iterator, Mapping, Sequence

from uv_studio.editor.timeline_commands import (
    AddClipCommand,
    CreateTrackCommand,
    MoveClipCommand,
    RemoveClipCommand,
    TimelineCommandError,
    TrimClipCommand,
)
from uv_studio.generation.models import GenerationContract, GenerationValidationError
from uv_studio.production.semantics import (
    ProductionSemanticError,
    Scene,
    Shot,
    Take,
)
from uv_studio.projects.models import ProjectValidationError, validate_identifier
from uv_studio.projects.timeline import (
    MAIN_TIMELINE_PATH,
    TimelineClip,
    TimelineDocument,
    TimelineError,
)
from uv_studio.projects.transactions import (
    HISTORY_TRANSACTIONS_ROOT,
    ProjectTransactionError,
    ProjectUnitOfWork,
)

from .models import AgentTraceRecord, AgentTraceStatus, portable_json, stable_digest
from .orchestration import (
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_runtime import (
    AgentPlanner as _RuntimeAgentPlanner,
    AgentSkillCatalog,
    AgentTaskCoordinator as _RuntimeAgentTaskCoordinator,
    AgentTaskStore as _RuntimeAgentTaskStore,
)

_CORRELATION_FIELD = "execution_correlation_id"
_EXECUTION_CONTEXT_FIELD = "execution_context_digest"
_EXECUTION_CONTEXT_REFERENCE_PREFIX = "agent_ctx_"

_EXECUTION_CORRELATION: ContextVar[str | None] = ContextVar(
    "uv_stage16_project_transaction_correlation",
    default=None,
)
_EXECUTION_CONTEXT: ContextVar[str | None] = ContextVar(
    "uv_stage16_execution_context_digest",
    default=None,
)

_REQUIRED_ACTION_INPUTS: dict[str, tuple[str, ...]] = {
    "generation.submit": (
        "shot_id",
        "model_id",
        "inputs",
        "contract",
        "idempotency_key",
    ),
    "production.accept_take": ("take_id", "timeline_start_us", "duration_us"),
    "production.create_scene": ("scene_id", "title"),
    "production.create_shot": ("shot_id", "scene_id", "intent"),
    "production.register_take": ("take_id", "shot_id", "reference_id"),
    "timeline.add_clip": (
        "track_id",
        "reference_id",
        "timeline_start_us",
        "duration_us",
    ),
    "timeline.create_track": ("kind",),
    "timeline.move_clip": ("clip_id", "timeline_start_us"),
    "timeline.remove_clip": ("clip_id",),
    "timeline.trim_clip": ("clip_id", "source_start_us", "duration_us"),
}


def _typed_correlation_reference(
    plan_id: str,
    task_id: str,
    skill_id: str | None,
) -> str:
    digest = stable_digest(
        {
            "record_type": "agent_task_correlation",
            "plan_id": plan_id,
            "task_id": task_id,
            "skill_id": skill_id,
        }
    )
    return f"agent_corr_{digest[:32]}"


def _validate_context_digest(value: Any, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AgentTaskStateError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _execution_context_reference(context_digest: str) -> str:
    normalized = _validate_context_digest(
        context_digest,
        field_name="execution context digest",
    )
    reference = f"{_EXECUTION_CONTEXT_REFERENCE_PREFIX}{normalized}"
    try:
        return validate_identifier(reference, field_name="execution context reference")
    except ProjectValidationError as exc:
        raise AgentTaskStateError(str(exc)) from exc


def _record_execution_context_digest(record: AgentTaskRecord) -> str | None:
    matches = [
        reference[len(_EXECUTION_CONTEXT_REFERENCE_PREFIX) :]
        for reference in record.canonical_references
        if reference.startswith(_EXECUTION_CONTEXT_REFERENCE_PREFIX)
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise AgentTaskStateError(
            f"Agent Task {record.task_id!r} has ambiguous execution context evidence"
        )
    return _validate_context_digest(
        matches[0],
        field_name="durable execution context digest",
    )


@contextmanager
def _execution_correlation(correlation_id: str) -> Iterator[None]:
    try:
        normalized = validate_identifier(
            correlation_id,
            field_name="execution correlation_id",
        )
    except ProjectValidationError as exc:
        raise AgentTaskStateError(str(exc)) from exc
    token = _EXECUTION_CORRELATION.set(normalized)
    try:
        yield
    finally:
        _EXECUTION_CORRELATION.reset(token)


@contextmanager
def _execution_context(context_digest: str) -> Iterator[None]:
    normalized = _validate_context_digest(
        context_digest,
        field_name="execution context digest",
    )
    token = _EXECUTION_CONTEXT.set(normalized)
    try:
        yield
    finally:
        _EXECUTION_CONTEXT.reset(token)


class _RecoveryAgentTaskStore(_RuntimeAgentTaskStore):
    """Persist opaque execution-context evidence on the existing RUNNING task record."""

    def write(self, record: AgentTaskRecord) -> AgentTaskRecord:
        context_digest = _EXECUTION_CONTEXT.get()
        if context_digest is not None and record.status is AgentTaskStatus.RUNNING:
            reference = _execution_context_reference(context_digest)
            existing_contexts = [
                item
                for item in record.canonical_references
                if item.startswith(_EXECUTION_CONTEXT_REFERENCE_PREFIX)
            ]
            if existing_contexts and existing_contexts != [reference]:
                raise AgentTaskStateError(
                    "RUNNING Agent Task already carries different execution context evidence"
                )
            if reference not in record.canonical_references:
                record = replace(
                    record,
                    canonical_references=tuple(
                        dict.fromkeys((*record.canonical_references, reference))
                    ),
                )
        return super().write(record)


@dataclass(frozen=True)
class _CommittedTransactionEvidence:
    transaction_id: str
    command: str
    created_at: str
    context_digest: str | None
    result_references: dict[str, str]


class _CorrelatedProjectUnitOfWork(ProjectUnitOfWork):
    """ProjectUnitOfWork that binds execution evidence before its commit point."""

    def _execute_prepared(
        self,
        project_id: str,
        record_path: Any,
        record: dict[str, Any],
        changes: list[dict[str, Any]],
        history_before: Any,
        history_after: Any,
    ) -> None:
        correlation_id = _EXECUTION_CORRELATION.get()
        context_digest = _EXECUTION_CONTEXT.get()
        prepared = dict(record)
        if correlation_id is not None:
            prepared[_CORRELATION_FIELD] = correlation_id
        if context_digest is not None:
            prepared[_EXECUTION_CONTEXT_FIELD] = context_digest
        super()._execute_prepared(
            project_id,
            record_path,
            prepared,
            changes,
            history_before,
            history_after,
        )

    @staticmethod
    def _timeline_from_snapshot(
        snapshot: Any,
        *,
        label: str,
    ) -> TimelineDocument:
        if not isinstance(snapshot, Mapping):
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot must be a JSON object"
            )
        if snapshot.get("path") != MAIN_TIMELINE_PATH:
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot path is invalid"
            )
        exists = snapshot.get("exists")
        if not isinstance(exists, bool):
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot exists flag is invalid"
            )
        if not exists:
            if (
                snapshot.get("size") != 0
                or snapshot.get("sha256") is not None
                or snapshot.get("content_base64") is not None
            ):
                raise ProjectTransactionError(
                    f"correlated timeline {label} missing snapshot metadata is invalid"
                )
            return TimelineDocument()

        encoded = snapshot.get("content_base64")
        expected_size = snapshot.get("size")
        expected_sha = snapshot.get("sha256")
        if (
            not isinstance(encoded, str)
            or isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or not isinstance(expected_sha, str)
        ):
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot metadata is invalid"
            )
        try:
            content = base64.b64decode(encoded.encode("ascii"), validate=True)
        except (UnicodeEncodeError, ValueError) as exc:
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot base64 is invalid"
            ) from exc
        if len(content) != expected_size:
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot size is invalid"
            )
        if hashlib.sha256(content).hexdigest() != expected_sha:
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot digest is invalid"
            )
        try:
            payload = json.loads(content.decode("utf-8"))
            return TimelineDocument.from_dict(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, TimelineError) as exc:
            raise ProjectTransactionError(
                f"correlated timeline {label} snapshot content is invalid: {exc}"
            ) from exc

    @classmethod
    def _timeline_result_references(
        cls,
        record: Mapping[str, Any],
        command: str,
    ) -> dict[str, str]:
        if command not in {
            "timeline.create_track",
            "timeline.add_clip",
            "timeline.move_clip",
            "timeline.remove_clip",
            "timeline.trim_clip",
        }:
            return {}

        changes = record.get("changes")
        if not isinstance(changes, list):
            raise ProjectTransactionError(
                "correlated timeline transaction changes are invalid"
            )
        timeline_changes = [
            change
            for change in changes
            if isinstance(change, Mapping)
            and change.get("path") == MAIN_TIMELINE_PATH
        ]
        if len(timeline_changes) != 1:
            raise ProjectTransactionError(
                "correlated timeline transaction must contain exactly one main timeline change"
            )
        change = timeline_changes[0]
        before = cls._timeline_from_snapshot(change.get("before"), label="before")
        after = cls._timeline_from_snapshot(change.get("after"), label="after")

        before_tracks = {track.track_id: track for track in before.tracks}
        after_tracks = {track.track_id: track for track in after.tracks}
        before_clips = {
            clip.clip_id: (track.track_id, clip)
            for track in before.tracks
            for clip in track.clips
        }
        after_clips = {
            clip.clip_id: (track.track_id, clip)
            for track in after.tracks
            for clip in track.clips
        }

        if command == "timeline.create_track":
            added = sorted(set(after_tracks).difference(before_tracks))
            if len(added) != 1:
                raise ProjectTransactionError(
                    "correlated create_track transaction does not identify one created track"
                )
            return {"track_id": added[0]}

        if command == "timeline.add_clip":
            added = sorted(set(after_clips).difference(before_clips))
            if len(added) != 1:
                raise ProjectTransactionError(
                    "correlated add_clip transaction does not identify one created clip"
                )
            clip_id = added[0]
            track_id = after_clips[clip_id][0]
            return {"track_id": track_id, "clip_id": clip_id}

        if command == "timeline.remove_clip":
            removed = sorted(set(before_clips).difference(after_clips))
            if len(removed) != 1:
                raise ProjectTransactionError(
                    "correlated remove_clip transaction does not identify one removed clip"
                )
            clip_id = removed[0]
            track_id = before_clips[clip_id][0]
            return {"track_id": track_id, "clip_id": clip_id}

        changed = sorted(
            clip_id
            for clip_id in set(before_clips).intersection(after_clips)
            if (
                before_clips[clip_id][0] != after_clips[clip_id][0]
                or before_clips[clip_id][1] != after_clips[clip_id][1]
            )
        )
        if len(changed) != 1:
            raise ProjectTransactionError(
                f"correlated {command} transaction does not identify one changed clip"
            )
        clip_id = changed[0]
        return {"track_id": after_clips[clip_id][0], "clip_id": clip_id}

    def committed_by_correlation(
        self,
        project_id: str,
        correlation_id: str,
    ) -> _CommittedTransactionEvidence | None:
        """Return the unique committed transaction carrying this opaque correlation."""

        try:
            normalized = validate_identifier(
                correlation_id,
                field_name="execution correlation_id",
            )
        except ProjectValidationError as exc:
            raise ProjectTransactionError(str(exc)) from exc

        with self.project_store._lock:
            self._ensure_history_layout(project_id)
            # A prepared operation is not proof of a mutation. The canonical transaction
            # authority first rolls every interrupted prepared record back, then this
            # lookup considers committed records only.
            self._recover_prepared_operations(project_id)
            self.project_store.load_project(project_id)

            matches: list[_CommittedTransactionEvidence] = []
            transaction_root = self._history_dir(
                project_id,
                HISTORY_TRANSACTIONS_ROOT,
            )
            for path in sorted(transaction_root.glob("*.json"), key=lambda item: item.name):
                record = self._load_record(path)
                if record.get("phase") != "committed":
                    continue
                if record.get(_CORRELATION_FIELD) != normalized:
                    continue
                raw_transaction_id = record.get("transaction_id")
                try:
                    transaction_id = validate_identifier(
                        raw_transaction_id,
                        field_name="transaction_id",
                    )
                except ProjectValidationError as exc:
                    raise ProjectTransactionError(
                        f"correlated transaction {path.name!r} has invalid identity"
                    ) from exc
                if transaction_id != path.stem or record.get("record_id") != transaction_id:
                    raise ProjectTransactionError(
                        "correlated transaction record identity mismatch"
                    )
                command = record.get("command")
                created_at = record.get("created_at")
                if not isinstance(command, str) or not command.strip():
                    raise ProjectTransactionError(
                        "correlated transaction command is invalid"
                    )
                command = command.strip()
                if not isinstance(created_at, str) or not created_at:
                    raise ProjectTransactionError(
                        "correlated transaction created_at is invalid"
                    )
                raw_context_digest = record.get(_EXECUTION_CONTEXT_FIELD)
                context_digest: str | None = None
                if raw_context_digest is not None:
                    try:
                        context_digest = _validate_context_digest(
                            raw_context_digest,
                            field_name="correlated transaction execution context digest",
                        )
                    except AgentTaskStateError as exc:
                        raise ProjectTransactionError(str(exc)) from exc
                result_references = {
                    "transaction_id": transaction_id,
                    **self._timeline_result_references(record, command),
                }
                matches.append(
                    _CommittedTransactionEvidence(
                        transaction_id=transaction_id,
                        command=command,
                        created_at=created_at,
                        context_digest=context_digest,
                        result_references=result_references,
                    )
                )

            if len(matches) > 1:
                raise ProjectTransactionError(
                    f"execution correlation {normalized!r} matched multiple committed transactions"
                )
            return matches[0] if matches else None


def _validate_non_generation_action_inputs(
    action_id: str,
    inputs: Mapping[str, Any],
) -> None:
    """Validate planner input shapes with the same command/domain constructors."""

    try:
        if action_id == "production.create_scene":
            Scene(
                scene_id=inputs["scene_id"],
                title=inputs["title"],
                summary=inputs.get("summary", ""),
            )
            return
        if action_id == "production.create_shot":
            Shot(
                shot_id=inputs["shot_id"],
                scene_id=inputs["scene_id"],
                intent=inputs["intent"],
                reference_ids=inputs.get("reference_ids", ()),
            )
            return
        if action_id == "production.register_take":
            Take(
                take_id=inputs["take_id"],
                shot_id=inputs["shot_id"],
                reference_id=inputs["reference_id"],
                label=inputs.get("label", ""),
                notes=inputs.get("notes", ""),
            )
            return
        if action_id == "production.accept_take":
            validate_identifier(inputs["take_id"], field_name="take_id")
            validate_identifier(
                inputs.get("track_id", "production_video"),
                field_name="track_id",
            )
            clip_id = inputs.get("clip_id")
            if clip_id is not None:
                validate_identifier(clip_id, field_name="clip_id")
            TimelineClip(
                clip_id=clip_id or "clip_validation",
                reference_id="ref_validation",
                timeline_start_us=inputs["timeline_start_us"],
                source_start_us=inputs.get("source_start_us", 0),
                duration_us=inputs["duration_us"],
            )
            return
        if action_id == "timeline.create_track":
            CreateTrackCommand(**dict(inputs))
            return
        if action_id == "timeline.add_clip":
            AddClipCommand(**dict(inputs))
            return
        if action_id == "timeline.move_clip":
            MoveClipCommand(**dict(inputs))
            return
        if action_id == "timeline.remove_clip":
            RemoveClipCommand(**dict(inputs))
            return
        if action_id == "timeline.trim_clip":
            TrimClipCommand(**dict(inputs))
            return
        raise AgentPlanningError(
            f"input-shape contract is not defined for action {action_id!r}"
        )
    except (
        ProductionSemanticError,
        TimelineCommandError,
        TimelineError,
        ProjectValidationError,
        TypeError,
    ) as exc:
        raise AgentPlanningError(
            f"action {action_id!r} inputs are invalid: {exc}"
        ) from exc


class AgentPlanner(_RuntimeAgentPlanner):
    """Stage-16 Planner with command-level input validation before persistence."""

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
        for spec in plan.tasks:
            required = _REQUIRED_ACTION_INPUTS.get(spec.action_id)
            if required is None:
                raise AgentPlanningError(
                    f"required-input contract is not defined for action {spec.action_id!r}"
                )
            missing = [
                field_name
                for field_name in required
                if field_name not in spec.inputs or spec.inputs[field_name] is None
            ]
            if missing:
                raise AgentPlanningError(
                    f"action {spec.action_id!r} is missing required inputs: {missing!r}"
                )
            if spec.action_id == "generation.submit":
                if not isinstance(spec.inputs["inputs"], Mapping):
                    raise AgentPlanningError(
                        "generation.submit inputs must be a JSON object"
                    )
                contract = spec.inputs["contract"]
                if not isinstance(contract, Mapping):
                    raise AgentPlanningError(
                        "generation.submit contract must be a JSON object"
                    )
                try:
                    validate_identifier(
                        spec.inputs["shot_id"],
                        field_name="shot_id",
                    )
                    validate_identifier(
                        spec.inputs["model_id"],
                        field_name="model_id",
                    )
                    GenerationContract.from_dict(contract)
                    validate_identifier(
                        spec.inputs["idempotency_key"],
                        field_name="idempotency_key",
                    )
                except (GenerationValidationError, ProjectValidationError) as exc:
                    raise AgentPlanningError(
                        f"generation.submit required inputs are invalid: {exc}"
                    ) from exc
            else:
                _validate_non_generation_action_inputs(
                    spec.action_id,
                    spec.inputs,
                )
        return plan


class AgentTaskCoordinator(_RuntimeAgentTaskCoordinator):
    """Recover post-commit/pre-trace crashes from canonical transaction or Job evidence."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        if planner is None:
            planner = AgentPlanner(
                harness,
                skills=AgentSkillCatalog(harness.catalog),
            )
        if task_store is None:
            task_store = _RecoveryAgentTaskStore(harness.project_store)
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )
        self._transaction_evidence = _CorrelatedProjectUnitOfWork(
            self.project_store
        )
        # The same canonical Production/Timeline services remain authoritative; only
        # their existing UoW instance is replaced by a subclass that enriches the
        # prepared journal with execution correlation before any canonical write.
        self.harness.production.uow = self._transaction_evidence
        self.harness.timeline.unit_of_work = self._transaction_evidence

    @staticmethod
    def _known_input_references(spec: Any) -> tuple[str, ...]:
        values: list[str] = []
        for field_name in (
            "scene_id",
            "shot_id",
            "take_id",
            "reference_id",
            "track_id",
            "clip_id",
        ):
            value = spec.inputs.get(field_name)
            if isinstance(value, str) and value:
                values.append(value)
        return tuple(dict.fromkeys(values))

    def _recovered_success_trace(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
        *,
        created_at: str,
        result_references: Mapping[str, str],
        extra_references: Sequence[str] = (),
        context_digest: str | None = None,
    ) -> AgentTraceRecord:
        spec = plan.task(record.task_id)
        typed_reference = _typed_correlation_reference(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        )
        recovered_context_digest = (
            context_digest
            or _record_execution_context_digest(record)
            or plan.context_digest
        )
        references = tuple(
            dict.fromkeys(
                (
                    record.project_id,
                    *(self._known_input_references(spec)),
                    *extra_references,
                    *result_references.values(),
                    typed_reference,
                )
            )
        )
        return AgentTraceRecord(
            trace_id=f"agent_trace_{uuid.uuid4().hex}",
            project_id=record.project_id,
            created_at=created_at,
            context_digest=recovered_context_digest,
            action_id=spec.action_id,
            input_digest=self._expected_input_digest(spec),
            canonical_references=references,
            policy=spec.policy,
            status=AgentTraceStatus.SUCCEEDED,
            result_references=dict(result_references),
        )

    def _transaction_recovery_trace(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTraceRecord | None:
        spec = plan.task(record.task_id)
        if spec.action_id == "generation.submit":
            return None
        correlation_id = _typed_correlation_reference(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        )
        try:
            evidence = self._transaction_evidence.committed_by_correlation(
                record.project_id,
                correlation_id,
            )
        except ProjectTransactionError as exc:
            raise AgentTaskStateError(
                f"could not inspect correlated project transaction: {exc}"
            ) from exc
        if evidence is None:
            return None
        if evidence.command != spec.action_id:
            raise AgentTaskStateError(
                "correlated committed transaction action does not match durable Agent Task"
            )
        created_at = evidence.created_at
        if record.started_at is not None and created_at < record.started_at:
            created_at = record.started_at
        return self._recovered_success_trace(
            plan,
            record,
            created_at=created_at,
            result_references=evidence.result_references,
            context_digest=evidence.context_digest,
        )

    def _generation_recovery_trace(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTraceRecord | None:
        spec = plan.task(record.task_id)
        if spec.action_id != "generation.submit":
            return None
        idempotency_key = spec.inputs.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise AgentTaskStateError(
                "durable generation task lost its required idempotency key"
            )
        matches = [
            job
            for job in self.harness.jobs.list(record.project_id)
            if job.idempotency_key == idempotency_key
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise AgentTaskStateError(
                "generation idempotency key matched multiple durable Jobs"
            )
        job = matches[0]

        contract_raw = spec.inputs.get("contract")
        request_inputs = spec.inputs.get("inputs")
        if not isinstance(contract_raw, Mapping) or not isinstance(request_inputs, Mapping):
            raise AgentTaskStateError(
                "durable generation task lost normalized request semantics"
            )
        try:
            expected_contract = GenerationContract.from_dict(contract_raw).to_dict()
        except GenerationValidationError as exc:
            raise AgentTaskStateError(
                f"durable generation contract is invalid: {exc}"
            ) from exc
        expected_inputs = portable_json(
            dict(request_inputs),
            field_name="Agent generation recovery inputs",
        )
        request = job.request
        exact_request = (
            request.get("project_id") == record.project_id
            and request.get("shot_id") == spec.inputs.get("shot_id")
            and request.get("model_id") == spec.inputs.get("model_id")
            and request.get("inputs") == expected_inputs
            and request.get("generation_contract") == expected_contract
        )
        if not exact_request:
            raise AgentTaskStateError(
                "generation idempotency key is bound to request semantics that do not match the Agent Task"
            )

        created_at = record.started_at or job.created_at
        result_references = {"job_id": job.job_id}
        attempt = job.current_attempt
        if attempt is not None:
            result_references["attempt_id"] = attempt.attempt_id
            if attempt.output_reference_id is not None:
                result_references["output_reference_id"] = attempt.output_reference_id
            if attempt.take_id is not None:
                result_references["take_id"] = attempt.take_id
        return self._recovered_success_trace(
            plan,
            record,
            created_at=created_at,
            result_references=result_references,
            extra_references=(
                spec.inputs["shot_id"],
                job.job_id,
            ),
        )

    def _reconcile_running(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTaskRecord:
        trace = self._correlated_trace_for(plan, record)
        if trace is not None:
            return super()._reconcile_running(plan, record)

        recovered = self._transaction_recovery_trace(plan, record)
        if recovered is None:
            recovered = self._generation_recovery_trace(plan, record)
        if recovered is not None:
            # Append evidence first. If the process stops after this append but before
            # the task transition, the next reopen consumes this exact correlated trace.
            self.harness.traces.append(recovered)
            return self.tasks.transition(
                record,
                AgentTaskStatus.SUCCEEDED,
                trace=recovered,
            )
        return super()._reconcile_running(plan, record)

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        # Hold the same project/task lease while observing execution context and while
        # the runtime coordinator transitions READY -> RUNNING -> terminal. Agent Task
        # writes do not participate in AgentContextBuilder, so the subsequent Harness
        # snapshot is byte-for-byte the same observation unless canonical state changes,
        # which this lease prevents.
        with self.project_store._lock, self.tasks.records.project_lock(project_id):
            plan = self.plans.get(project_id, plan_id)
            spec = plan.task(task_id)
            correlation_id = _typed_correlation_reference(
                plan.plan_id,
                spec.task_id,
                spec.skill_id,
            )
            try:
                snapshot = self.harness.context.build(
                    project_id,
                    shot_id=spec.target_shot_id,
                )
            except Exception:
                # Preserve the Harness preparation-failure path. No canonical mutation
                # can occur when the same context build fails before dispatch.
                with _execution_correlation(correlation_id):
                    return super().execute_task(
                        project_id=project_id,
                        plan_id=plan.plan_id,
                        task_id=spec.task_id,
                        runtime_inputs=runtime_inputs,
                    )

            with (
                _execution_correlation(correlation_id),
                _execution_context(snapshot.digest),
            ):
                return super().execute_task(
                    project_id=project_id,
                    plan_id=plan.plan_id,
                    task_id=spec.task_id,
                    runtime_inputs=runtime_inputs,
                )
