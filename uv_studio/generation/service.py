"""Named-model generation orchestration over existing UV project authorities."""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Protocol

from uv_studio.capabilities.authorization import (
    ExecutionPreparation,
    OneShotAuthorizationStore,
    prepare_execution,
)
from uv_studio.capabilities.models import CapabilityOffer, MediaKind, OfferAvailability
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.models import PROJECT_SCHEMA_VERSION, ProjectReference
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore
from uv_studio.projects.transactions import ProjectUnitOfWork

from .jobs import (
    GenerationExecutionAttempt,
    GenerationJob,
    GenerationJobConflict,
    GenerationJobManager,
    GenerationStatus,
    generation_request_digest,
)
from .models import (
    GENERATION_FEATURE_CONTINUATION,
    GenerationContract,
    GenerationValidationError,
    ModelDefinition,
    ModelRegistry,
)


class GenerationServiceError(RuntimeError):
    pass


class GenerationExecutionUnavailable(GenerationServiceError):
    pass


class GenerationOutputError(GenerationServiceError):
    pass


class GenerationExecutor(Protocol):
    """Transport seam for one bounded output.

    Executors receive durable UV-owned request semantics. Provider-private continuation
    state such as KV caches, latents, session handles, sliding windows or anchor caches
    remains adapter-owned/reconstructible and must not become Project Store truth.
    Returned metadata is durable provenance only.
    """

    def execute(
        self,
        *,
        project_id: str,
        job: GenerationJob,
        attempt: GenerationExecutionAttempt,
        model: ModelDefinition,
        offer: CapabilityOffer,
        inputs: Mapping[str, Any],
        contract: GenerationContract,
        output_path: Path,
    ) -> Mapping[str, Any]: ...


class UnavailableGenerationExecutor:
    """Fail-closed default until a concrete mapped generation transport is executable."""

    def execute(self, **_: Any) -> Mapping[str, Any]:
        raise GenerationExecutionUnavailable(
            "selected generation model has no executable generation transport in this installation"
        )


@dataclass(frozen=True)
class GenerationSubmissionPreparation:
    model: ModelDefinition
    offer: CapabilityOffer
    contract: GenerationContract
    request_digest: str
    request: dict[str, Any]
    execution: ExecutionPreparation

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model.to_dict(),
            "request_digest": self.request_digest,
            "request": dict(self.request),
            "authorization": self.execution.to_dict(),
        }


@dataclass(frozen=True)
class GenerationSubmissionResult:
    job: GenerationJob
    reused: bool

    def to_dict(self) -> dict[str, Any]:
        return {"reused": self.reused, "job": self.job.to_dict()}


