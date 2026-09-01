"""Restart recovery for durable generation Jobs and interrupted media publication.

In-process FastAPI background tasks are deliberately not treated as durable workers.
If the process exits, persisted queued/running Jobs are reconciled on the next
application startup. Provider work is never replayed automatically. Canonical
managed output bytes that were published without owning metadata are moved out of
the project tree before abandoned Jobs are failed; Generation attempts whose
artifact metadata is already durable are completed from canonical evidence instead.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from dataclasses import replace
from pathlib import Path

from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.models import ProjectDocument, ProjectReference, utc_now_iso
from uv_studio.projects.publication import recover_managed_publications
from uv_studio.projects.store import ProjectStore, ProjectStoreError
from uv_studio.projects.transactions import ProjectUnitOfWork

from .jobs import (
    GenerationExecutionAttempt,
    GenerationJob,
    GenerationJobConflict,
    GenerationJobError,
    GenerationJobManager,
    GenerationStatus,
)

logger = logging.getLogger(__name__)

INTERRUPTED_QUEUED_ERROR = (
    "application restarted before the queued generation execution was confirmed; "
    "explicit retry is required"
)
INTERRUPTED_RUNNING_ERROR = (
    "application restarted while generation was running; provider outcome is unknown "
    "and no automatic rerun was attempted; explicit retry is required"
)

_MANAGED_OUTPUT_ROOTS = ("sources", "artifacts", "exports")
_CRASH_IDENTIFIABLE_OUTPUT_NAME = re.compile(
    r"^(?:src_[0-9a-f]{32}|sub_[0-9a-f]{32}|generated_attempt_[0-9a-f]{32})(?:[._-]|$)"
)


def _persist(manager: GenerationJobManager, job: GenerationJob) -> GenerationJob:
    """Persist one recovery transition through the existing project task store."""

    manager.records.write(job.project_id, job.job_id, job.to_dict())
    return job


def _registered_output_paths(project: ProjectDocument) -> set[str]:
    return {item.path for item in (*project.sources, *project.artifacts)}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quarantine_unregistered_managed_outputs(
    store: ProjectStore,
    project_id: str,
) -> tuple[Path, ...]:
    """Move crash-identifiable unregistered publisher bytes out of the project tree.

    Ordinary unregistered project files remain portable for compatibility. Current
    source upload ``src_<uuid>``, WebVTT ``sub_<uuid>`` and Generation
    ``generated_attempt_<uuid>`` final names are self-identifying and can therefore
    be recovered after hard process loss. Arbitrary-path ``timeline.assemble`` is
    recovered only through its durable publication marker, never by filename guess.
    """

    project = store.load_project(project_id)
    registered = _registered_output_paths(project)
    project_dir = store.project_directory(project_id)
    quarantined: list[Path] = []
    for root_name in _MANAGED_OUTPUT_ROOTS:
        root = project_dir / root_name
        if root.is_symlink():
            raise ProjectStoreError(f"managed output root must not be a symlink: {root_name!r}")
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_symlink():
                raise ProjectStoreError(f"managed output entry must not be a symlink: {path}")
            if not path.is_file():
                continue
            relative = path.relative_to(project_dir).as_posix()
            if relative in registered or _CRASH_IDENTIFIABLE_OUTPUT_NAME.match(path.name) is None:
                continue
            destination = store.root / (
                f".uv-recovered-orphan-{project_id}-{uuid.uuid4().hex}-{path.name}"
            )
            if destination.exists() or destination.is_symlink():
                raise ProjectStoreError(
                    f"managed output quarantine path unexpectedly exists: {destination.name!r}"
                )
            os.replace(path, destination)
            quarantined.append(destination)
            logger.warning(
                "moved unregistered managed output out of project %s: %s -> %s",
                project_id,
                relative,
                destination.name,
            )
    return tuple(quarantined)


def _matching_generation_artifacts(
    project: ProjectDocument,
    job: GenerationJob,
    attempt: GenerationExecutionAttempt,
) -> tuple[ProjectReference, ...]:
    matches: list[ProjectReference] = []
    for artifact in project.artifacts:
        generation = artifact.metadata.get("generation")
        if not isinstance(generation, dict):
            continue
        if (
            generation.get("job_id") == job.job_id
            and generation.get("attempt_id") == attempt.attempt_id
        ):
            matches.append(artifact)
    return tuple(matches)


def _unreconciled_generation_artifacts(
    project: ProjectDocument,
    job: GenerationJob,
) -> tuple[ProjectReference, ...]:
    """Return durable Job artifacts whose own attempt is not yet a proven success."""

    attempts = {attempt.attempt_id: attempt for attempt in job.attempts}
    pending: list[ProjectReference] = []
    for artifact in project.artifacts:
        generation = artifact.metadata.get("generation")
        if not isinstance(generation, dict) or generation.get("job_id") != job.job_id:
            continue
        attempt_id = generation.get("attempt_id")
        attempt = attempts.get(attempt_id) if isinstance(attempt_id, str) else None
        if attempt is None or attempt.status is not GenerationStatus.SUCCEEDED:
            pending.append(artifact)
    return tuple(pending)


def _validate_generation_artifact(
    manager: GenerationJobManager,
    job: GenerationJob,
    attempt: GenerationExecutionAttempt,
    artifact: ProjectReference,
) -> Path:
    """Prove that durable metadata still describes the exact attempt output bytes."""

    generation = artifact.metadata.get("generation")
    if not isinstance(generation, dict):
        raise GenerationJobError("durable generation artifact lost provenance metadata")

    mapping = job.request.get("execution_mapping")
    contract = job.request.get("generation_contract")
    if not isinstance(mapping, dict) or not isinstance(contract, dict):
        raise GenerationJobError("generation recovery lost execution mapping or contract")
    expected = {
        "job_id": job.job_id,
        "attempt_id": attempt.attempt_id,
        "model_id": job.request.get("model_id"),
        "capability_id": mapping.get("capability_id"),
        "offer_id": mapping.get("offer_id"),
        "adapter_id": mapping.get("adapter_id"),
        "request_digest": job.request_digest,
    }
    for field_name, expected_value in expected.items():
        if not isinstance(expected_value, str) or not expected_value:
            raise GenerationJobError(
                f"generation recovery request lost {field_name} authority"
            )
        if generation.get(field_name) != expected_value:
            raise GenerationJobError(
                f"durable generation artifact {field_name} does not match Job authority"
            )
    if generation.get("contract") != contract:
        raise GenerationJobError("durable generation artifact contract does not match Job authority")

    expected_name = f"generated_{attempt.attempt_id}"
    if not (
        Path(artifact.path).name == expected_name
        or Path(artifact.path).name.startswith(expected_name + ".")
    ):
        raise GenerationJobError("durable generation artifact path does not match attempt identity")

    size_bytes = artifact.metadata.get("size_bytes")
    sha256 = artifact.metadata.get("sha256")
    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or size_bytes <= 0
        or not isinstance(sha256, str)
        or len(sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in sha256)
    ):
        raise GenerationJobError("durable generation artifact lost size/digest authority")

    output = manager.project_store.resolve_project_file(
        job.project_id,
        artifact.path,
        must_exist=True,
        allowed_roots=("artifacts",),
    )
    if output.is_symlink() or not output.is_file():
        raise GenerationJobError("durable generation reference does not resolve to regular output bytes")
    stat_result = output.stat()
    if stat_result.st_size != size_bytes:
        raise GenerationJobError("durable generation output size does not match persisted metadata")
    if _sha256_file(output) != sha256:
        raise GenerationJobError("durable generation output digest does not match persisted metadata")
    return output


def _mark_reconciled_success(
    manager: GenerationJobManager,
    job: GenerationJob,
    *,
    attempt_index: int,
    artifact_id: str,
    take_id: str,
) -> GenerationJob:
    """Finish one attempt from proven durable local materialization evidence.

    Legacy runtimes could append a newer retry after an older attempt had already
    crossed the durable ProjectReference boundary. Recovery therefore repairs the
    artifact-owning attempt in place instead of rewriting history to pretend that the
    artifact belongs to ``attempts[-1]``. Only repair of the final/current attempt
    changes the Job's overall status to ``SUCCEEDED``.
    """

    if not 0 <= attempt_index < len(job.attempts):
        raise GenerationJobError("generation recovery attempt index is out of bounds")
    attempt = job.attempts[attempt_index]
    if attempt.status is GenerationStatus.SUCCEEDED:
        if attempt.output_reference_id != artifact_id or attempt.take_id != take_id:
            raise GenerationJobError("succeeded generation attempt disagrees with durable materialization")
        return job
    if attempt.status not in {
        GenerationStatus.RUNNING,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    }:
        raise GenerationJobError(
            f"generation materialization cannot be reconciled from status {attempt.status.value!r}"
        )

    ended_at = utc_now_iso()
    completed = replace(
        attempt,
        status=GenerationStatus.SUCCEEDED,
        ended_at=ended_at,
        output_reference_id=artifact_id,
        take_id=take_id,
        error=None,
    )
    attempts = list(job.attempts)
    attempts[attempt_index] = completed
    is_current = attempt_index == len(attempts) - 1
    return _persist(
        manager,
        replace(
            job,
            status=(GenerationStatus.SUCCEEDED if is_current else job.status),
            updated_at=ended_at,
            attempts=tuple(attempts),
        ),
    )


def _reconcile_attempt_materialization(
    manager: GenerationJobManager,
    production: ProductionSemanticService,
    job: GenerationJob,
    *,
    attempt_index: int,
    artifact: ProjectReference,
) -> GenerationJob:
    attempt = job.attempts[attempt_index]
    _validate_generation_artifact(manager, job, attempt, artifact)

    shot_id = job.request.get("shot_id")
    if not isinstance(shot_id, str) or not shot_id:
        raise GenerationJobError("generation recovery lost shot identity")
    state = production.state(job.project_id)
    artifact_takes = tuple(take for take in state.takes if take.reference_id == artifact.id)
    if any(take.shot_id != shot_id for take in artifact_takes):
        raise GenerationJobError("generation recovery found Take bound to the wrong Shot")
    if len(artifact_takes) > 1:
        raise GenerationJobError("generation recovery found multiple Takes for one attempt output")
    if artifact_takes:
        take_id = artifact_takes[0].take_id
    else:
        generation = artifact.metadata.get("generation")
        model_id = generation.get("model_id") if isinstance(generation, dict) else None
        label = f"Recovered generated output · {model_id}" if model_id else "Recovered generated output"
        take_id = f"take_{uuid.uuid4().hex}"
        production.register_take(
            job.project_id,
            take_id=take_id,
            shot_id=shot_id,
            reference_id=artifact.id,
            label=label,
            notes=(
                f"Recovered generation job {job.job_id}; "
                f"attempt {attempt.attempt_id} after interrupted local publication"
            ),
        )

    completed = _mark_reconciled_success(
        manager,
        job,
        attempt_index=attempt_index,
        artifact_id=artifact.id,
        take_id=take_id,
    )
    logger.warning(
        "generation job %s attempt %s recovered as succeeded from verified durable artifact %s without provider replay",
        job.job_id,
        attempt.attempt_id,
        artifact.id,
    )
    return completed


def _reconcile_materializations(
    manager: GenerationJobManager,
    production: ProductionSemanticService,
    job: GenerationJob,
) -> GenerationJob:
    """Repair every non-succeeded attempt that already owns a durable artifact."""

    project = manager.project_store.load_project(job.project_id)
    attempt_indexes = {attempt.attempt_id: index for index, attempt in enumerate(job.attempts)}
    grouped: dict[str, list[ProjectReference]] = {}
    for artifact in project.artifacts:
        generation = artifact.metadata.get("generation")
        if not isinstance(generation, dict) or generation.get("job_id") != job.job_id:
            continue
        attempt_id = generation.get("attempt_id")
        if not isinstance(attempt_id, str) or attempt_id not in attempt_indexes:
            raise GenerationJobError(
                "durable generation artifact references an unknown Job attempt"
            )
        grouped.setdefault(attempt_id, []).append(artifact)

    current_job = job
    for attempt_id, attempt_index in sorted(
        attempt_indexes.items(), key=lambda item: item[1]
    ):
        artifacts = grouped.get(attempt_id, [])
        if not artifacts:
            continue
        if len(artifacts) != 1:
            raise GenerationJobError(
                f"generation attempt has {len(artifacts)} durable output references"
            )
        attempt = current_job.attempts[attempt_index]
        if attempt.status is GenerationStatus.SUCCEEDED:
            continue
        current_job = _reconcile_attempt_materialization(
            manager,
            production,
            current_job,
            attempt_index=attempt_index,
            artifact=artifacts[0],
        )
    return current_job


def requeue_failed_generation_job(
    manager: GenerationJobManager,
    project_id: str,
    job_id: str,
) -> GenerationJob:
    """Move one failed Job back to queued after retry authorization succeeds."""

    with manager.records.project_lock(project_id):
        job = manager.get(project_id, job_id)
        if job.status is not GenerationStatus.FAILED:
            raise GenerationJobConflict("only a failed generation job can be requeued")
        project = manager.project_store.load_project(project_id)
        if _unreconciled_generation_artifacts(project, job):
            raise GenerationJobConflict(
                "generation job has a durable artifact pending recovery"
            )
        return _persist(
            manager,
            replace(
                job,
                status=GenerationStatus.QUEUED,
                updated_at=utc_now_iso(),
            ),
        )


def recover_interrupted_project_jobs(
    manager: GenerationJobManager,
    project_id: str,
) -> tuple[GenerationJob, ...]:
    """Reconcile crash publication, then fail only truly abandoned queued/running Jobs.

    Recovery never launches a provider call. A running Job with no durable generated
    artifact is failed so explicit retry can obtain fresh D-017 authorization. Any
    attempt whose exact artifact ProjectReference is already durable can be completed
    locally from verified bytes/provenance, including historical older-attempt split
    states left by a runtime that retried after publishing an earlier artifact.
    """

    recovered: list[GenerationJob] = []
    production = ProductionSemanticService(manager.project_store)
    with manager.records.project_lock(project_id):
        # ProjectUnitOfWork has its own durable prepared journal. Recover it first so
        # publication reconciliation never treats a half-applied artifact/Take commit
        # as durable truth and then later has that UOW roll it back underneath a Job.
        ProjectUnitOfWork(manager.project_store).history(project_id)
        manager.project_store.load_project(project_id)

        # Arbitrary-path timeline publication is identified only by a durable marker.
        # Current source/WebVTT/Generation names are self-identifying and can be
        # quarantined directly when bytes exist without owning Project metadata.
        recover_managed_publications(manager.project_store, project_id)
        _quarantine_unregistered_managed_outputs(manager.project_store, project_id)

        # Reconcile every artifact-owning attempt, not merely attempts[-1]. This is
        # required for historical states in which an older failed attempt published a
        # ProjectReference before a later retry was appended. Already-succeeded
        # attempts are intentionally not recreated here; their Take may have been
        # removed by explicit user Undo and remains governed by UOW history.
        for job in manager.list(project_id):
            _reconcile_materializations(manager, production, job)

        # Re-read after materialization reconciliation. Only current work with no
        # durable materialized outcome remains abandoned and becomes retryable.
        for job in manager.list(project_id):
            if job.status is GenerationStatus.QUEUED:
                now = utc_now_iso()
                interrupted = GenerationExecutionAttempt(
                    attempt_id=f"attempt_{uuid.uuid4().hex}",
                    retry_index=len(job.attempts),
                    status=GenerationStatus.FAILED,
                    started_at=now,
                    ended_at=now,
                    error=INTERRUPTED_QUEUED_ERROR,
                )
                updated = replace(
                    job,
                    status=GenerationStatus.FAILED,
                    updated_at=now,
                    attempts=(*job.attempts, interrupted),
                )
            elif job.status is GenerationStatus.RUNNING:
                current = job.current_attempt
                if current is None:  # pragma: no cover - GenerationJob invariant
                    raise GenerationJobError("running generation job lost current attempt")
                ended_at = utc_now_iso()
                interrupted = replace(
                    current,
                    status=GenerationStatus.FAILED,
                    ended_at=ended_at,
                    error=INTERRUPTED_RUNNING_ERROR,
                )
                updated = replace(
                    job,
                    status=GenerationStatus.FAILED,
                    updated_at=ended_at,
                    attempts=(*job.attempts[:-1], interrupted),
                )
            else:
                continue
            recovered.append(_persist(manager, updated))
    return tuple(recovered)


def recover_interrupted_generation_jobs(store: ProjectStore) -> tuple[str, ...]:
    """Best-effort startup reconciliation across healthy projects.

    Damaged projects/job records are never rewritten to make startup appear healthy.
    They are logged and isolated so one damaged project does not prevent UV Studio
    from opening other projects. Publication reconciliation runs under the same
    cross-runtime project fence before abandoned Jobs are classified.
    """

    recovered_ids: list[str] = []
    try:
        projects, project_diagnostics = store.list_projects_with_diagnostics()
    except (OSError, ProjectStoreError) as exc:
        logger.error("generation recovery could not enumerate projects: %s", exc)
        return ()

    for diagnostic in project_diagnostics:
        logger.warning(
            "generation recovery skipped invalid project %s: %s",
            diagnostic.project_id,
            diagnostic.error,
        )

    manager = GenerationJobManager(store)
    for project in projects:
        try:
            recovered = recover_interrupted_project_jobs(manager, project.project_id)
        except (GenerationJobError, ProjectStoreError, OSError, ValueError) as exc:
            logger.error(
                "generation/publication recovery skipped project %s: %s",
                project.project_id,
                exc,
            )
            continue
        for job in recovered:
            logger.warning(
                "generation job %s recovered as failed after application restart",
                job.job_id,
            )
            recovered_ids.append(job.job_id)
    return tuple(recovered_ids)
