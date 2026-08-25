from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.authorization import (
    ExecutionConsentRequired,
    OneShotAuthorizationStore,
)
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
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.generation.service import GenerationService
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.timeline import TimelineStore
from uv_studio.projects.transactions import ProjectUnitOfWork


class _FakeImageExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, *, output_path: Path, **kwargs):
        self.calls += 1
        output_path.write_bytes(b"stage14-test-image")
        return {"test_executor": True, "call": self.calls}


class GenerationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Named generation",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_named_generation",
        )
        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_1",
            title="Scene",
        )
        self.production.create_shot(
            self.project.project_id,
            shot_id="shot_1",
            scene_id="scene_1",
            intent="Generate a stable portrait",
        )
        self.authorizations = OneShotAuthorizationStore()
        self.executor = _FakeImageExecutor()
        self.registry = self._model_registry(locality=LocalityClass.LOCAL, cost=CostClass.FREE)
        self.service = GenerationService(
            self.store,
            self.registry,
            self.authorizations,
            self.executor,
        )
        self.contract = GenerationContract(
            fixed_constraints=("same character",),
            editable_variables=("camera",),
            forbidden_changes=("identity",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _model_registry(*, locality: LocalityClass, cost: CostClass) -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Test image generation capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "test_generator",
            "Test generator",
            "Bounded test-only generation transport.",
            AdapterKind.LOCAL if locality is LocalityClass.LOCAL else AdapterKind.RUNTIME,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="test_generator.image_generate",
                capability_id="image.generate",
                adapter_id="test_generator",
                title="Test image generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available inside the bounded test harness.",
                locality=locality,
                cost_class=cost,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.test",
                    title="UV Image Test",
                    description="Test-only named model used to prove the generation contract.",
                    capability_id="image.generate",
                    offer_id="test_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _submit(self, key: str):
        return self.service.submit(
            project_id=self.project.project_id,
            shot_id="shot_1",
            model_id="uv.image.test",
            inputs={"prompt": "portrait", "seed": 7},
            contract=self.contract,
            idempotency_key=key,
            authorization_token=None,
        )

    def test_generation_materializes_project_artifact_and_take_then_acceptance_undo_keeps_job(self) -> None:
        submitted = self._submit("idem_vertical")
        completed = self.service.run(self.project.project_id, submitted.job.job_id)

        self.assertEqual(completed.status.value, "succeeded")
        self.assertEqual(self.executor.calls, 1)
        attempt = completed.current_attempt
        self.assertIsNotNone(attempt)

        project = self.store.load_project(self.project.project_id)
        artifact = next(item for item in project.artifacts if item.id == attempt.output_reference_id)
        self.assertEqual(artifact.kind, "image")
        self.assertTrue(artifact.path.startswith("artifacts/generated_attempt_"))
        self.assertEqual(artifact.metadata["generation"]["job_id"], completed.job_id)
        self.assertEqual(artifact.metadata["generation"]["model_id"], "uv.image.test")
        self.assertEqual(artifact.metadata["generation"]["contract"], self.contract.to_dict())

        shot = self.production.state(self.project.project_id).shot("shot_1")
        self.assertEqual(shot.take_ids, (attempt.take_id,))
        take = self.production.state(self.project.project_id).take(attempt.take_id)
        self.assertEqual(take.reference_id, artifact.id)
        self.assertIsNone(shot.accepted_take_id)

        accepted = self.production.accept_take(
            self.project.project_id,
            take_id=attempt.take_id,
            timeline_start_us=0,
            source_start_us=0,
            duration_us=2_000_000,
            clip_id="clip_generated",
        )
        self.assertEqual(accepted.production.shot("shot_1").accepted_take_id, attempt.take_id)
        self.assertEqual(
            TimelineStore(self.store).load(self.project.project_id).tracks[0].clips[0].reference_id,
            artifact.id,
        )

        ProjectUnitOfWork(self.store).undo(self.project.project_id)
        undone = self.production.state(self.project.project_id).shot("shot_1")
        self.assertIsNone(undone.accepted_take_id)
        self.assertEqual(undone.take_ids, (attempt.take_id,))
        durable_job = self.service.jobs.get(self.project.project_id, completed.job_id)
        self.assertEqual(durable_job.status.value, "succeeded")
        self.assertEqual(durable_job.current_attempt.output_reference_id, artifact.id)

    def test_completed_replay_reuses_result_and_fresh_key_rerolls(self) -> None:
        first = self._submit("idem_replay")
        first_done = self.service.run(self.project.project_id, first.job.job_id)

        replay = self._submit("idem_replay")
        self.assertTrue(replay.reused)
        self.assertEqual(replay.job.job_id, first_done.job_id)
        self.assertEqual(self.executor.calls, 1)

        reroll = self._submit("idem_reroll")
        self.assertFalse(reroll.reused)
        self.assertNotEqual(reroll.job.job_id, first_done.job_id)
        self.service.run(self.project.project_id, reroll.job.job_id)
        self.assertEqual(self.executor.calls, 2)

    def test_remote_or_paid_model_requires_existing_one_shot_authorization(self) -> None:
        registry = self._model_registry(
            locality=LocalityClass.REMOTE,
            cost=CostClass.POTENTIALLY_PAID,
        )
        service = GenerationService(
            self.store,
            registry,
            self.authorizations,
            self.executor,
        )
        kwargs = {
            "project_id": self.project.project_id,
            "shot_id": "shot_1",
            "model_id": "uv.image.test",
            "inputs": {"prompt": "portrait"},
            "contract": self.contract,
        }

        with self.assertRaises(ExecutionConsentRequired):
            service.submit(
                **kwargs,
                idempotency_key="idem_remote",
                authorization_token=None,
            )
        self.assertEqual(service.jobs.list(self.project.project_id), ())

        prepared = service.prepare(**kwargs)
        token, _expires = self.authorizations.issue(
            prepared.execution,
            acknowledgements=set(prepared.execution.consent_required),
        )
        authorized = service.submit(
            **kwargs,
            idempotency_key="idem_remote",
            authorization_token=token,
        )
        self.assertFalse(authorized.reused)

        replay = service.submit(
            **kwargs,
            idempotency_key="idem_remote",
            authorization_token=None,
        )
        self.assertTrue(replay.reused)
        self.assertEqual(replay.job.job_id, authorized.job.job_id)


if __name__ == "__main__":
    unittest.main()
