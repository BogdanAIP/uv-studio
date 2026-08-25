from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.generation.jobs import (
    GenerationJobConflict,
    GenerationJobManager,
    GenerationStatus,
    generation_request_digest,
)
from uv_studio.generation.models import GenerationContract
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class GenerationJobManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Generation jobs",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_generation_jobs",
        )
        self.manager = GenerationJobManager(self.store)
        self.contract = GenerationContract(
            fixed_constraints=("same character",),
            editable_variables=("camera",),
            forbidden_changes=("identity",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _request(self, *, prompt: str = "portrait") -> tuple[str, dict[str, object]]:
        return generation_request_digest(
            project_id=self.project.project_id,
            shot_id="shot_1",
            model_id="uv.image.standard",
            capability_id="image.generate",
            offer_id="native_videoclaw.image_generate",
            adapter_id="native_videoclaw",
            inputs={"prompt": prompt, "seed": 7},
            contract=self.contract,
        )

    def test_same_key_same_digest_reuses_job_without_new_execution(self) -> None:
        digest, request = self._request()
        first, first_reused = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_same_request",
            request_digest=digest,
            request=request,
        )
        started = self.manager.start_execution(self.project.project_id, first.job_id)
        attempt_id = started.current_attempt.attempt_id
        succeeded = self.manager.succeed(
            self.project.project_id,
            first.job_id,
            attempt_id=attempt_id,
            output_reference_id="artifact_generation_1",
            take_id="take_generation_1",
        )

        replayed, replayed_flag = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_same_request",
            request_digest=digest,
            request=request,
        )

        self.assertFalse(first_reused)
        self.assertTrue(replayed_flag)
        self.assertEqual(replayed.job_id, first.job_id)
        self.assertEqual(replayed.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(len(replayed.attempts), 1)
        self.assertEqual(replayed.attempts[0].attempt_id, attempt_id)
        self.assertEqual(succeeded, replayed)

    def test_same_key_different_request_fails_closed(self) -> None:
        first_digest, first_request = self._request(prompt="portrait")
        second_digest, second_request = self._request(prompt="wide shot")
        self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_conflict",
            request_digest=first_digest,
            request=first_request,
        )

        with self.assertRaises(GenerationJobConflict):
            self.manager.create_or_reuse(
                project_id=self.project.project_id,
                idempotency_key="idem_conflict",
                request_digest=second_digest,
                request=second_request,
            )

    def test_fresh_key_creates_new_creative_job_for_identical_inputs(self) -> None:
        digest, request = self._request()
        first, _ = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_reroll_a",
            request_digest=digest,
            request=request,
        )
        second, second_reused = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_reroll_b",
            request_digest=digest,
            request=request,
        )

        self.assertFalse(second_reused)
        self.assertNotEqual(first.job_id, second.job_id)
        self.assertEqual(first.request_digest, second.request_digest)
        self.assertEqual(len(self.manager.list(self.project.project_id)), 2)

    def test_failed_job_keeps_attempt_and_explicit_retry_appends_history(self) -> None:
        digest, request = self._request()
        job, _ = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_retry",
            request_digest=digest,
            request=request,
        )
        first_running = self.manager.start_execution(self.project.project_id, job.job_id)
        first_attempt_id = first_running.current_attempt.attempt_id
        failed = self.manager.fail(
            self.project.project_id,
            job.job_id,
            attempt_id=first_attempt_id,
            error="provider timeout",
        )

        replayed, reused = self.manager.create_or_reuse(
            project_id=self.project.project_id,
            idempotency_key="idem_retry",
            request_digest=digest,
            request=request,
        )
        self.assertTrue(reused)
        self.assertEqual(replayed.status, GenerationStatus.FAILED)
        self.assertEqual(len(replayed.attempts), 1)

        retry_running = self.manager.start_execution(self.project.project_id, job.job_id)
        second_attempt_id = retry_running.current_attempt.attempt_id
        completed = self.manager.succeed(
            self.project.project_id,
            job.job_id,
            attempt_id=second_attempt_id,
            output_reference_id="artifact_generation_retry",
            take_id="take_generation_retry",
        )

        self.assertEqual(completed.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(len(completed.attempts), 2)
        self.assertEqual(completed.attempts[0].status, GenerationStatus.FAILED)
        self.assertEqual(completed.attempts[0].retry_index, 0)
        self.assertEqual(completed.attempts[1].status, GenerationStatus.SUCCEEDED)
        self.assertEqual(completed.attempts[1].retry_index, 1)
        self.assertNotEqual(first_attempt_id, second_attempt_id)

        restored = GenerationJobManager(self.store).get(self.project.project_id, job.job_id)
        self.assertEqual(restored, completed)

    def test_request_digest_is_stable_for_mapping_order(self) -> None:
        left_digest, _ = generation_request_digest(
            project_id=self.project.project_id,
            shot_id="shot_1",
            model_id="uv.image.standard",
            capability_id="image.generate",
            offer_id="native_videoclaw.image_generate",
            adapter_id="native_videoclaw",
            inputs={"prompt": "portrait", "options": {"b": 2, "a": 1}},
            contract=self.contract,
        )
        right_digest, _ = generation_request_digest(
            project_id=self.project.project_id,
            shot_id="shot_1",
            model_id="uv.image.standard",
            capability_id="image.generate",
            offer_id="native_videoclaw.image_generate",
            adapter_id="native_videoclaw",
            inputs={"options": {"a": 1, "b": 2}, "prompt": "portrait"},
            contract=self.contract,
        )

        self.assertEqual(left_digest, right_digest)


if __name__ == "__main__":
    unittest.main()