class GenerationService:
    """One project-scoped generation path from named model to Take candidate."""

    def __init__(
        self,
        project_store: ProjectStore,
        model_registry: ModelRegistry,
        authorizations: OneShotAuthorizationStore,
        executor: GenerationExecutor | None = None,
    ) -> None:
        self.project_store = project_store
        self.model_registry = model_registry
        self.authorizations = authorizations
        self.executor = executor or UnavailableGenerationExecutor()
        self.jobs = GenerationJobManager(project_store)
        self.production = ProductionSemanticService(project_store)
        self.transactions = ProjectUnitOfWork(project_store)

    def prepare(
        self,
        *,
        project_id: str,
        shot_id: str,
        model_id: str,
        inputs: Mapping[str, Any],
        contract: GenerationContract,
    ) -> GenerationSubmissionPreparation:
        project = self.project_store.load_project(project_id)
        self.production.state(project_id).shot(shot_id)
        model = self.model_registry.get(model_id)
        offer = self.model_registry.capability_registry.get_offer(model.offer_id)
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise GenerationExecutionUnavailable(
                f"selected model execution is {offer.availability.value}: {offer.reason}"
            )

        references = {item.id for item in (*project.sources, *project.artifacts)}
        if contract.approved_reference_id is not None:
            if contract.approved_reference_id not in references:
                raise GenerationValidationError(
                    "approved_reference_id is not registered in this project"
                )

        if contract.continuation_source_reference_id is not None:
            if GENERATION_FEATURE_CONTINUATION not in offer.features:
                raise GenerationValidationError(
                    "selected model does not support generation continuation"
                )
            if contract.continuation_source_reference_id not in references:
                raise GenerationValidationError(
                    "continuation_source_reference_id is not registered in this project"
                )

        digest, request = generation_request_digest(
            project_id=project_id,
            shot_id=shot_id,
            model_id=model.model_id,
            capability_id=model.capability_id,
            offer_id=offer.offer_id,
            adapter_id=offer.adapter_id,
            inputs=inputs,
            contract=contract,
        )
        execution = prepare_execution(
            project_id=project_id,
            offer=offer,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload=request,
        )
        return GenerationSubmissionPreparation(
            model=model,
            offer=offer,
            contract=contract,
            request_digest=digest,
            request=request,
            execution=execution,
        )

    def submit(
        self,
        *,
        project_id: str,
        shot_id: str,
        model_id: str,
        inputs: Mapping[str, Any],
        contract: GenerationContract,
        idempotency_key: str,
        authorization_token: str | None,
    ) -> GenerationSubmissionResult:
        # One cross-runtime project critical section owns preparation, idempotency
        # lookup, D-017 grant consumption and durable Job reservation. Agent, GUI,
        # API and script callers therefore cannot reserve two Jobs for one key or
        # consume a second grant after another runtime has already committed it.
        with self.jobs.records.project_lock(project_id):
            prepared = self.prepare(
                project_id=project_id,
                shot_id=shot_id,
                model_id=model_id,
                inputs=inputs,
                contract=contract,
            )
            for existing in self.jobs.list(project_id):
                if existing.idempotency_key != idempotency_key:
                    continue
                if existing.request_digest != prepared.request_digest:
                    raise GenerationJobConflict(
                        "idempotency key is already bound to a different generation request"
                    )
                return GenerationSubmissionResult(job=existing, reused=True)

            self.authorizations.consume(authorization_token, prepared.execution)
            job, reused = self.jobs.create_or_reuse(
                project_id=project_id,
                idempotency_key=idempotency_key,
                request_digest=prepared.request_digest,
                request=prepared.request,
            )
            return GenerationSubmissionResult(job=job, reused=reused)

    def run(self, project_id: str, job_id: str) -> GenerationJob:
        """Execute a queued Job or explicitly retry a failed Job."""

        running = self.jobs.start_execution(project_id, job_id)
        attempt = running.current_attempt
        if attempt is None:  # pragma: no cover - GenerationJob invariant
            raise GenerationServiceError("generation job did not create an execution attempt")

        request = running.request
        model_id = request.get("model_id")
        shot_id = request.get("shot_id")
        inputs = request.get("inputs")
        contract_raw = request.get("generation_contract")
        if not isinstance(model_id, str) or not isinstance(shot_id, str):
            return self._fail_running(running, attempt, "generation request lost model/shot identity")
        if not isinstance(inputs, Mapping) or not isinstance(contract_raw, Mapping):
            return self._fail_running(running, attempt, "generation request lost inputs/contract")

        staged_output: Path | None = None
        try:
            model = self.model_registry.get(model_id)
            offer = self.model_registry.capability_registry.get_offer(model.offer_id)
            contract = GenerationContract.from_dict(contract_raw)
            mapping = request.get("execution_mapping")
            if not isinstance(mapping, Mapping):
                raise GenerationServiceError("generation request lost execution mapping")
            if (
                mapping.get("capability_id") != model.capability_id
                or mapping.get("offer_id") != offer.offer_id
                or mapping.get("adapter_id") != offer.adapter_id
            ):
                raise GenerationServiceError(
                    "persisted generation execution mapping no longer matches named model"
                )
            if offer.availability is not OfferAvailability.AVAILABLE:
                raise GenerationExecutionUnavailable(
                    f"selected model execution is {offer.availability.value}: {offer.reason}"
                )

            artifact_id = f"artifact_{uuid.uuid4().hex}"
            take_id = f"take_{uuid.uuid4().hex}"
            suffix = self._suffix_for(model.output_kind)
            relative_path = f"artifacts/generated_{attempt.attempt_id}{suffix}"
            output_path = self.project_store.resolve_project_file(
                project_id,
                relative_path,
                allowed_roots=("artifacts",),
            )
            if output_path.exists() or output_path.is_symlink():
                raise GenerationOutputError("allocated generation output path already exists")

            # Provider execution can be long-running. Keep its output outside every
            # canonical project directory so archive recovery can continue to observe
            # the old durable project state until final publication begins.
            with tempfile.NamedTemporaryFile(
                prefix=f".uv-generation-{attempt.attempt_id}-",
                suffix=suffix,
                dir=self.project_store.root,
                delete=False,
            ) as handle:
                staged_output = Path(handle.name)
            staged_output.unlink()

            executor_metadata = self.executor.execute(
                project_id=project_id,
                job=running,
                attempt=attempt,
                model=model,
                offer=offer,
                inputs=dict(inputs),
                contract=contract,
                output_path=staged_output,
            )
            if not isinstance(executor_metadata, Mapping):
                raise GenerationOutputError("generation executor metadata must be a JSON object")
            self._validate_output(staged_output)

            # Publication is the consequence-bearing transition. The shared
            # cross-runtime project fence owns job revalidation, byte publication,
            # Project artifact registration, Take registration and durable success.
            with self.jobs.records.project_lock(project_id):
                current = self.jobs.get(project_id, job_id)
                if current.status is GenerationStatus.CANCELLED:
                    return current
                if current.status is not GenerationStatus.RUNNING:
                    raise GenerationJobConflict(
                        f"generation job changed to {current.status.value!r} before materialization"
                    )

                fenced_output = self.project_store.resolve_project_file(
                    project_id,
                    relative_path,
                    allowed_roots=("artifacts",),
                )
                if fenced_output.exists() or fenced_output.is_symlink():
                    raise GenerationOutputError("allocated generation output path already exists")

                final_written = False
                try:
                    os.replace(staged_output, fenced_output)
                    final_written = True
                    reference = self._register_artifact(
                        project_id=project_id,
                        artifact_id=artifact_id,
                        relative_path=relative_path,
                        output_path=fenced_output,
                        model=model,
                        offer=offer,
                        job=current,
                        attempt=attempt,
                        contract=contract,
                        executor_metadata=executor_metadata,
                    )
                    self.production.register_take(
                        project_id,
                        take_id=take_id,
                        shot_id=shot_id,
                        reference_id=reference.id,
                        label=f"Generated · {model.title}",
                        notes=f"Generation job {current.job_id}; attempt {attempt.attempt_id}",
                    )
                    return self.jobs.succeed(
                        project_id,
                        job_id,
                        attempt_id=attempt.attempt_id,
                        output_reference_id=reference.id,
                        take_id=take_id,
                    )
                except Exception:
                    if final_written:
                        try:
                            current_project = self.project_store.load_project(project_id)
                            registered = any(
                                item.id == artifact_id for item in current_project.artifacts
                            )
                        except Exception:
                            # A failed read after a possible transaction commit is
                            # ambiguous. Preserve bytes that may already be durable.
                            registered = True
                        if not registered:
                            fenced_output.unlink(missing_ok=True)
                    raise
        except Exception as exc:
            try:
                current = self.jobs.get(project_id, job_id)
                if current.status is GenerationStatus.RUNNING:
                    self.jobs.fail(
                        project_id,
                        job_id,
                        attempt_id=attempt.attempt_id,
                        error=f"{type(exc).__name__}: {exc}",
                    )
            except Exception:
                pass
            raise
        finally:
            if staged_output is not None:
                staged_output.unlink(missing_ok=True)

    def cancel(self, project_id: str, job_id: str) -> GenerationJob:
        return self.jobs.cancel(project_id, job_id)

    def _fail_running(
        self,
        job: GenerationJob,
        attempt: GenerationExecutionAttempt,
        message: str,
    ) -> GenerationJob:
        return self.jobs.fail(
            job.project_id,
            job.job_id,
            attempt_id=attempt.attempt_id,
            error=message,
        )

    def _register_artifact(
        self,
        *,
        project_id: str,
        artifact_id: str,
        relative_path: str,
        output_path: Path,
        model: ModelDefinition,
        offer: CapabilityOffer,
        job: GenerationJob,
        attempt: GenerationExecutionAttempt,
        contract: GenerationContract,
        executor_metadata: Mapping[str, Any],
    ) -> ProjectReference:
        lineage = None
        if contract.continuation_source_reference_id is not None:
            lineage = {
                "kind": "continuation",
                "source_reference_id": contract.continuation_source_reference_id,
            }
        metadata = {
            "size_bytes": output_path.stat().st_size,
            "sha256": self._sha256_file(output_path),
            "generation": {
                "job_id": job.job_id,
                "attempt_id": attempt.attempt_id,
                "model_id": model.model_id,
                "capability_id": model.capability_id,
                "offer_id": offer.offer_id,
                "adapter_id": offer.adapter_id,
                "request_digest": job.request_digest,
                "contract": contract.to_dict(),
                "lineage": lineage,
            },
            "executor": dict(executor_metadata),
        }
        reference = ProjectReference(
            id=artifact_id,
            kind=model.output_kind.value,
            path=relative_path,
            metadata=metadata,
        )
        project = self.project_store.load_project(project_id)
        if project.schema_version != PROJECT_SCHEMA_VERSION:
            raise GenerationOutputError("project schema changed during generation")
        updated = replace(project, artifacts=(*project.artifacts, reference))
        self.transactions.commit(
            project_id,
            command="generation.register_output",
            documents={PROJECT_FILENAME: updated.to_dict()},
        )
        return reference

    @staticmethod
    def _validate_output(path: Path) -> None:
        if not path.exists() or not path.is_file() or path.is_symlink():
            raise GenerationOutputError("generation executor did not materialize a regular output file")
        if path.stat().st_size <= 0:
            raise GenerationOutputError("generation executor produced an empty output file")

    @staticmethod
    def _suffix_for(kind: MediaKind) -> str:
        return {
            MediaKind.IMAGE: ".png",
            MediaKind.VIDEO: ".mp4",
            MediaKind.AUDIO: ".wav",
            MediaKind.TEXT: ".txt",
        }[kind]

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
