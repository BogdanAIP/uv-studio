from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.adapters.musetalk import (
    MUSE_TALK_UPSTREAM_COMMIT,
    MuseTalkAdapter,
    _REQUIRED_RELATIVE_PATHS,
)
from uv_studio.capabilities.execution import CapabilityToolFailed, InvalidCapabilityInput
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore


class MuseTalkAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root / "projects")
        self.project = self.store.create_project(
            title="MuseTalk test",
            recipe_id="performance_lip_sync",
            project_id="prj_musetalk",
        )
        self.pack = self.root / "MuseTalk"
        self.pack.mkdir()
        for relative in _REQUIRED_RELATIVE_PATHS:
            path = self.pack / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"runtime")
        self.python = self.pack / "python.exe"
        self.python.write_bytes(b"python")
        self.ffmpeg = self.root / "ffmpeg.exe"
        self.ffprobe = self.root / "ffprobe.exe"
        self.ffmpeg.write_bytes(b"ffmpeg")
        self.ffprobe.write_bytes(b"ffprobe")
        self.media = ProjectSourceMediaStore(self.store)
        self.portrait = self._source("portrait.png", "image", b"portrait", {"width": 512, "height": 512})
        self.speech = self._source(
            "speech.wav",
            "audio",
            b"speech",
            {"duration_us": 3_000_000, "has_audio": True},
        )
        self.offer = CapabilityOffer(
            offer_id="local_musetalk.video_digital_human",
            capability_id="video.digital_human",
            adapter_id="local_musetalk",
            title="MuseTalk test",
            availability=OfferAvailability.AVAILABLE,
            reason="configured",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _source(self, filename: str, kind: str, body: bytes, extra: dict[str, object]):
        allocation = self.media.allocate(self.project.project_id, filename)
        allocation.absolute_path.write_bytes(body)
        metadata = {
            "original_name": filename,
            "size_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            **extra,
        }
        project = self.media.register(
            self.project.project_id,
            allocation,
            metadata=metadata,
            media_kind=kind,
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _runner(self, command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        if command[0] == str(self.ffmpeg):
            Path(command[-1]).write_bytes(b"avatar-video")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "scripts.inference" in command:
            result_dir = Path(command[command.index("--result_dir") + 1])
            output = result_dir / "v15" / "output.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"musetalk-output")
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[0] == str(self.ffprobe):
            payload = {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 512, "height": 512},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"duration": "3.000"},
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        raise AssertionError(f"unexpected command: {command!r}")

    def _adapter(self, runner=None) -> MuseTalkAdapter:
        return MuseTalkAdapter(
            self.store,
            runner=runner or self._runner,
            root_path=self.pack,
            python_path=self.python,
            ffmpeg_path=self.ffmpeg,
            ffprobe_path=self.ffprobe,
        )

    def test_exact_project_sources_produce_sha_bound_artifact(self) -> None:
        with mock.patch(
            "uv_studio.capabilities.adapters.musetalk.shutil.which",
            side_effect=lambda tool: str(self.ffmpeg if tool == "ffmpeg" else self.ffprobe),
        ):
            result = self._adapter().execute(
                project_id=self.project.project_id,
                offer=self.offer,
                payload={
                    "portrait_source_id": self.portrait.id,
                    "speech_source_id": self.speech.id,
                },
            )
        self.assertEqual(result.output["engine"], "musetalk_v15")
        artifact = self.store.load_project(self.project.project_id).artifacts[-1]
        self.assertEqual(artifact.metadata["upstream_commit"], MUSE_TALK_UPSTREAM_COMMIT)
        self.assertEqual(artifact.metadata["portrait_binding"]["source_id"], self.portrait.id)
        self.assertEqual(artifact.metadata["speech_binding"]["source_id"], self.speech.id)
        self.assertEqual(artifact.metadata["expected_duration_us"], 3_000_000)
        self.assertEqual(artifact.metadata["actual_duration_us"], 3_000_000)
        path = self.store.resolve_project_file(
            self.project.project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(artifact.metadata["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_substituted_source_fails_before_runtime_execution(self) -> None:
        path = self.store.resolve_project_file(
            self.project.project_id,
            self.portrait.path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        path.write_bytes(b"substituted")
        calls: list[list[str]] = []

        def runner(command: list[str], **kwargs):
            calls.append(command)
            raise AssertionError("runtime must not execute after source substitution")

        with self.assertRaises(InvalidCapabilityInput):
            self._adapter(runner=runner).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                payload={
                    "portrait_source_id": self.portrait.id,
                    "speech_source_id": self.speech.id,
                },
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

    def test_success_exit_without_expected_output_fails_closed(self) -> None:
        def runner(command: list[str], **kwargs):
            if command[0] == str(self.ffmpeg):
                Path(command[-1]).write_bytes(b"avatar-video")
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch(
            "uv_studio.capabilities.adapters.musetalk.shutil.which",
            side_effect=lambda tool: str(self.ffmpeg if tool == "ffmpeg" else self.ffprobe),
        ):
            with self.assertRaises(CapabilityToolFailed):
                self._adapter(runner=runner).execute(
                    project_id=self.project.project_id,
                    offer=self.offer,
                    payload={
                        "portrait_source_id": self.portrait.id,
                        "speech_source_id": self.speech.id,
                    },
                )
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

    def test_arbitrary_runtime_fields_are_rejected(self) -> None:
        with self.assertRaises(InvalidCapabilityInput):
            self._adapter().execute(
                project_id=self.project.project_id,
                offer=self.offer,
                payload={
                    "portrait_source_id": self.portrait.id,
                    "speech_source_id": self.speech.id,
                    "command": "rm -rf /",
                },
            )


if __name__ == "__main__":
    unittest.main()
