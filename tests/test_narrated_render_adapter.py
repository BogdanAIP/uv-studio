from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities import CapabilityOffer, CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import InvalidCapabilityInput
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import save_stage8_workspace
from uv_studio.projects.store import ProjectStore


def _offer() -> CapabilityOffer:
    return CapabilityOffer(
        offer_id="local_ffmpeg.video_render_narrated",
        capability_id="video.render_narrated",
        adapter_id="local_ffmpeg",
        title="Narrated render",
        availability=OfferAvailability.AVAILABLE,
        reason="test runtime",
        locality=LocalityClass.LOCAL,
        cost_class=CostClass.FREE,
        asynchronous=False,
    )


class NarratedRenderAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Narrated adapter", recipe_id="narrated_video")
        self.image_body = b"image-fixture"
        media = ProjectSourceMediaStore(self.store)
        image_allocation = media.allocate(self.project.project_id, "frame.png")
        image_allocation.absolute_path.write_bytes(self.image_body)
        self.image = media.register(
            self.project.project_id,
            image_allocation,
            media_kind="image",
            metadata={
                "sha256": hashlib.sha256(self.image_body).hexdigest(),
                "size_bytes": len(self.image_body),
            },
        )
        self.workspace = save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Объяснить устройство",
            script="Это проверенный текст диктора.",
            source_ids=[self.image.id],
        )

        self.audio_body = b"prepared-audio-fixture"
        audio_store = ProjectPreparedAudioStore(self.store)
        audio_allocation = audio_store.allocate(self.project.project_id, "narration.wav")
        audio_allocation.absolute_path.write_bytes(self.audio_body)
        updated = audio_store.register(
            self.project.project_id,
            audio_allocation,
            metadata={
                "original_name": "narration.wav",
                "origin": "imported",
                "duration_us": 3_000_000,
                "sha256": hashlib.sha256(self.audio_body).hexdigest(),
                "size_bytes": len(self.audio_body),
                "has_audio": True,
                "has_video": False,
            },
        )
        self.audio = next(item for item in updated.artifacts if item.id == audio_allocation.audio_id)
        self.adapter = LocalFFmpegAdapter(
            self.store,
            tool_paths={"ffmpeg": "/tools/ffmpeg", "ffprobe": "/tools/ffprobe"},
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_render_uses_only_bound_project_media_and_registers_fingerprints(self) -> None:
        commands: list[list[str]] = []

        def fake_invoke(command, **_kwargs):
            commands.append(list(command))
            Path(command[-1]).write_bytes(b"rendered-master")
            return None

        with (
            mock.patch.object(self.adapter._delegate, "_invoke", side_effect=fake_invoke),
            mock.patch.object(
                self.adapter._delegate,
                "_probe_path",
                return_value={
                    "duration_us": 3_000_000,
                    "has_video": True,
                    "has_audio": True,
                },
            ),
        ):
            result = self.adapter.execute(
                project_id=self.project.project_id,
                offer=_offer(),
                payload={
                    "workspace_revision_sha256": self.workspace.revision_sha256,
                    "audio_id": self.audio.id,
                },
            )

        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertEqual(command[0], "/tools/ffmpeg")
        self.assertIn("concat", command)
        self.assertIn(str(self.store.project_directory(self.project.project_id) / self.audio.path), command)
        self.assertNotIn(self.audio.id, command)
        self.assertEqual(result.output["workspace_revision_sha256"], self.workspace.revision_sha256)
        self.assertEqual(result.output["audio_id"], self.audio.id)

        current = self.store.load_project(self.project.project_id)
        artifact = next(item for item in current.artifacts if item.id == result.output["artifact_id"])
        self.assertEqual(artifact.metadata["lifecycle"], "narrated_video_render")
        self.assertEqual(artifact.metadata["workspace_revision_sha256"], self.workspace.revision_sha256)
        self.assertEqual(
            artifact.metadata["image_bindings"],
            [
                {
                    "source_id": self.image.id,
                    "path": self.image.path,
                    "sha256": hashlib.sha256(self.image_body).hexdigest(),
                    "size_bytes": len(self.image_body),
                }
            ],
        )
        self.assertEqual(artifact.metadata["audio_binding"]["audio_id"], self.audio.id)
        self.assertEqual(
            artifact.metadata["audio_binding"]["sha256"],
            hashlib.sha256(self.audio_body).hexdigest(),
        )
        output = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(artifact.metadata["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(list((self.store.project_directory(self.project.project_id) / "tasks").iterdir()), [])

    def test_stale_revision_and_tampered_audio_are_rejected_before_ffmpeg(self) -> None:
        invoke = mock.Mock()
        with mock.patch.object(self.adapter._delegate, "_invoke", invoke):
            with self.assertRaises(InvalidCapabilityInput):
                self.adapter.execute(
                    project_id=self.project.project_id,
                    offer=_offer(),
                    payload={
                        "workspace_revision_sha256": "0" * 64,
                        "audio_id": self.audio.id,
                    },
                )
        invoke.assert_not_called()

        audio_path = self.store.resolve_project_file(
            self.project.project_id,
            self.audio.path,
            must_exist=True,
            allowed_roots=("assets",),
        )
        audio_path.write_bytes(b"tampered-audio")
        invoke.reset_mock()
        with mock.patch.object(self.adapter._delegate, "_invoke", invoke):
            with self.assertRaises(InvalidCapabilityInput):
                self.adapter.execute(
                    project_id=self.project.project_id,
                    offer=_offer(),
                    payload={
                        "workspace_revision_sha256": self.workspace.revision_sha256,
                        "audio_id": self.audio.id,
                    },
                )
        invoke.assert_not_called()

    def test_registry_offer_is_local_free_and_requires_both_ffmpeg_tools(self) -> None:
        patch_target = "uv_studio.capabilities.adapters.narrated_render.shutil.which"
        from uv_studio.capabilities import build_builtin_capability_registry

        with mock.patch(patch_target, side_effect=lambda tool: f"/tools/{tool}"):
            available = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.render_narrated")
                if item.offer_id == "local_ffmpeg.video_render_narrated"
            )
        self.assertEqual(available.availability, OfferAvailability.AVAILABLE)
        self.assertEqual(available.locality, LocalityClass.LOCAL)
        self.assertEqual(available.cost_class, CostClass.FREE)

        with mock.patch(
            patch_target,
            side_effect=lambda tool: "/tools/ffmpeg" if tool == "ffmpeg" else None,
        ):
            unavailable = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.render_narrated")
                if item.offer_id == "local_ffmpeg.video_render_narrated"
            )
        self.assertEqual(unavailable.availability, OfferAvailability.UNAVAILABLE)
        self.assertIn("ffprobe", unavailable.reason)


if __name__ == "__main__":
    unittest.main()
