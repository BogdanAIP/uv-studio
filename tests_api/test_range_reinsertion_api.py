from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import get_local_ffmpeg_adapter
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class RangeReinsertionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(recipe_id="general_video", title="Range reinsertion API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.replacement = self.project_dir / "artifacts" / "replacement.mkv"
        self.source.write_bytes(b"source")
        self.replacement.write_bytes(b"replacement")
        self.calls: list[list[str]] = []

        def probe_payload(duration: str) -> dict:
            return {
                "format": {
                    "duration": duration,
                    "format_name": "matroska,webm",
                    "size": "1000",
                },
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "ffv1",
                        "width": 640,
                        "height": 360,
                        "duration": duration,
                        "start_time": "0.000000",
                        "avg_frame_rate": "0/0",
                    },
                    {
                        "codec_type": "audio",
                        "codec_name": "flac",
                        "duration": duration,
                        "start_time": "0.000000",
                    },
                ],
            }

        def runner(command, **kwargs):
            self.calls.append(list(command))
            self.assertIs(kwargs["shell"], False)
            if command[0] == "fake-ffprobe":
                target = Path(command[-1])
                duration = "8.000000" if target == self.source else "2.000000"
                if target != self.source and target != self.replacement:
                    duration = "8.000000"
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(probe_payload(duration)),
                    stderr="",
                )
            Path(command[-1]).write_bytes(b"edited-video")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        self.adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        self.registry = self._registry()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.adapter
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "video.replace_range",
            "Replace range",
            "Replace an exact existing-video interval",
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.VIDEO,),
            (MediaKind.VIDEO,),
            asynchronous=False,
        )
        adapter = AdapterDefinition(
            "local_ffmpeg",
            "Local FFmpeg",
            "Local deterministic media",
            AdapterKind.LOCAL,
        )
        registry = CapabilityRegistry((capability,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "local_ffmpeg.video_replace_range",
                "video.replace_range",
                "local_ffmpeg",
                "Replace range",
                OfferAvailability.AVAILABLE,
                "test",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
                ("video.range_replace", "video.reinsertion"),
            )
        )
        return registry

    def _url(self, action: str = "execute") -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            f"/capabilities/video.replace_range/{action}"
        )

    @staticmethod
    def _body() -> dict:
        return {
            "selection_policy": "local_free_first",
            "input": {
                "source_path": "sources/source.mkv",
                "replacement_path": "artifacts/replacement.mkv",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
            },
        }

    def test_prepare_is_local_free_and_requires_no_consent(self) -> None:
        response = self.client.post(self._url("prepare-execution"), json=self._body())
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_ffmpeg.video_replace_range",
        )
        self.assertFalse(payload["authorization"]["authorization_required"])
        self.assertEqual(payload["authorization"]["consent_required"], [])
        self.assertEqual(payload["authorization"]["cost_estimate"]["state"], "not_applicable")
        self.assertEqual(self.calls, [])

    def test_local_free_first_executes_reinsertion_without_token(self) -> None:
        response = self.client.post(self._url(), json=self._body())
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        result = payload["result"]
        self.assertEqual(result["adapter_id"], "local_ffmpeg")
        self.assertEqual(result["capability_id"], "video.replace_range")
        self.assertEqual(result["output"]["source_path"], "sources/source.mkv")
        self.assertEqual(result["output"]["replacement_path"], "artifacts/replacement.mkv")
        self.assertEqual(result["output"]["expected_output_video_duration_us"], 8_000_000)
        self.assertEqual(result["output"]["actual_output_video_duration_us"], 8_000_000)
        self.assertTrue(result["output"]["path"].startswith("artifacts/art_"))
        self.assertNotIn(str(self.project_dir), json.dumps(payload))

        ffprobe_calls = [command for command in self.calls if command[0] == "fake-ffprobe"]
        ffmpeg_calls = [command for command in self.calls if command[0] == "fake-ffmpeg"]
        self.assertEqual(len(ffprobe_calls), 3)
        self.assertEqual(len(ffmpeg_calls), 1)
        self.assertIn(
            "concat=n=3:v=1:a=1",
            ffmpeg_calls[0][ffmpeg_calls[0].index("-filter_complex") + 1],
        )

        artifacts = self.store.load_project(self.project.project_id).artifacts
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0].metadata["composition_mode"], "filter_concat_ffv1_flac_vfr")
        self.assertEqual(artifacts[0].metadata["source_av_start_delta_us"], 0)
        self.assertEqual(artifacts[0].metadata["replacement_av_start_delta_us"], 0)


if __name__ == "__main__":
    unittest.main()
