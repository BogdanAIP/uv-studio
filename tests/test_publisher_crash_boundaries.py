from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.generation.jobs import GenerationJobManager, GenerationStatus, generation_request_digest
from uv_studio.generation.models import GenerationContract
from uv_studio.generation.recovery import recover_interrupted_project_jobs
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.archive import ProjectArchiveError, export_project
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.publication import pending_managed_publications, recover_managed_publications
from uv_studio.projects.store import ProjectStore


class PublisherCrashBoundaryTests(unittest.TestCase):
    @staticmethod
    def _timeline_offer() -> CapabilityOffer:
        return CapabilityOffer(
            "local_ffmpeg.timeline_assemble",
            "timeline.assemble",
            "local_ffmpeg",
            "Timeline assemble",
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def test_timeline_assemble_process_loss_leaves_marker_and_recovery_quarantines_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                recipe_id="general_video",
                title="Timeline crash boundary",
                project_id="prj_timeline_crash_boundary",
            )
            project_dir = store.project_directory(project.project_id)
            (project_dir / "sources" / "a.mp4").write_bytes(b"a")
            (project_dir / "sources" / "b.mp4").write_bytes(b"b")

            def runner(command, **kwargs):
                self.assertIs(kwargs["shell"], False)
                Path(command[-1]).write_bytes(b"joined-before-process-loss")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            adapter = LocalFFmpegAdapter(
                store,
                runner=runner,
                tool_paths={"ffmpeg": "fake-ffmpeg"},
            )
            output = project_dir / "artifacts" / "caller-selected-name.mp4"

            with mock.patch.object(
                store,
                "update_project",
                side_effect=SystemExit("simulated process loss after canonical move"),
            ):
                with self.assertRaises(SystemExit):
                    adapter.execute(
                        project_id=project.project_id,
                        offer=self._timeline_offer(),
                        payload={
                            "input_paths": ["sources/a.mp4", "sources/b.mp4"],
                            "output_path": "artifacts/caller-selected-name.mp4",
                        },
                    )

            self.assertEqual(output.read_bytes(), b"joined-before-process-loss")
            self.assertEqual(store.load_project(project.project_id).artifacts, ())
            pending = pending_managed_publications(store, project.project_id)
            self.assertEqual(len(pending), 1)
            self.assertEqual(
                pending[0]["relative_path"],
                "artifacts/caller-selected-name.mp4",
            )

            with self.assertRaisesRegex(ProjectArchiveError, "interrupted managed publication"):
                export_project(store, project.project_id, base / "before-recovery.uvproj.zip")

            quarantined = recover_managed_publications(store, project.project_id)
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0].read_bytes(), b"joined-before-process-loss")
            self.assertFalse(output.exists())
            self.assertEqual(pending_managed_publications(store, project.project_id), ())

    def test_startup_recovery_quarantines_webvtt_bytes_without_project_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                recipe_id="general_video",
                title="WebVTT crash boundary",
                project_id="prj_webvtt_crash_boundary",
            )
            project_dir = store.project_directory(project.project_id)
            output = project_dir / "artifacts" / "sub_0123456789abcdef0123456789abcdef.vtt"
            output.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nCrash boundary\n", encoding="utf-8")

            manager = GenerationJobManager(store)
            self.assertEqual(recover_interrupted_project_jobs(manager, project.project_id), ())
            self.assertFalse(output.exists())
            quarantined = tuple(
                store.root.glob(
                    f".uv-recovered-orphan-{project.project_id}-*-{output.name}"
                )
            )
            self.assertEqual(len(quarantined), 1)
            self.assertIn("WEBVTT", quarantined[0].read_text(encoding="utf-8"))

            archive = export_project(
                store,
                project.project_id,
                base / "webvtt-after-recovery.uvproj.zip",
            )
            self.assertTrue(archive.is_file())

    def test_archive_rejects_generation_artifact_take_until_running_job_is_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                title="Generation crash boundary",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_generation_crash_boundary",
            )
            production = ProductionSemanticService(store)
            production.create_scene(project.project_id, scene_id="scene_1", title="Scene")
            production.create_shot(
                project.project_id,
                shot_id="shot_1",
                scene_id="scene_1",
                intent="Crash boundary",
            )

            contract = GenerationContract(
                fixed_constraints=("same character",),
                editable_variables=("camera",),
                forbidden_changes=("identity",),
            )
            digest, request = generation_request_digest(
                project_id=project.project_id,
                shot_id="shot_1",
                model_id="uv.image.standard",
                capability_id="image.generate",
                offer_id="native_videoclaw.image_generate",
                adapter_id="native_videoclaw",
                inputs={"prompt": "portrait"},
                contract=contract,
            )
            manager = GenerationJobManager(store)
            job, reused = manager.create_or_reuse(
                project_id=project.project_id,
                idempotency_key="idem_generation_crash_boundary",
                request_digest=digest,
                request=request,
            )
            self.assertFalse(reused)
            running = manager.start_execution(project.project_id, job.job_id)
            attempt = running.current_attempt
            self.assertIsNotNone(attempt)

            relative_path = f"artifacts/generated_{attempt.attempt_id}.png"
            output = store.resolve_project_file(
                project.project_id,
                relative_path,
                allowed_roots=("artifacts",),
            )
            output.write_bytes(b"generation-crash-boundary")
            artifact = ProjectReference(
                id="artifact_generation_crash_boundary",
                kind="image",
                path=relative_path,
                metadata={
                    "generation": {
                        "job_id": job.job_id,
                        "attempt_id": attempt.attempt_id,
                        "model_id": "uv.image.standard",
                    }
                },
            )
            current = store.load_project(project.project_id)
            store.update_project(
                project.project_id,
                artifacts=(*current.artifacts, artifact),
            )
            production.register_take(
                project.project_id,
                take_id="take_generation_crash_boundary",
                shot_id="shot_1",
                reference_id=artifact.id,
                label="Crash-boundary Take",
            )

            self.assertEqual(manager.get(project.project_id, job.job_id).status, GenerationStatus.RUNNING)
            with self.assertRaisesRegex(ProjectArchiveError, "not durably complete"):
                export_project(store, project.project_id, base / "generation-before-recovery.uvproj.zip")

            self.assertEqual(recover_interrupted_project_jobs(manager, project.project_id), ())
            durable = manager.get(project.project_id, job.job_id)
            self.assertEqual(durable.status, GenerationStatus.SUCCEEDED)
            self.assertEqual(durable.current_attempt.output_reference_id, artifact.id)
            self.assertEqual(durable.current_attempt.take_id, "take_generation_crash_boundary")

            archive = export_project(
                store,
                project.project_id,
                base / "generation-after-recovery.uvproj.zip",
            )
            self.assertTrue(archive.is_file())


if __name__ == "__main__":
    unittest.main()
