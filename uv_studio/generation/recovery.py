"""Restart recovery for durable generation Jobs.

In-process FastAPI background tasks are deliberately not treated as durable workers.
If the process exits, persisted queued/running Jobs are converted to explicit failed
attempts on the next application startup. The user can then retry through the normal
Job API, which re-runs D-017 authorization instead of silently spending/contacting a
provider after restart.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import replace

from uv_studio.projects.models import utc_now_iso
from uv_studio.projects.store import ProjectStore, ProjectStoreError

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


def _persist(manager: GenerationJobManager, job: GenerationJob) -> GenerationJob:
    """Persist one recovery transition through the existing project task store."""

    manager.records.write(job.project_id, job.job_id, job.to_dict())
    return job


def requeue_failed_generation_job(
    manager: GenerationJobManager,
    project_id: str,
    job_id: str,
) -> GenerationJob:
    """Move one failed Job back to queued after retry authorization succeeds."""

    with manager.project_store._lock:
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
    """Fail abandoned queued/running Jobs so they become explicitly retryable.

    Recovery never launches a provider call. This is important for D-017: a remote
    or non-free retry after restart must be a new explicit action with fresh one-shot
    authorization rather than an automatic replay of a pre-crash grant.
    """

    recovered: list[GenerationJob] = []
    with manager.project_store._lock:
        manager.project_store.load_project(project_id)
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
    from opening other projects.
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
                "generation recovery skipped project %s: %s",
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
