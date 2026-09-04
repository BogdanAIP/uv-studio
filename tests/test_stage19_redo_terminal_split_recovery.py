from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.jobs import GenerationJobConflict, GenerationStatus
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.generation.recovery import (
    recover_interrupted_project_jobs,
    requeue_failed_generation_job,
)
from uv_studio.generation.service import GenerationService
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import utc_now_iso
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.transactions import ProjectUnitOfWork


class _TerminalSplitExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, *, output_path: Path, **kwargs):
        self.calls += 1
        output_path.write_bytes(b"stage19-redo-terminal-split")
        return {"stage19": "redo-terminal-split", "call": self.calls}


class Stage19RedoTerminalSplitRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 19 redo terminal split",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage19_redo_terminal_split",
        )
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_terminal_split",
            title="Terminal split scene",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_terminal_split",
            scene_id="scene_terminal_split",
            intent="Recover a redo-owned legacy terminal split",
        )
        self.executor = _TerminalSplitExecutor()
        self.service = GenerationService(
            self.store,
            self._model_registry(),
            OneShotAuthorizationStore(),
            self.executor,
        )
        self.contract = GenerationContract(
            fixed_constraints=("same subject",),
            editable_variables=("camera",),
            forbidden_changes=("identity",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _model_registry() -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Stage-19 terminal-split regression capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "stage19_terminal_split_generator",
            "Stage 19 terminal split generator",
            "Bounded test-only generation transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage19_terminal_split_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage19_terminal_split_generator",
                title="Stage 19 terminal split generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available inside the bounded regression harness.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage19-terminal-split",
                    title="UV Image Stage 19 Terminal Split",
                    description="Test-only named model for redo terminal-split recovery.",
                    capability_id="image.generate",
                    offer_id="stage19_terminal_split_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _artifact(self, job):
        attempt = job.current_attempt
        self.assertIsNotNone(attempt)
        project = self.store.load_project(self.project.project_id)
        matches = [
            artifact
            for artifact in project.artifacts
            if isinstance(artifact.metadata.get("generation"), dict)
            and artifact.metadata["generation"].get("job_id") == job.job_id
            and artifact.metadata["generation"].get("attempt_id") == attempt.attempt_id
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_failed_materialization_can_remain_redo_only_without_duplicate_retry(self) -> None:
        submitted = self.service.submit(
            project_id=self.project.project_id,
            shot_id="shot_terminal_split",
            model_id="uv.image.stage19-terminal-split",
            inputs={"prompt": "portrait", "seed": 31},
            contract=self.contract,
            idempotency_key="idem_redo_terminal_split",
            authorization_token=None,
        )
        with mock.patch.object(
            self.service.production,
            "register_take",
            side_effect=RuntimeError("simulated legacy post-artifact failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "post-artifact failure"):
                self.service.run(self.project.project_id, submitted.job.job_id)

        running = self.service.jobs.get(self.project.project_id, submitted.job.job_id)
        self.assertEqual(running.status, GenerationStatus.RUNNING)
        attempt = running.current_attempt
        self.assertIsNotNone(attempt)
        artifact = self._artifact(running)
        output = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        payload = output.read_bytes()

        ended_at = utc_now_iso()
        failed_attempt = replace(
            attempt,
            status=GenerationStatus.FAILED,
            ended_at=ended_at,
            error="legacy post-artifact failure",
        )
        legacy_failed = replace(
            running,
            status=GenerationStatus.FAILED,
            updated_at=ended_at,
            attempts=(*running.attempts[:-1], failed_attempt),
        )
        with self.service.jobs.records.project_lock(self.project.project_id):
            self.service.jobs.records.write(
                self.project.project_id,
                legacy_failed.job_id,
                legacy_failed.to_dict(),
            )

        uow = ProjectUnitOfWork(self.store)
        uow.undo(self.project.project_id)  # generation.register_output
        undone = self.store.load_project(self.project.project_id)
        self.assertFalse(any(item.id == artifact.id for item in undone.artifacts))
        self.assertTrue(uow.history(self.project.project_id).can_redo)
        self.assertEqual(output.read_bytes(), payload)

        self.assertEqual(
            recover_interrupted_project_jobs(self.service.jobs, self.project.project_id),
            (),
        )
        after_restart = self.service.jobs.get(self.project.project_id, legacy_failed.job_id)
        self.assertEqual(after_restart.status, GenerationStatus.FAILED)
        self.assertFalse(
            any(
                item.id == artifact.id
                for item in self.store.load_project(self.project.project_id).artifacts
            )
        )
        self.assertEqual(output.read_bytes(), payload)
        self.assertEqual(self.executor.calls, 1)

        with self.assertRaisesRegex(GenerationJobConflict, "durable artifact pending recovery"):
            self.service.run(self.project.project_id, legacy_failed.job_id)
        after_direct_retry = self.service.jobs.get(
            self.project.project_id,
            legacy_failed.job_id,
        )
        self.assertEqual(after_direct_retry.status, GenerationStatus.FAILED)
        self.assertEqual(len(after_direct_retry.attempts), 1)
        self.assertEqual(self.executor.calls, 1)
        self.assertTrue(uow.history(self.project.project_id).can_redo)

        with self.assertRaisesRegex(GenerationJobConflict, "durable artifact pending recovery"):
            requeue_failed_generation_job(
                self.service.jobs,
                self.project.project_id,
                legacy_failed.job_id,
            )
        self.assertEqual(self.executor.calls, 1)
        self.assertTrue(uow.history(self.project.project_id).can_redo)

        uow.redo(self.project.project_id)  # generation.register_output
        restored = self.store.load_project(self.project.project_id)
        self.assertTrue(any(item.id == artifact.id for item in restored.artifacts))
        self.assertEqual(output.read_bytes(), payload)

        self.assertEqual(
            recover_interrupted_project_jobs(self.service.jobs, self.project.project_id),
            (),
        )
        completed = self.service.jobs.get(self.project.project_id, legacy_failed.job_id)
        self.assertEqual(completed.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(completed.current_attempt.output_reference_id, artifact.id)
        self.assertIsNotNone(completed.current_attempt.take_id)
        state = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertTrue(
            any(take.reference_id == artifact.id for take in state.takes)
        )
        self.assertEqual(self.executor.calls, 1)


if __name__ == "__main__":
    unittest.main()
