"""Typed portable replacement-candidate state for Stage 4B preparation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .media_ranges import ProjectMediaRange
from .models import ProjectValidationError, validate_identifier, validate_project_relative_path
from .replacement_plan import (
    ReplacementPlan,
    ReplacementPlanError,
    ReplacementPlanNotFound,
    ReplacementPlanStore,
)
from .store import ProjectStore, ProjectStoreError

REPLACEMENT_CANDIDATE_SCHEMA_VERSION = 1
REPLACEMENT_CANDIDATE_PATH = "timeline/replacement-candidates.json"
CANDIDATE_STAGES = frozenset({"sample", "full"})


class ReplacementCandidateError(ProjectValidationError):
    """Invalid, stale or inconsistent replacement candidate state."""


class ReplacementCandidateNotFound(ReplacementCandidateError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise ReplacementCandidateError(str(exc)) from exc


def _project_path(value: Any, *, field_name: str) -> str:
    try:
        path = validate_project_relative_path(value)
    except ProjectValidationError as exc:
        raise ReplacementCandidateError(f"{field_name}: {exc}") from exc
    if not path.startswith("artifacts/"):
        raise ReplacementCandidateError(f"{field_name} must be under artifacts/")
    return path


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise ReplacementCandidateError(f"{field_name} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ReplacementCandidateError(f"{field_name} must be a lowercase SHA-256 digest") from exc
    return value


def _optional_identifier(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, field_name=field_name)


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    if unknown:
        raise ReplacementCandidateError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    missing = allowed.difference(data)
    if missing:
        raise ReplacementCandidateError(f"{kind} is missing fields: {sorted(missing)!r}")


def replacement_plan_sha256(plan: ReplacementPlan) -> str:
    payload = json.dumps(
        plan.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ReplacementCandidate:
    candidate_id: str
    edit_id: str
    source_path: str
    start_us: int
    end_us: int
    plan_sha256: str
    method_class: str
    stage: str
    artifact_id: str
    artifact_path: str
    execution_run_id: str | None = None
    schema_version: int = REPLACEMENT_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != REPLACEMENT_CANDIDATE_SCHEMA_VERSION
        ):
            raise ReplacementCandidateError(
                f"unsupported replacement candidate schema: {self.schema_version!r}"
            )
        object.__setattr__(self, "candidate_id", _identifier(self.candidate_id, field_name="candidate_id"))
        object.__setattr__(self, "edit_id", _identifier(self.edit_id, field_name="edit_id"))
        try:
            target = ProjectMediaRange(
                source_path=self.source_path,
                start_us=self.start_us,
                end_us=self.end_us,
            )
        except ProjectValidationError as exc:
            raise ReplacementCandidateError(str(exc)) from exc
        object.__setattr__(self, "source_path", target.source_path)
        object.__setattr__(self, "start_us", target.start_us)
        object.__setattr__(self, "end_us", target.end_us)
        object.__setattr__(self, "plan_sha256", _sha256(self.plan_sha256, field_name="plan_sha256"))
        if self.method_class not in {
            "deterministic_edit",
            "prepared_asset",
            "generative_transform",
        }:
            raise ReplacementCandidateError("candidate method_class is not a supported plan method")
        if self.stage not in CANDIDATE_STAGES:
            raise ReplacementCandidateError(f"stage must be one of {sorted(CANDIDATE_STAGES)!r}")
        if self.method_class != "generative_transform" and self.stage != "full":
            raise ReplacementCandidateError("only generative candidates may use stage='sample'")
        object.__setattr__(self, "artifact_id", _identifier(self.artifact_id, field_name="artifact_id"))
        object.__setattr__(self, "artifact_path", _project_path(self.artifact_path, field_name="artifact_path"))
        object.__setattr__(
            self,
            "execution_run_id",
            _optional_identifier(self.execution_run_id, field_name="execution_run_id"),
        )

    @property
    def target_identity(self) -> tuple[str, str, int, int]:
        return (self.edit_id, self.source_path, self.start_us, self.end_us)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "edit_id": self.edit_id,
            "source_path": self.source_path,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "plan_sha256": self.plan_sha256,
            "method_class": self.method_class,
            "stage": self.stage,
            "artifact_id": self.artifact_id,
            "artifact_path": self.artifact_path,
            "execution_run_id": self.execution_run_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementCandidate":
        if not isinstance(data, Mapping):
            raise ReplacementCandidateError("replacement candidate must be an object")
        allowed = {
            "schema_version",
            "candidate_id",
            "edit_id",
            "source_path",
            "start_us",
            "end_us",
            "plan_sha256",
            "method_class",
            "stage",
            "artifact_id",
            "artifact_path",
            "execution_run_id",
        }
        _strict_fields(data, allowed=allowed, kind="replacement candidate")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SampleApproval:
    edit_id: str
    candidate_id: str
    plan_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "edit_id", _identifier(self.edit_id, field_name="edit_id"))
        object.__setattr__(self, "candidate_id", _identifier(self.candidate_id, field_name="candidate_id"))
        object.__setattr__(self, "plan_sha256", _sha256(self.plan_sha256, field_name="plan_sha256"))

    def to_dict(self) -> dict[str, str]:
        return {
            "edit_id": self.edit_id,
            "candidate_id": self.candidate_id,
            "plan_sha256": self.plan_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SampleApproval":
        if not isinstance(data, Mapping):
            raise ReplacementCandidateError("sample approval must be an object")
        allowed = {"edit_id", "candidate_id", "plan_sha256"}
        _strict_fields(data, allowed=allowed, kind="sample approval")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ReplacementCandidateState:
    candidates: tuple[ReplacementCandidate, ...] = ()
    sample_approvals: tuple[SampleApproval, ...] = ()
    schema_version: int = REPLACEMENT_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != REPLACEMENT_CANDIDATE_SCHEMA_VERSION
        ):
            raise ReplacementCandidateError(
                f"unsupported replacement candidate state schema: {self.schema_version!r}"
            )
        candidates = tuple(self.candidates)
        approvals = tuple(self.sample_approvals)
        if not all(isinstance(item, ReplacementCandidate) for item in candidates):
            raise ReplacementCandidateError("candidates must contain ReplacementCandidate values")
        if not all(isinstance(item, SampleApproval) for item in approvals):
            raise ReplacementCandidateError("sample_approvals must contain SampleApproval values")
        candidate_ids = [item.candidate_id for item in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ReplacementCandidateError("candidate_id values must be unique")
        approval_edits = [item.edit_id for item in approvals]
        if len(approval_edits) != len(set(approval_edits)):
            raise ReplacementCandidateError("only one current sample approval may exist per edit_id")
        known = {item.candidate_id: item for item in candidates}
        for approval in approvals:
            candidate = known.get(approval.candidate_id)
            if candidate is None:
                raise ReplacementCandidateError("sample approval references an unknown candidate")
            if candidate.edit_id != approval.edit_id:
                raise ReplacementCandidateError("sample approval edit_id does not match its candidate")
            if candidate.stage != "sample" or candidate.method_class != "generative_transform":
                raise ReplacementCandidateError("sample approval must reference a generative sample candidate")
            if candidate.plan_sha256 != approval.plan_sha256:
                raise ReplacementCandidateError("sample approval plan digest does not match its candidate")
        object.__setattr__(self, "candidates", tuple(sorted(candidates, key=lambda item: item.candidate_id)))
        object.__setattr__(self, "sample_approvals", tuple(sorted(approvals, key=lambda item: item.edit_id)))

    def get(self, candidate_id: str) -> ReplacementCandidate:
        normalized = _identifier(candidate_id, field_name="candidate_id")
        for candidate in self.candidates:
            if candidate.candidate_id == normalized:
                return candidate
        raise ReplacementCandidateNotFound(normalized)

    def add_candidate(self, candidate: ReplacementCandidate) -> "ReplacementCandidateState":
        if not isinstance(candidate, ReplacementCandidate):
            raise ReplacementCandidateError("add_candidate requires ReplacementCandidate")
        return ReplacementCandidateState(
            candidates=(*self.candidates, candidate),
            sample_approvals=self.sample_approvals,
        )

    def approve_sample(self, approval: SampleApproval) -> "ReplacementCandidateState":
        return ReplacementCandidateState(
            candidates=self.candidates,
            sample_approvals=tuple(item for item in self.sample_approvals if item.edit_id != approval.edit_id)
            + (approval,),
        )

    def remove_candidate(self, candidate_id: str) -> "ReplacementCandidateState":
        candidate = self.get(candidate_id)
        remaining = tuple(item for item in self.candidates if item.candidate_id != candidate.candidate_id)
        approvals = tuple(item for item in self.sample_approvals if item.candidate_id != candidate.candidate_id)
        return ReplacementCandidateState(candidates=remaining, sample_approvals=approvals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidates": [item.to_dict() for item in self.candidates],
            "sample_approvals": [item.to_dict() for item in self.sample_approvals],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementCandidateState":
        if not isinstance(data, Mapping):
            raise ReplacementCandidateError("replacement candidate state must be an object")
        allowed = {"schema_version", "candidates", "sample_approvals"}
        _strict_fields(data, allowed=allowed, kind="replacement candidate state")
        if not isinstance(data["candidates"], list) or not isinstance(data["sample_approvals"], list):
            raise ReplacementCandidateError("candidates and sample_approvals must be lists")
        return cls(
            schema_version=data["schema_version"],
            candidates=tuple(ReplacementCandidate.from_dict(item) for item in data["candidates"]),
            sample_approvals=tuple(SampleApproval.from_dict(item) for item in data["sample_approvals"]),
        )


class ReplacementCandidateStore:
    """Atomic candidate state with current-plan and artifact validation."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _state_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                REPLACEMENT_CANDIDATE_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ReplacementCandidateError(str(exc)) from exc

    def load(self, project_id: str) -> ReplacementCandidateState:
        path = self._state_path(project_id)
        if not path.exists():
            return ReplacementCandidateState()
        if not path.is_file() or path.is_symlink():
            raise ReplacementCandidateError("replacement candidate state path must be a regular file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReplacementCandidateError("replacement candidate state is malformed JSON") from exc
        except OSError as exc:
            raise ReplacementCandidateError("replacement candidate state could not be read") from exc
        return ReplacementCandidateState.from_dict(data)

    def _write(self, project_id: str, state: ReplacementCandidateState) -> ReplacementCandidateState:
        self.project_store._atomic_write_json(self._state_path(project_id), state.to_dict())
        return state

    def current_plan(self, project_id: str, edit_id: str) -> ReplacementPlan:
        try:
            return ReplacementPlanStore(self.project_store).validate_project(project_id).get(edit_id)
        except (ReplacementPlanError, ReplacementPlanNotFound, ProjectStoreError) as exc:
            raise ReplacementCandidateError(
                f"replacement candidate requires a current valid ReplacementPlan: {exc}"
            ) from exc

    def make_candidate(
        self,
        project_id: str,
        *,
        candidate_id: str,
        edit_id: str,
        stage: str,
        artifact_id: str,
        artifact_path: str,
        execution_run_id: str | None = None,
    ) -> ReplacementCandidate:
        plan = self.current_plan(project_id, edit_id)
        return ReplacementCandidate(
            candidate_id=candidate_id,
            edit_id=plan.edit_id,
            source_path=plan.source_path,
            start_us=plan.start_us,
            end_us=plan.end_us,
            plan_sha256=replacement_plan_sha256(plan),
            method_class=plan.method_class,
            stage=stage,
            artifact_id=artifact_id,
            artifact_path=artifact_path,
            execution_run_id=execution_run_id,
        )

    def register(self, project_id: str, candidate: ReplacementCandidate) -> ReplacementCandidateState:
        if not isinstance(candidate, ReplacementCandidate):
            raise ReplacementCandidateError("register requires ReplacementCandidate")
        with self.project_store._lock:
            self._validate_candidate(project_id, candidate, require_sample_for_full=True)
            current = self.load(project_id)
            return self._write(project_id, current.add_candidate(candidate))

    def approve_sample(self, project_id: str, candidate_id: str) -> ReplacementCandidateState:
        with self.project_store._lock:
            state = self.load(project_id)
            candidate = state.get(candidate_id)
            self._validate_candidate(project_id, candidate, require_sample_for_full=False)
            if candidate.method_class != "generative_transform" or candidate.stage != "sample":
                raise ReplacementCandidateError("only a current generative sample candidate can be approved")
            approval = SampleApproval(
                edit_id=candidate.edit_id,
                candidate_id=candidate.candidate_id,
                plan_sha256=candidate.plan_sha256,
            )
            return self._write(project_id, state.approve_sample(approval))

    def remove(self, project_id: str, candidate_id: str) -> ReplacementCandidateState:
        with self.project_store._lock:
            state = self.load(project_id)
            return self._write(project_id, state.remove_candidate(candidate_id))

    def validate_candidate(self, project_id: str, candidate_id: str) -> ReplacementCandidate:
        candidate = self.load(project_id).get(candidate_id)
        self._validate_candidate(project_id, candidate, require_sample_for_full=True)
        return candidate

    def _validate_candidate(
        self,
        project_id: str,
        candidate: ReplacementCandidate,
        *,
        require_sample_for_full: bool,
    ) -> None:
        plan = self.current_plan(project_id, candidate.edit_id)
        plan_identity = (plan.edit_id, plan.source_path, plan.start_us, plan.end_us)
        if candidate.target_identity != plan_identity:
            raise ReplacementCandidateError("candidate target no longer matches the current approved plan")
        digest = replacement_plan_sha256(plan)
        if candidate.plan_sha256 != digest:
            raise ReplacementCandidateError("candidate is stale because its approved plan changed")
        if candidate.method_class != plan.method_class:
            raise ReplacementCandidateError("candidate method_class does not match the approved plan")

        try:
            artifact_path = self.project_store.resolve_project_file(
                project_id,
                candidate.artifact_path,
                must_exist=True,
                allowed_roots=("artifacts",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ReplacementCandidateError(f"candidate artifact is not a current project artifact: {exc}") from exc
        if not artifact_path.is_file() or artifact_path.is_symlink() or artifact_path.stat().st_size <= 0:
            raise ReplacementCandidateError("candidate artifact must be a non-empty regular project file")
        project = self.project_store.load_project(project_id)
        matching = [
            item
            for item in project.artifacts
            if item.id == candidate.artifact_id and item.path == candidate.artifact_path
        ]
        if len(matching) != 1:
            raise ReplacementCandidateError("candidate artifact must be registered exactly once in Project Store")

        if (
            require_sample_for_full
            and candidate.method_class == "generative_transform"
            and candidate.stage == "full"
        ):
            state = self.load(project_id)
            approval = next(
                (
                    item
                    for item in state.sample_approvals
                    if item.edit_id == candidate.edit_id and item.plan_sha256 == candidate.plan_sha256
                ),
                None,
            )
            if approval is None:
                raise ReplacementCandidateError(
                    "full generative candidate requires an approved sample for the current plan"
                )
            sample = state.get(approval.candidate_id)
            self._validate_candidate(project_id, sample, require_sample_for_full=False)
