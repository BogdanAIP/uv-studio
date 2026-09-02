from __future__ import annotations

import tempfile
import threading
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
from uv_studio.generation.jobs import (
    GenerationExecutionAttempt,
    GenerationJobConflict,
    GenerationJobError,
    GenerationJobManager,
    GenerationStatus,
)
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.generation.recovery import (
    recover_interrupted_project_jobs,
    requeue_failed_generation_job,
)
from uv_studio.generation.service import GenerationService
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.production.semantics import (
    PRODUCTION_SEMANTICS_PATH,
    ProductionSemanticsDocument,
)
from uv_studio.projects.archive import ProjectArchiveError, export_project
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.models import utc_now_iso
from uv_studio.projects.transactions import ProjectUnitOfWork


class _ImageExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, *, output_path: Path, **kwargs):
        self.calls += 1
        output_path.write_bytes(b"stage19-fresh-review-image")
        return {"test_executor": True, "call": self.calls}


class Stage19FreshReviewRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 19 fresh review repairs",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage19_fresh_review",
        )
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_stage19",
            title="Scene",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_stage19",
            scene_id="scene_stage19",
            intent="Generate a recovery candidate",
        )
        self.executor = _ImageExecutor()
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
            "Stage-19 repair test generation capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "stage19_test_generator",
            "Stage 19 test generator",
            "Bounded test-only generation transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage19_test_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage19_test_generator",
                title="Stage 19 test image generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available inside the bounded test harness.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage19-test",
                    title="UV Image Stage 19 Test",
                    description="Test-only named model for fresh-review recovery repairs.",
                    capability_id="image.generate",
                    offer_id="stage19_test_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _submit(self, key: str):
        return self.service.submit(
            project_id=self.project.project_id,
            shot_id="shot_stage19",
            model_id="uv.image.stage19-test",
            inputs={"prompt": "portrait", "seed": 19},
            contract=self.contract,
            idempotency_key=key,
            authorization_token=None,
        )

    def _artifact_for_current_attempt(self, job):
        attempt = job.current_attempt
        self.assertIsNotNone(attempt)
        project = self.store.load_project(self.project.project_id)
        matches = []
        for artifact in project.artifacts:
            generation = artifact.metadata.get("generation")
            if not isinstance(generation, dict):
                continue
            if (
                generation.get("job_id") == job.job_id
                and generation.get("attempt_id") == attempt.attempt_id
            ):
                matches.append(artifact)
        self.assertEqual(len(matches), 1)
        return matches[0]

    def _run_until_take_failure(self, key: str):
        submitted = self._submit(key)
        with mock.patch.object(
            self.service.production,
            "register_take",
            side_effect=RuntimeError("simulated local Take persistence failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Take persistence failure"):
                self.service.run(self.project.project_id, submitted.job.job_id)
        durable = self.service.jobs.get(self.project.project_id, submitted.job.job_id)
        self.assertEqual(durable.status, GenerationStatus.RUNNING)
        artifact = self._artifact_for_current_attempt(durable)
        return durable, artifact

    def test_local_take_failure_preserves_running_job_and_restart_completes(self) -> None:
        running, artifact = self._run_until_take_failure("idem_take_failure")
        archive_path = Path(self.tmp.name) / "before-recovery.uvproj.zip"
        with self.assertRaises(ProjectArchiveError):
            export_project(self.store, self.project.project_id, archive_path)

        self.assertEqual(
            recover_interrupted_project_jobs(self.service.jobs, self.project.project_id),
            (),
        )
        completed = self.service.jobs.get(self.project.project_id, running.job_id)
        self.assertEqual(completed.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(completed.current_attempt.output_reference_id, artifact.id)
        self.assertIsNotNone(completed.current_attempt.take_id)
        self.assertEqual(self.executor.calls, 1)

        export_project(self.store, self.project.project_id, archive_path)
        self.assertTrue(archive_path.is_file())

    def test_legacy_terminal_split_is_reconciled_and_retry_is_blocked_first(self) -> None:
        running, artifact = self._run_until_take_failure("idem_legacy_terminal")
        attempt = running.current_attempt
        self.assertIsNotNone(attempt)
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

        with self.assertRaisesRegex(GenerationJobConflict, "durable artifact pending recovery"):
            requeue_failed_generation_job(
                self.service.jobs,
                self.project.project_id,
                legacy_failed.job_id,
            )

        recover_interrupted_project_jobs(self.service.jobs, self.project.project_id)
        completed = self.service.jobs.get(self.project.project_id, legacy_failed.job_id)
        self.assertEqual(completed.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(completed.current_attempt.output_reference_id, artifact.id)
        self.assertEqual(self.executor.calls, 1)

    def test_historical_older_attempt_artifact_is_reconciled_by_its_own_identity(self) -> None:
        running, artifact = self._run_until_take_failure("idem_historical_retry")
        attempt0 = running.current_attempt
        self.assertIsNotNone(attempt0)
        ended_at = utc_now_iso()
        failed0 = replace(
            attempt0,
            status=GenerationStatus.FAILED,
            ended_at=ended_at,
            error="legacy attempt zero failed after artifact commit",
        )
        failed1 = GenerationExecutionAttempt(
            attempt_id="attempt_legacy_retry_one",
            retry_index=1,
            status=GenerationStatus.FAILED,
            started_at=ended_at,
            ended_at=ended_at,
            error="legacy retry failed without materialization",
        )
        legacy = replace(
            running,
            status=GenerationStatus.FAILED,
            updated_at=ended_at,
            attempts=(failed0, failed1),
        )
        with self.service.jobs.records.project_lock(self.project.project_id):
            self.service.jobs.records.write(
                self.project.project_id,
                legacy.job_id,
                legacy.to_dict(),
            )

        with self.assertRaisesRegex(GenerationJobConflict, "durable artifact pending recovery"):
            self.service.jobs.start_execution(self.project.project_id, legacy.job_id)

        self.assertEqual(
            recover_interrupted_project_jobs(self.service.jobs, self.project.project_id),
            (),
        )
        repaired = self.service.jobs.get(self.project.project_id, legacy.job_id)
        self.assertEqual(repaired.status, GenerationStatus.FAILED)
        self.assertEqual(repaired.attempts[0].status, GenerationStatus.SUCCEEDED)
        self.assertEqual(repaired.attempts[0].output_reference_id, artifact.id)
        self.assertIsNotNone(repaired.attempts[0].take_id)
        self.assertEqual(repaired.attempts[1].status, GenerationStatus.FAILED)
        state = ProductionSemanticService(self.store).state(self.project.project_id)
        recovered_takes = [take for take in state.takes if take.reference_id == artifact.id]
        self.assertEqual(len(recovered_takes), 1)
        self.assertEqual(recovered_takes[0].take_id, repaired.attempts[0].take_id)
        self.assertEqual(self.executor.calls, 1)

        archive_path = Path(self.tmp.name) / "historical-attempt.uvproj.zip"
        export_project(self.store, self.project.project_id, archive_path)
        self.assertTrue(archive_path.is_file())

    def test_cross_runtime_cancel_waits_for_publication_fence(self) -> None:
        submitted = self._submit("idem_cross_runtime_cancel")
        artifact_committed = threading.Event()
        release_publication = threading.Event()
        run_done = threading.Event()
        cancel_done = threading.Event()
        run_errors: list[BaseException] = []
        cancel_errors: list[BaseException] = []
        original_register = self.service._register_artifact

        def blocked_register(**kwargs):
            reference = original_register(**kwargs)
            artifact_committed.set()
            if not release_publication.wait(timeout=5):
                raise RuntimeError("test did not release generation publication")
            return reference

        def run_generation() -> None:
            try:
                self.service.run(self.project.project_id, submitted.job.job_id)
            except BaseException as exc:  # pragma: no cover - surfaced below
                run_errors.append(exc)
            finally:
                run_done.set()

        other_store = ProjectStore(self.store.root)
        other_manager = GenerationJobManager(other_store)

        def cancel_generation() -> None:
            try:
                other_manager.cancel(self.project.project_id, submitted.job.job_id)
            except BaseException as exc:  # expected after publication succeeds
                cancel_errors.append(exc)
            finally:
                cancel_done.set()

        run_thread = threading.Thread(target=run_generation, daemon=True)
        cancel_thread = threading.Thread(target=cancel_generation, daemon=True)
        with mock.patch.object(self.service, "_register_artifact", side_effect=blocked_register):
            run_thread.start()
            try:
                self.assertTrue(artifact_committed.wait(timeout=5))
                cancel_thread.start()
                self.assertFalse(
                    cancel_done.wait(timeout=0.2),
                    "cross-runtime cancellation must wait behind publication fence",
                )
            finally:
                release_publication.set()
                run_thread.join(timeout=5)
                cancel_thread.join(timeout=5)

        self.assertTrue(run_done.is_set())
        self.assertTrue(cancel_done.is_set())
        self.assertEqual(run_errors, [])
        self.assertEqual(len(cancel_errors), 1)
        self.assertIsInstance(cancel_errors[0], GenerationJobConflict)
        durable = self.service.jobs.get(self.project.project_id, submitted.job.job_id)
        self.assertEqual(durable.status, GenerationStatus.SUCCEEDED)

    def test_recovery_rejects_changed_generation_bytes(self) -> None:
        running, artifact = self._run_until_take_failure("idem_changed_bytes")
        output = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        original = output.read_bytes()
        self.assertGreater(len(original), 1)
        output.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        self.assertEqual(output.stat().st_size, len(original))

        with self.assertRaisesRegex(GenerationJobError, "digest does not match"):
            recover_interrupted_project_jobs(self.service.jobs, self.project.project_id)
        durable = self.service.jobs.get(self.project.project_id, running.job_id)
        self.assertEqual(durable.status, GenerationStatus.RUNNING)
        state = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertFalse(any(take.reference_id == artifact.id for take in state.takes))

    def test_recovery_rejects_generation_provenance_mismatch(self) -> None:
        running, artifact = self._run_until_take_failure("idem_bad_provenance")
        project = self.store.load_project(self.project.project_id)
        metadata = dict(artifact.metadata)
        generation = dict(metadata["generation"])
        generation["request_digest"] = "0" * 64
        metadata["generation"] = generation
        bad_artifact = replace(artifact, metadata=metadata)
        corrupted = project.to_dict()
        corrupted["artifacts"] = [
            bad_artifact.to_dict() if item["id"] == artifact.id else item
            for item in corrupted["artifacts"]
        ]
        self.store._atomic_write_json(
            self.store.project_path(self.project.project_id),
            corrupted,
        )

        with self.assertRaisesRegex(GenerationJobError, "request_digest"):
            recover_interrupted_project_jobs(self.service.jobs, self.project.project_id)
        durable = self.service.jobs.get(self.project.project_id, running.job_id)
        self.assertEqual(durable.status, GenerationStatus.RUNNING)

    def test_archive_hashes_exact_generation_bytes_against_persisted_digest(self) -> None:
        submitted = self._submit("idem_archive_digest")
        completed = self.service.run(self.project.project_id, submitted.job.job_id)
        artifact = self._artifact_for_current_attempt(completed)
        output = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        original = output.read_bytes()
        output.write_bytes(bytes([original[0] ^ 1]) + original[1:])

        archive_path = Path(self.tmp.name) / "corrupt-generation.uvproj.zip"
        with self.assertRaisesRegex(ProjectArchiveError, "persisted size/digest"):
            export_project(self.store, self.project.project_id, archive_path)
        self.assertFalse(archive_path.exists())

    def test_archive_accepts_generation_take_removed_by_explicit_undo(self) -> None:
        submitted = self._submit("idem_take_undo")
        completed = self.service.run(self.project.project_id, submitted.job.job_id)
        attempt = completed.current_attempt
        self.assertIsNotNone(attempt)
        artifact = self._artifact_for_current_attempt(completed)
        take_id = attempt.take_id
        self.assertIsNotNone(take_id)

        ProjectUnitOfWork(self.store).undo(self.project.project_id)
        state = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertFalse(any(take.take_id == take_id for take in state.takes))
        durable = self.service.jobs.get(self.project.project_id, completed.job_id)
        self.assertEqual(durable.status, GenerationStatus.SUCCEEDED)
        self.assertEqual(durable.current_attempt.take_id, take_id)

        # A new command truncates the stale redo branch. The durable undo operation
        # must still prove why immutable Job provenance names a Take absent from the
        # current Production state.
        ProductionSemanticService(self.store).create_scene(
            self.project.project_id,
            scene_id="scene_after_generation_undo",
            title="After Undo",
        )

        archive_path = Path(self.tmp.name) / "generation-take-undone.uvproj.zip"
        export_project(self.store, self.project.project_id, archive_path)
        self.assertTrue(archive_path.is_file())
        self.assertTrue(
            any(
                item.id == artifact.id
                for item in self.store.load_project(self.project.project_id).artifacts
            )
        )

    def test_archive_rejects_generation_take_missing_without_undo_authority(self) -> None:
        submitted = self._submit("idem_take_out_of_band")
        completed = self.service.run(self.project.project_id, submitted.job.job_id)
        attempt = completed.current_attempt
        self.assertIsNotNone(attempt)
        take_id = attempt.take_id
        self.assertIsNotNone(take_id)

        state = ProductionSemanticService(self.store).state(self.project.project_id)
        updated_shots = tuple(
            replace(
                shot,
                take_ids=tuple(item for item in shot.take_ids if item != take_id),
                accepted_take_id=(None if shot.accepted_take_id == take_id else shot.accepted_take_id),
            )
            for shot in state.shots
        )
        corrupted = ProductionSemanticsDocument(
            scenes=state.scenes,
            shots=updated_shots,
            takes=tuple(take for take in state.takes if take.take_id != take_id),
        )
        semantics_path = self.store.resolve_project_file(
            self.project.project_id,
            PRODUCTION_SEMANTICS_PATH,
            allowed_roots=("production",),
        )
        self.store._atomic_write_json(semantics_path, corrupted.to_dict())

        archive_path = Path(self.tmp.name) / "generation-take-missing.uvproj.zip"
        with self.assertRaisesRegex(ProjectArchiveError, "missing without durable Undo authority"):
            export_project(self.store, self.project.project_id, archive_path)
        self.assertFalse(archive_path.exists())

    def test_source_orphan_blocks_archive_then_restart_quarantines_it(self) -> None:
        media_store = ProjectSourceMediaStore(self.store)
        allocation = media_store.allocate(self.project.project_id, "crash-source.mp4")
        allocation.absolute_path.write_bytes(b"source-bytes-after-final-move")
        self.assertFalse(
            any(
                item.id == allocation.source_id
                for item in self.store.load_project(self.project.project_id).sources
            )
        )

        archive_path = Path(self.tmp.name) / "source-before-recovery.uvproj.zip"
        with self.assertRaisesRegex(ProjectArchiveError, "unpublished managed media"):
            export_project(self.store, self.project.project_id, archive_path)

        manager = GenerationJobManager(self.store)
        self.assertEqual(
            recover_interrupted_project_jobs(manager, self.project.project_id),
            (),
        )
        self.assertFalse(allocation.absolute_path.exists())
        quarantined = tuple(
            self.store.root.glob(
                f".uv-recovered-orphan-{self.project.project_id}-*-{allocation.absolute_path.name}"
            )
        )
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_bytes(), b"source-bytes-after-final-move")

        export_project(self.store, self.project.project_id, archive_path)
        self.assertTrue(archive_path.is_file())


if __name__ == "__main__":
    unittest.main()
