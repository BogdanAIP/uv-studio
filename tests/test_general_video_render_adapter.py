from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities import CapabilityOffer, CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import InvalidCapabilityInput
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.stage8_workspace import save_stage8_workspace
from uv_studio.projects.store import ProjectStore


def _offer() -> CapabilityOffer:
    return CapabilityOffer(
        offer_id="local_ffmpeg.video_render_general",
        capability_id="video.render_general",
        adapter_id="local_ffmpeg",
        title="General Video render",
        availability=OfferAvailability.AVAILABLE,
        reason="test runtime",
        locality=LocalityClass.LOCAL,
        cost_class=CostClass.FREE,
        asynchronous=False,
    )


class GeneralVideoRenderAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="General adapter", recipe_id="general_video")
        media = ProjectSourceMediaStore(self.store)

        self.image_body = b"general-image-fixture"
        image_allocation = media.allocate(self.project.project_id, "frame.png")
        image_allocation.absolute_path.write_bytes(self.image_body)
        updated = media.register(
            self.project.project_id,
            image_allocation,
            media_kind="image",
            metadata={
                "sha256": hashlib.sha256(self.image_body).hexdigest(),
                "size_bytes": len(self.image_body),
            },
        )
        self.image = next(item for item in updated.sources if item.id == image_allocation.source_id)
        self.workspace = save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Собрать обычный ролик",
            script="",
            source_ids=[self.image.id],
        )
        self.adapter = LocalFFmpegAdapter(
            self.store,
            tool_paths={"ffmpeg": "/tools/ffmpeg", "ffprobe": "/tools/ffprobe"},
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _register_audio(self, name: str = "music.wav"):
        media = ProjectSourceMediaStore(self.store)
        body = f"audio-{name}".encode()
        allocation = media.allocate(self.project.project_id, name)
        allocation.absolute_path.write_bytes(body)
        updated = media.register(
            self.project.project_id,
            allocation,
            media_kind="audio",
            metadata={
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        return next(item for item in updated.sources if item.id == allocation.source_id)

    def test_render_normalizes_workspace_visuals_and_registers_exact_fingerprints(self) -> None:
        commands: list[list[str]] = []

        def fake_invoke(command, **_kwargs):
            commands.append(list(command))
            Path(command[-1]).write_bytes(b"general-render-output")
            return None

        with (
            mock.patch.object(self.adapter._delegate, "_invoke", side_effect=fake_invoke),
            mock.patch.object(
                self.adapter._delegate,
                "_probe_path",
                return_value={
                    "duration_us": 2_000_000,
                    "has_video": True,
                    "has_audio": False,
                },
            ),
        ):
            result = self.adapter.execute(
                project_id=self.project.project_id,
                offer=_offer(),
                payload={"workspace_revision_sha256": self.workspace.revision_sha256},
            )

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][0], "/tools/ffmpeg")
        self.assertIn("-loop", commands[0])
        self.assertIn("concat", commands[1])
        self.assertEqual(result.output["workspace_revision_sha256"], self.workspace.revision_sha256)
        self.assertEqual(result.output["composition_mode"], "general_workspace_ordered_visuals")

        current = self.store.load_project(self.project.project_id)
        artifact = next(item for item in current.artifacts if item.id == result.output["artifact_id"])
        self.assertEqual(artifact.metadata["lifecycle"], "general_video_render")
        self.assertEqual(artifact.metadata["workspace_revision_sha256"], self.workspace.revision_sha256)
        self.assertEqual(
            artifact.metadata["visual_bindings"],
            [
                {
                    "source_id": self.image.id,
                    "kind": "image",
                    "path": self.image.path,
                    "sha256": hashlib.sha256(self.image_body).hexdigest(),
                    "size_bytes": len(self.image_body),
                    "duration_us": 2_000_000,
                    "embedded_audio_ignored": False,
                }
            ],
        )
        self.assertIsNone(artifact.metadata["audio_binding"])
        output = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(artifact.metadata["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(
            list((self.store.project_directory(self.project.project_id) / "tasks").glob("*.json")),
            [],
        )

    def test_stale_revision_tampered_visual_and_multiple_audio_are_rejected(self) -> None:
        invoke = mock.Mock()
        with mock.patch.object(self.adapter._delegate, "_invoke", invoke):
            with self.assertRaises(InvalidCapabilityInput):
                self.adapter.execute(
                    project_id=self.project.project_id,
                    offer=_offer(),
                    payload={"workspace_revision_sha256": "0" * 64},
                )
        invoke.assert_not_called()

        image_path = self.store.resolve_project_file(
            self.project.project_id,
            self.image.path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        image_path.write_bytes(b"tampered-image")
        with mock.patch.object(self.adapter._delegate, "_invoke", invoke):
            with self.assertRaises(InvalidCapabilityInput):
                self.adapter.execute(
                    project_id=self.project.project_id,
                    offer=_offer(),
                    payload={"workspace_revision_sha256": self.workspace.revision_sha256},
                )
        invoke.assert_not_called()

        image_path.write_bytes(self.image_body)
        audio_a = self._register_audio("a.wav")
        audio_b = self._register_audio("b.wav")
        ambiguous = save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Собрать обычный ролик",
            script="",
            source_ids=[self.image.id, audio_a.id, audio_b.id],
        )
        with mock.patch.object(self.adapter._delegate, "_invoke", invoke):
            with self.assertRaises(InvalidCapabilityInput):
                self.adapter.execute(
                    project_id=self.project.project_id,
                    offer=_offer(),
                    payload={"workspace_revision_sha256": ambiguous.revision_sha256},
                )
        invoke.assert_not_called()

    def test_registry_offer_is_local_free_and_requires_ffmpeg_and_ffprobe(self) -> None:
        from uv_studio.capabilities import build_builtin_capability_registry

        patch_target = "uv_studio.capabilities.adapters.general_video_render.shutil.which"
        with mock.patch(patch_target, side_effect=lambda tool: f"/tools/{tool}"):
            available = next(
                item
                for item in build_builtin_capability_registry().offers_for("video.render_general")
                if item.offer_id == "local_ffmpeg.video_render_general"
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
                for item in build_builtin_capability_registry().offers_for("video.render_general")
                if item.offer_id == "local_ffmpeg.video_render_general"
            )
        self.assertEqual(unavailable.availability, OfferAvailability.UNAVAILABLE)
        self.assertIn("ffprobe", unavailable.reason)


if __name__ == "__main__":
    unittest.main()
