"""Restart recovery for durable generation Jobs and interrupted media publication.

In-process FastAPI background tasks are deliberately not treated as durable workers.
If the process exits, persisted queued/running Jobs are reconciled on the next
application startup. Provider work is never replayed automatically. Canonical
managed output bytes that were published without owning metadata are moved out of
the project tree before abandoned Jobs are failed; a Generation attempt whose
artifact metadata is already durable is completed from canonical evidence instead.
"""

from __future__ import annotations

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

_MANAGED_OUTPUT_ROOTS = ("artifacts", "exports")
_CRASH_IDENTIFIABLE_OUTPUT_NAME = re.compile(
    r"^(?:sub_[0-9a-f]{32}|generated_attempt_[0-9a-f]{32})(?:[._-]|$)"
)


def _persist(manager: GenerationJobManager, job: GenerationJob) -> GenerationJob:
    """Persist one recovery transition through the existing project task store."""

    manager.records.write(job.project_id, job.job_id, job.to_dict())
    return job


def _registered_output_paths(project: ProjectDocument) -> set[str]:
    return {item.path for item in (*project.sources, *project.artifacts)}


def _quarantine_unregistered_managed_outputs(
    store: ProjectStore,
    project_id: str,
) -> tuple[Path, ...]:
    """Move crash-identifiable unregistered publisher bytes out of the project tree.

    Ordinary unregistered project files remain portable for compatibility. Only
    current publishers with self-identifying final names (WebVTT ``sub_<uuid>`` and
    Generation ``generated_attempt_<uuid>``) are inferred from the filesystem.
    Arbitrary-path ``timeline.assemble`` is recovered only through its durable
    publication marker, never by guessing from the filename.
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
) -> tuple[ProjectReference, ...]:
    attempt = job.current_attempt
    if attempt is None:
        return ()
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


def _reconcile_running_materialization(
    manager: GenerationJobManager,
    production: ProductionSemanticService,
    job: GenerationJob,
) -> GenerationJob | None:
    """Complete a crash-interrupted Generation publication without provider replay.

    Once the generated artifact ProjectReference is durable, its provenance binds it
    to the exact running Job/Attempt. Recovery may therefore finish only the missing
    local Take/Job transitions. If no artifact reference is durable, provider outcome
    remains unknown and normal restart recovery fails the Job instead.
    """

    if job.status is not GenerationStatus.RUNNING:
        return None
    attempt = job.current_attempt
    if attempt is None:
        raise GenerationJobError("running generation job lost current attempt")

    project = manager.project_store.load_project(job.project_id)
    artifacts = _matching_generation_artifacts(project, job)
    if not artifacts:
        return None
    if len(artifacts) != 1:
        raise GenerationJobError(
            f"running generation attempt has {len(artifacts)} durable output references"
        )
    artifact = artifacts[0]
    output = manager.project_store.resolve_project_file(
        job.project_id,
        artifact.path,
        must_exist=True,
        allowed_roots=("artifacts",),
    )
    if output.is_symlink() or not output.is_file() or output.stat().st_size <= 0:
        raise GenerationJobError("durable generation reference does not resolve to output bytes")

    shot_id = job.request.get("shot_id")
    if not isinstance(shot_id, str) or not shot_id:
        raise GenerationJobError("generation recovery lost shot identity")
    state = production.state(job.project_id)
    matching_takes = tuple(
        take
        for take in state.takes
        if take.reference_id == artifact.id and take.shot_id == shot_id
    )
    if len(matching_takes) > 1:
        raise GenerationJobError("generation recovery found multiple Takes for one attempt output")
    if matching_takes:
        take_id = matching_takes[0].take_id
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
                f"attempt {attempt.attempt_id} after application restart"
            ),
        )

    completed = manager.succeed(
        job.project_id,
        job.job_id,
        attempt_id=attempt.attempt_id,
        output_reference_id=artifact.id,
        take_id=take_id,
    )
    logger.warning(
        "generation job %s recovered as succeeded from durable artifact %s without provider replay",
        job.job_id,
        artifact.id,
    )
    return completed


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
    artifact is failed so explicit retry can obtain fresh D-017 authorization. A
    running Job whose exact artifact ProjectReference is already durable is completed
    locally by restoring/creating its Take and then recording Job success.
    """

    recovered: list[GenerationJob] = []
    production = ProductionSemanticService(manager.project_store)
    with manager.records.project_lock(project_id):
        # ProjectUnitOfWork has its own durable prepared journal. Recover it first so
        # publication reconciliation never treats a half-applied artifact/Take commit
        # as durable truth and then later has that UOW roll it back underneath a Job.
        ProjectUnitOfWork(manager.project_store).history(project_id)
        manager.project_store.load_project(project_id)

        # Arbitrary-path timeline publication is identified only by a durable marker
        # written immediately before canonical os.replace. Current self-identifying
        # WebVTT/Generation names can be reconciled directly from the filesystem.
        recover_managed_publications(manager.project_store, project_id)
        _quarantine_unregistered_managed_outputs(manager.project_store, project_id)

        # Complete any consequence-bearing Generation materialization that crossed
        # the durable ProjectReference boundary before the process died.
        for job in manager.list(project_id):
            if job.status is GenerationStatus.RUNNING:
                _reconcile_running_materialization(manager, production, job)

        # Re-read after materialization reconciliation. Only work with no durable
        # materialized outcome remains abandoned and becomes explicitly retryable.
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
