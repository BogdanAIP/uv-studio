from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uv_studio.generation.jobs import (
    GenerationJobManager,
    GenerationStatus,
    generation_request_digest,
)
from uv_studio.generation.models import GenerationContract
from uv_studio.generation.recovery import (
    INTERRUPTED_QUEUED_ERROR,
    INTERRUPTED_RUNNING_ERROR,
    recover_interrupted_generation_jobs,
    recover_interrupted_project_jobs,
    requeue_failed_generation_job,
)
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class GenerationRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Generation recovery",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_generation_recovery",
        )
        self.manager = GenerationJobManager(self.store)
        self.contract = GenerationContract(
            fixed_constraints=("same character",),
            editable_variables=("camera",),
            forbidden_changes=("identity",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _request(self, prompt: str) -> tuple[str, dict[str, object]]:
        return generation_request_digest(
            project_id=self.project.project_id,
            shot_id="shot_recovery",
            model_id="uv.image.standard",
            capability_id="image.generate",
            offer_id="native_videoclaw.image_generate",
            adapter_id="native_videoclaw",
            inputs={"prompt": prompt},
            contract=self.contract,
        )

    def _job(self, *, key: str, prompt: str):
        digest, request = self._request(prompt)
        job, reused = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key=key,
            request_digest=digest,
            request=request,
        )
        self.assertFalse(reused)
        return job

    def _ensure_production(self) -> ProductionSemanticService:
        production = ProductionSemanticService(self.store)
        state = production.state(self.project.project_id)
        if not any(item.scene_id == "scene_recovery" for item in state.scenes):
            production.create_scene(
                self.project.project_id,
                scene_id="scene_recovery",
                title="Recovery scene",
            )
        state = production.state(self.project.project_id)
        if not any(item.shot_id == "shot_recovery" for item in state.shots):
            production.create_shot(
                self.project.project_id,
                shot_id="shot_recovery",
                scene_id="scene_recovery",
                intent="Recover generated materialization",
            )
        return production

    def _register_running_artifact(self, running, *, artifact_id: str) -> ProjectReference:
        attempt = running.current_attempt
        self.assertIsNotNone(attempt)
        relative_path = f"artifacts/generated_{attempt.attempt_id}.png"
        output = self.store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        output.write_bytes(b"crash-recovery-image")
        artifact = ProjectReference(
            id=artifact_id,
            kind="image",
            path=relative_path,
            metadata={
                "generation": {
                    "job_id": running.job_id,
                    "attempt_id": attempt.attempt_id,
                    "model_id": "uv.image.standard",
                }
            },
        )
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, artifact),
        )
        return artifact

    def test_restart_fails_abandoned_queued_and_running_jobs_without_replaying(self) -> None:
        queued = self._job(key="idem_recovery_queued", prompt="queued")
        running_job = self._job(key="idem_recovery_running", prompt="running")
        running = self.manager.start_execution(self.project.project_id, running_job.job_id)
        running_attempt_id = running.current_attempt.attempt_id

        completed_job = self._job(key="idem_recovery_done", prompt="done")
        completed_running = self.manager.start_execution(self.project.project_id, completed_job.job_id)
        completed = self.manager.succeed(
            self.project.project_id,
            completed_job.job_id,
            attempt_id=completed_running.current_attempt.attempt_id,
            output_reference_id="artifact_recovery_done",
            take_id="take_recovery_done",
        )

        recovered = recover_interrupted_project_jobs(self.manager, self.project.project_id)
        recovered_by_id = {job.job_id: job for job in recovered}
        self.assertEqual(set(recovered_by_id), {queued.job_id, running.job_id})

        recovered_queued = recovered_by_id[queued.job_id]
        self.assertEqual(recovered_queued.status, GenerationStatus.FAILED)
        self.assertEqual(len(recovered_queued.attempts), 1)
        self.assertEqual(recovered_queued.attempts[0].status, GenerationStatus.FAILED)
        self.assertEqual(recovered_queued.attempts[0].error, INTERRUPTED_QUEUED_ERROR)

        recovered_running = recovered_by_id[running.job_id]
        self.assertEqual(recovered_running.status, GenerationStatus.FAILED)
        self.assertEqual(len(recovered_running.attempts), 1)
        self.assertEqual(recovered_running.attempts[0].attempt_id, running_attempt_id)
        self.assertEqual(recovered_running.attempts[0].status, GenerationStatus.FAILED)
        self.assertEqual(recovered_running.attempts[0].error, INTERRUPTED_RUNNING_ERROR)

        durable_completed = self.manager.get(self.project.project_id, completed.job_id)
        self.assertEqual(durable_completed, completed)
        self.assertEqual(durable_completed.status, GenerationStatus.SUCCEEDED)

    def test_restart_quarantines_bytes_only_generation_then_fails_job(self) -> None:
        job = self._job(key="idem_recovery_bytes_only", prompt="bytes only")
        running = self.manager.start_execution(self.project.project_id, job.job_id)
        attempt = running.current_attempt
        self.assertIsNotNone(attempt)
        relative_path = f"artifacts/generated_{attempt.attempt_id}.png"
        output = self.store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        output.write_bytes(b"bytes-without-project-reference")

        recovered = recover_interrupted_project_jobs(self.manager, self.project.project_id)
        self.assertEqual([item.job_id for item in recovered], [job.job_id])
        self.assertFalse(output.exists())
        quarantined = tuple(
            self.store.root.glob(
                f".uv-recovered-orphan-{self.project.project_id}-*-{output.name}"
            )
        )
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_bytes(), b"bytes-without-project-reference")
        durable = self.manager.get(self.project.project_id, job.job_id)
        self.assertEqual(durable.status, GenerationStatus.FAILED)
        self.assertEqual(durable.current_attempt.error, INTERRUPTED_RUNNING_ERROR)

    def test_restart_completes_artifact_only_generation_without_provider_replay(self) -> None:
        production = self._ensure_production()
        job = self._job(key="idem_recovery_artifact_only", prompt="artifact only")
        running = self.manager.start_execution(self.project.project_id, job.job_id)
        artifact = self._register_running_artifact(
            running,
            artifact_id="artifact_recovery_partial",
        )

        recovered = recover_interrupted_project_jobs(self.manager, self.project.project_id)
        self.assertEqual(recovered, ())
        durable = self.manager.get(self.project.project_id, job.job_id)
        self.assertEqual(durable.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(durable.current_attempt.output_reference_id, artifact.id)
        self.assertIsNotNone(durable.current_attempt.take_id)
        take = production.state(self.project.project_id).take(durable.current_attempt.take_id)
        self.assertEqual(take.reference_id, artifact.id)
        self.assertEqual(take.shot_id, "shot_recovery")

        # Recovery is idempotent once the Job is terminal and must not duplicate Takes.
        take_ids = production.state(self.project.project_id).shot("shot_recovery").take_ids
        self.assertEqual(recover_interrupted_project_jobs(self.manager, self.project.project_id), ())
        self.assertEqual(
            production.state(self.project.project_id).shot("shot_recovery").take_ids,
            take_ids,
        )

    def test_restart_completes_existing_take_before_job_success(self) -> None:
        production = self._ensure_production()
        job = self._job(key="idem_recovery_take_only", prompt="take exists")
        running = self.manager.start_execution(self.project.project_id, job.job_id)
        artifact = self._register_running_artifact(
            running,
            artifact_id="artifact_recovery_take_exists",
        )
        production.register_take(
            self.project.project_id,
            take_id="take_recovery_existing",
            shot_id="shot_recovery",
            reference_id=artifact.id,
            label="Existing crash-boundary Take",
        )

        recovered = recover_interrupted_project_jobs(self.manager, self.project.project_id)
        self.assertEqual(recovered, ())
        durable = self.manager.get(self.project.project_id, job.job_id)
        self.assertEqual(durable.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(durable.current_attempt.output_reference_id, artifact.id)
        self.assertEqual(durable.current_attempt.take_id, "take_recovery_existing")
        self.assertEqual(
            production.state(self.project.project_id).shot("shot_recovery").take_ids,
            ("take_recovery_existing",),
        )

    def test_explicit_retry_requeues_recovered_job_before_new_attempt(self) -> None:
        job = self._job(key="idem_recovery_retry", prompt="retry")
        running = self.manager.start_execution(self.project.project_id, job.job_id)
        first_attempt_id = running.current_attempt.attempt_id

        recovered = recover_interrupted_project_jobs(self.manager, self.project.project_id)[0]
        self.assertEqual(recovered.status, GenerationStatus.FAILED)
        self.assertEqual(recovered.current_attempt.attempt_id, first_attempt_id)

        queued = requeue_failed_generation_job(
            self.manager,
            self.project.project_id,
            recovered.job_id,
        )
        self.assertEqual(queued.status, GenerationStatus.QUEUED)
        self.assertEqual(len(queued.attempts), 1)
        self.assertEqual(queued.attempts[0].status, GenerationStatus.FAILED)

        retry_running = self.manager.start_execution(self.project.project_id, queued.job_id)
        self.assertEqual(retry_running.status, GenerationStatus.RUNNING)
        self.assertEqual(len(retry_running.attempts), 2)
        self.assertEqual(retry_running.attempts[0].attempt_id, first_attempt_id)
        self.assertEqual(retry_running.attempts[1].retry_index, 1)
        self.assertNotEqual(retry_running.attempts[1].attempt_id, first_attempt_id)

    def test_store_wide_recovery_returns_durable_recovered_ids(self) -> None:
        queued = self._job(key="idem_recovery_store", prompt="store")
        recovered_ids = recover_interrupted_generation_jobs(self.store)
        self.assertEqual(recovered_ids, (queued.job_id,))
        durable = GenerationJobManager(self.store).get(self.project.project_id, queued.job_id)
        self.assertEqual(durable.status, GenerationStatus.FAILED)
        self.assertEqual(durable.current_attempt.error, INTERRUPTED_QUEUED_ERROR)

    def test_fastapi_lifespan_runs_recovery_before_serving(self) -> None:
        from uv_studio.server import app, lifespan

        async def exercise() -> None:
            with (
                patch("uv_studio.server.get_project_store", return_value=self.store) as store_factory,
                patch("uv_studio.server.recover_interrupted_generation_jobs") as recover,
            ):
                async with lifespan(app):
                    recover.assert_called_once_with(self.store)
                    store_factory.assert_called_once_with()

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
