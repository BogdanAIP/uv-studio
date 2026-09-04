from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

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
from uv_studio.generation.jobs import GenerationJobError, GenerationJobManager
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.generation.recovery import recover_interrupted_project_jobs
from uv_studio.generation.service import GenerationService
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.archive import ProjectArchiveError, export_project, import_project
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore
from uv_studio.projects.transactions import ProjectTransactionError, ProjectUnitOfWork


class _DigestImageExecutor:
    def execute(self, *, output_path: Path, **kwargs):
        output_path.write_bytes(b"stage19-redo-generation-digest-authority")
        return {"stage19": "redo-generation-digest"}


class Stage19RedoGenerationDigestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 19 redo Generation digest authority",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage19_redo_generation_digest",
        )
        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_redo_generation_digest",
            title="Redo Generation digest scene",
        )
        self.production.create_shot(
            self.project.project_id,
            shot_id="shot_redo_generation_digest",
            scene_id="scene_redo_generation_digest",
            intent="Preserve only exact Generation bytes through Redo",
        )
        self.service = GenerationService(
            self.store,
            self._model_registry(),
            OneShotAuthorizationStore(),
            _DigestImageExecutor(),
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
            "Stage-19 redo digest authority capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "stage19_redo_digest_generator",
            "Stage 19 redo digest generator",
            "Bounded test-only generation transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage19_redo_digest_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage19_redo_digest_generator",
                title="Stage 19 redo digest image generator",
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
                    model_id="uv.image.stage19-redo-digest",
                    title="UV Image Stage 19 Redo Digest",
                    description="Test-only named model for redo Generation digest authority.",
                    capability_id="image.generate",
                    offer_id="stage19_redo_digest_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _generate(self):
        submitted = self.service.submit(
            project_id=self.project.project_id,
            shot_id="shot_redo_generation_digest",
            model_id="uv.image.stage19-redo-digest",
            inputs={"prompt": "portrait", "seed": 29},
            contract=self.contract,
            idempotency_key="idem_redo_generation_digest",
            authorization_token=None,
        )
        completed = self.service.run(self.project.project_id, submitted.job.job_id)
        attempt = completed.current_attempt
        self.assertIsNotNone(attempt)
        self.assertIsNotNone(attempt.take_id)

        project = self.store.load_project(self.project.project_id)
        artifacts = [
            artifact
            for artifact in project.artifacts
            if isinstance(artifact.metadata.get("generation"), dict)
            and artifact.metadata["generation"].get("job_id") == completed.job_id
            and artifact.metadata["generation"].get("attempt_id") == attempt.attempt_id
        ]
        self.assertEqual(len(artifacts), 1)
        artifact = artifacts[0]
        output = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        payload = output.read_bytes()
        self.assertGreater(len(payload), 1)
        return completed, attempt, artifact, output, payload, ProjectUnitOfWork(self.store)

    def _generate_and_undo(self):
        completed, attempt, artifact, output, payload, uow = self._generate()
        uow.undo(self.project.project_id)  # production.register_take
        uow.undo(self.project.project_id)  # generation.register_output

        undone = self.store.load_project(self.project.project_id)
        self.assertFalse(any(item.id == artifact.id for item in undone.artifacts))
        state = self.production.state(self.project.project_id)
        self.assertFalse(any(take.take_id == attempt.take_id for take in state.takes))
        self.assertTrue(uow.history(self.project.project_id).can_redo)
        self.assertEqual(output.read_bytes(), payload)
        return completed, attempt, artifact, output, payload, uow

    @staticmethod
    def _corrupt_same_size(output: Path, payload: bytes) -> bytes:
        corrupt = bytes([payload[0] ^ 1]) + payload[1:]
        output.write_bytes(corrupt)
        return corrupt

    def test_archive_requires_canonical_generation_job_record_validation(self) -> None:
        completed, _attempt, _artifact, _output, _payload, _uow = self._generate()
        job_path = (
            self.store.project_directory(self.project.project_id)
            / "tasks"
            / f"{completed.job_id}.json"
        )
        raw = json.loads(job_path.read_text(encoding="utf-8"))
        raw["schema_version"] = 999
        self.store._atomic_write_json(job_path, raw)

        with self.assertRaisesRegex(GenerationJobError, "schema v1|invalid generation job record"):
            GenerationJobManager(self.store).get(self.project.project_id, completed.job_id)

        archive_path = Path(self.tmp.name) / "unsupported-generation-job-schema.uvproj.zip"
        with self.assertRaisesRegex(ProjectArchiveError, "Generation|schema|authority"):
            export_project(self.store, self.project.project_id, archive_path)
        self.assertFalse(archive_path.exists())

    def test_archive_rejects_corrupt_redo_only_generation_bytes(self) -> None:
        _job, _attempt, _artifact, output, payload, _uow = self._generate_and_undo()
        self._corrupt_same_size(output, payload)

        archive_path = Path(self.tmp.name) / "corrupt-redo-generation.uvproj.zip"
        with self.assertRaisesRegex(ProjectArchiveError, "Generation.*digest|size/digest"):
            export_project(self.store, self.project.project_id, archive_path)
        self.assertFalse(archive_path.exists())

    def test_restart_rejects_corrupt_redo_only_generation_bytes(self) -> None:
        _job, _attempt, artifact, output, payload, _uow = self._generate_and_undo()
        corrupt = self._corrupt_same_size(output, payload)

        with self.assertRaisesRegex(GenerationJobError, "Generation.*digest|digest does not match"):
            recover_interrupted_project_jobs(
                GenerationJobManager(self.store),
                self.project.project_id,
            )
        self.assertTrue(output.is_file())
        self.assertEqual(output.read_bytes(), corrupt)
        project = self.store.load_project(self.project.project_id)
        self.assertFalse(any(item.id == artifact.id for item in project.artifacts))

    def test_direct_redo_rejects_corrupt_generation_bytes(self) -> None:
        _job, _attempt, artifact, output, payload, uow = self._generate_and_undo()
        corrupt = self._corrupt_same_size(output, payload)

        with self.assertRaisesRegex(ProjectTransactionError, "Generation.*digest|digest does not match"):
            uow.redo(self.project.project_id)
        self.assertTrue(uow.history(self.project.project_id).can_redo)
        project = self.store.load_project(self.project.project_id)
        self.assertFalse(any(item.id == artifact.id for item in project.artifacts))
        self.assertEqual(output.read_bytes(), corrupt)

    def test_second_redo_rejects_bytes_corrupted_after_artifact_redo(self) -> None:
        _job, attempt, artifact, output, payload, uow = self._generate_and_undo()

        uow.redo(self.project.project_id)  # generation.register_output
        live = self.store.load_project(self.project.project_id)
        self.assertTrue(any(item.id == artifact.id for item in live.artifacts))
        state = self.production.state(self.project.project_id)
        self.assertFalse(any(take.take_id == attempt.take_id for take in state.takes))

        corrupt = self._corrupt_same_size(output, payload)
        with self.assertRaisesRegex(ProjectTransactionError, "Generation.*digest|digest does not match"):
            uow.redo(self.project.project_id)  # production.register_take

        self.assertTrue(uow.history(self.project.project_id).can_redo)
        state = self.production.state(self.project.project_id)
        self.assertFalse(any(take.take_id == attempt.take_id for take in state.takes))
        self.assertEqual(output.read_bytes(), corrupt)

    def test_accept_take_reference_metadata_evolution_remains_redo_reachable(self) -> None:
        _job, attempt, artifact, output, payload, uow = self._generate()
        self.production.accept_take(
            self.project.project_id,
            take_id=attempt.take_id,
            timeline_start_us=0,
            duration_us=1_000_000,
            clip_id="clip_stage19_redo_metadata_evolution",
        )
        accepted = self.store.load_project(self.project.project_id)
        accepted_artifact = next(item for item in accepted.artifacts if item.id == artifact.id)
        self.assertNotEqual(accepted_artifact.metadata, artifact.metadata)
        self.assertTrue(accepted_artifact.metadata.get("production_acceptances"))

        uow.undo(self.project.project_id)  # production.accept_take
        uow.undo(self.project.project_id)  # production.register_take
        uow.undo(self.project.project_id)  # generation.register_output
        undone = self.store.load_project(self.project.project_id)
        self.assertFalse(any(item.id == artifact.id for item in undone.artifacts))
        self.assertEqual(output.read_bytes(), payload)

        self.assertEqual(
            recover_interrupted_project_jobs(
                GenerationJobManager(self.store),
                self.project.project_id,
            ),
            (),
        )
        self.assertEqual(output.read_bytes(), payload)

        archive_path = Path(self.tmp.name) / "redo-metadata-evolution.uvproj.zip"
        export_project(self.store, self.project.project_id, archive_path)
        imported_store = ProjectStore(Path(self.tmp.name) / "metadata-evolution-import")
        imported = import_project(imported_store, archive_path)
        imported_output = imported_store.resolve_project_file(
            imported.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(imported_output.read_bytes(), payload)

        imported_uow = ProjectUnitOfWork(imported_store)
        imported_uow.redo(imported.project_id)
        imported_uow.redo(imported.project_id)
        imported_uow.redo(imported.project_id)

        restored = imported_store.load_project(imported.project_id)
        restored_artifact = next(item for item in restored.artifacts if item.id == artifact.id)
        self.assertEqual(restored_artifact.metadata, accepted_artifact.metadata)
        restored_state = ProductionSemanticService(imported_store).state(imported.project_id)
        restored_shot = restored_state.shot("shot_redo_generation_digest")
        self.assertEqual(restored_shot.accepted_take_id, attempt.take_id)
        self.assertEqual(imported_output.read_bytes(), payload)

    def test_redo_media_authority_rejects_unreachable_snapshot_chain(self) -> None:
        _job, _attempt, _artifact, _output, _payload, uow = self._generate_and_undo()
        history = uow.history(self.project.project_id)
        entry = history.entries[history.cursor]
        self.assertEqual(entry.command, "generation.register_output")
        record_path = uow._record_path(
            self.project.project_id,
            entry.transaction_id,
            transaction=True,
        )
        record = uow._load_record(record_path)
        changes = record.get("changes")
        self.assertIsInstance(changes, list)
        mutated_changes = []
        changed_project = False
        for raw_change in changes:
            change = dict(raw_change)
            if change.get("path") == PROJECT_FILENAME:
                change["before"] = dict(change["after"])
                changed_project = True
            mutated_changes.append(change)
        self.assertTrue(changed_project)
        record["changes"] = mutated_changes
        self.store._atomic_write_json(record_path, record)

        archive_path = Path(self.tmp.name) / "unreachable-redo-authority.uvproj.zip"
        with self.assertRaisesRegex(ProjectArchiveError, "redo history is invalid|changed outside"):
            export_project(self.store, self.project.project_id, archive_path)
        self.assertFalse(archive_path.exists())

        with self.assertRaisesRegex(GenerationJobError, "invalid UOW redo history"):
            recover_interrupted_project_jobs(
                GenerationJobManager(self.store),
                self.project.project_id,
            )

    def test_generation_reference_rejects_outside_artifacts_root_before_archive(self) -> None:
        _job, _attempt, artifact, _output, _payload, _uow = self._generate()
        moved_relative = f"sources/{Path(artifact.path).name}"

        with self.assertRaisesRegex(
            ValueError,
            "Generation artifact path|canonical artifacts",
        ):
            replace(artifact, path=moved_relative)

        archive_path = Path(self.tmp.name) / "generation-wrong-root.uvproj.zip"
        self.assertFalse(archive_path.exists())

    def test_exact_generation_bytes_survive_archive_import_and_two_redos(self) -> None:
        _job, attempt, artifact, _output, payload, _uow = self._generate_and_undo()

        archive_path = Path(self.tmp.name) / "redo-generation-exact.uvproj.zip"
        export_project(self.store, self.project.project_id, archive_path)

        imported_store = ProjectStore(Path(self.tmp.name) / "imported-projects")
        imported = import_project(imported_store, archive_path)
        imported_output = imported_store.resolve_project_file(
            imported.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(imported_output.read_bytes(), payload)
        self.assertFalse(any(item.id == artifact.id for item in imported.artifacts))

        imported_uow = ProjectUnitOfWork(imported_store)
        imported_uow.redo(imported.project_id)
        imported_uow.redo(imported.project_id)

        restored = imported_store.load_project(imported.project_id)
        restored_artifacts = [item for item in restored.artifacts if item.id == artifact.id]
        self.assertEqual(len(restored_artifacts), 1)
        self.assertEqual(restored_artifacts[0].path, artifact.path)
        self.assertEqual(restored_artifacts[0].metadata, artifact.metadata)
        restored_state = ProductionSemanticService(imported_store).state(imported.project_id)
        restored_takes = [take for take in restored_state.takes if take.take_id == attempt.take_id]
        self.assertEqual(len(restored_takes), 1)
        self.assertEqual(restored_takes[0].reference_id, artifact.id)
        self.assertEqual(imported_output.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
