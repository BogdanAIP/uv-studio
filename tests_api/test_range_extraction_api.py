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


class RangeExtractionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Range API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "clip.mp4").write_bytes(b"source")
        self.calls: list[list[str]] = []

        def runner(command, **kwargs):
            self.calls.append(list(command))
            self.assertIs(kwargs["shell"], False)
            if command[0] == "fake-ffprobe":
                payload = {
                    "format": {
                        "duration": "8.000001",
                        "format_name": "mov,mp4",
                        "size": "1000",
                    },
                    "streams": [
                        {
                            "codec_type": "video",
                            "codec_name": "h264",
                            "width": 640,
                            "height": 360,
                            "avg_frame_rate": "30/1",
                        },
                        {"codec_type": "audio", "codec_name": "aac"},
                    ],
                }
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(payload),
                    stderr="",
                )
            Path(command[-1]).write_bytes(b"range-artifact")
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
            "video.extract_range",
            "Range",
            "Extract range",
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
                "local_ffmpeg.video_extract_range",
                "video.extract_range",
                "local_ffmpeg",
                "Range",
                OfferAvailability.AVAILABLE,
                "test",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
                ("video.range", "video.context"),
            )
        )
        return registry

    def _url(self, action: str = "execute") -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            f"/capabilities/video.extract_range/{action}"
        )

    @staticmethod
    def _body() -> dict:
        return {
            "selection_policy": "local_free_first",
            "input": {
                "source_path": "sources/clip.mp4",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
                "context_before_us": 1_000_000,
                "context_after_us": 1_000_000,
            },
        }

    def test_prepare_reports_local_free_execution_without_consent(self) -> None:
        response = self.client.post(self._url("prepare-execution"), json=self._body())
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_ffmpeg.video_extract_range",
        )
        authorization = payload["authorization"]
        self.assertFalse(authorization["authorization_required"])
        self.assertEqual(authorization["consent_required"], [])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")
        self.assertEqual(self.calls, [])

    def test_local_free_first_executes_range_without_authorization_token(self) -> None:
        response = self.client.post(self._url(), json=self._body())
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_ffmpeg.video_extract_range",
        )
        result = payload["result"]
        self.assertEqual(result["adapter_id"], "local_ffmpeg")
        self.assertEqual(result["capability_id"], "video.extract_range")
        self.assertTrue(result["output"]["requested_path"].startswith("artifacts/art_"))
        self.assertTrue(result["output"]["context_before_path"].startswith("artifacts/art_"))
        self.assertTrue(result["output"]["context_after_path"].startswith("artifacts/art_"))
        self.assertNotIn(str(self.project_dir), json.dumps(payload))

        ffprobe_calls = [command for command in self.calls if command[0] == "fake-ffprobe"]
        ffmpeg_calls = [command for command in self.calls if command[0] == "fake-ffmpeg"]
        self.assertEqual(len(ffprobe_calls), 4)
        self.assertEqual(len(ffmpeg_calls), 3)

        artifacts = self.store.load_project(self.project.project_id).artifacts
        self.assertEqual(len(artifacts), 3)
        self.assertEqual(
            [item.metadata["range_role"] for item in artifacts],
            ["context_before", "requested", "context_after"],
        )


if __name__ == "__main__":
    unittest.main()
