from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters.native_videoclaw import (
    EDGE_TTS_OFFER_ID,
    NativeVideoClawAdapter,
    NativeVideoClawDependencyUnavailable,
    NativeVideoClawExecutionError,
    NativeVideoClawInputRejected,
    NativeVideoClawRemoteFailed,
)
from uv_studio.capabilities.authorization import prepare_execution
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.projects.store import ProjectStore


class FakeEdgeTTSRuntime:
    def __init__(self, *, available: bool = True, fail: bool = False) -> None:
        self._available = available
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def available(self) -> bool:
        return self._available

    async def save(self, *, text, voice, rate, output_path) -> None:
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "rate": rate,
                "output_path": Path(output_path),
            }
        )
        if self.fail:
            Path(output_path).write_bytes(b"partial")
            raise RuntimeError("provider-secret-error-body")
        Path(output_path).write_bytes(b"ID3fake-edge-tts-audio")


class NativeVideoClawAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Native TTS")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _offer(*, offer_id: str = EDGE_TTS_OFFER_ID) -> CapabilityOffer:
        return CapabilityOffer(
            offer_id=offer_id,
            capability_id="speech.synthesize",
            adapter_id="native_videoclaw",
            title="Edge TTS",
            availability=OfferAvailability.AVAILABLE,
            reason="test",
            locality=LocalityClass.REMOTE,
            cost_class=CostClass.FREE,
            asynchronous=True,
            features=("speech.tts",),
        )

    def _preparation(self, offer: CapabilityOffer, payload: dict) -> object:
        return prepare_execution(
            project_id=self.project.project_id,
            offer=offer,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload=payload,
        )

    def _records(self) -> list[dict]:
        task_dir = self.store.project_directory(self.project.project_id) / "tasks"
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(task_dir.glob("run_*.json"))
        ]

    def test_success_writes_canonical_artifact_and_v2_native_provenance(self) -> None:
        runtime = FakeEdgeTTSRuntime()
        adapter = NativeVideoClawAdapter(self.store, edge_tts_runtime=runtime)
        offer = self._offer()
        payload = {"text": "Hello", "voice": "en-US-GuyNeural", "speed": 1.25}
        result = asyncio.run(
            adapter.execute(
                project_id=self.project.project_id,
                offer=offer,
                preparation=self._preparation(offer, payload),
                payload=payload,
            )
        )

        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.calls[0]["rate"], "+25%")
        artifact = result.output["artifact"]
        self.assertTrue(artifact.startswith("artifacts/run_"))
        self.assertTrue(artifact.endswith(".mp3"))
        artifact_path = self.store.resolve_project_file(
            self.project.project_id,
            artifact,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(artifact_path.read_bytes(), b"ID3fake-edge-tts-audio")

        record = self._records()[0]
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(record["executor"]["kind"], "native_videoclaw")
        self.assertEqual(record["executor"]["identity"], {"operation": "edge_tts"})
        self.assertEqual(record["result_summary"]["references"], {"artifact": artifact})
        serialized = json.dumps(record)
        self.assertNotIn(str(self.store.project_directory(self.project.project_id)), serialized)
        self.assertNotIn("authorization_token", serialized)

    def test_dependency_unavailable_fails_before_run_record(self) -> None:
        runtime = FakeEdgeTTSRuntime(available=False)
        adapter = NativeVideoClawAdapter(self.store, edge_tts_runtime=runtime)
        offer = self._offer()
        payload = {"text": "Hello"}
        with self.assertRaises(NativeVideoClawDependencyUnavailable):
            asyncio.run(
                adapter.execute(
                    project_id=self.project.project_id,
                    offer=offer,
                    preparation=self._preparation(offer, payload),
                    payload=payload,
                )
            )
        self.assertEqual(runtime.calls, [])
        self.assertEqual(self._records(), [])

    def test_remote_failure_removes_partial_artifact_and_writes_safe_failure(self) -> None:
        runtime = FakeEdgeTTSRuntime(fail=True)
        adapter = NativeVideoClawAdapter(self.store, edge_tts_runtime=runtime)
        offer = self._offer()
        payload = {"text": "Hello"}
        with self.assertRaises(NativeVideoClawRemoteFailed):
            asyncio.run(
                adapter.execute(
                    project_id=self.project.project_id,
                    offer=offer,
                    preparation=self._preparation(offer, payload),
                    payload=payload,
                )
            )
        record = self._records()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error"]["code"], "native_videoclaw_remote_failed")
        self.assertNotIn("provider-secret-error-body", json.dumps(record))
        artifact_dir = self.store.project_directory(self.project.project_id) / "artifacts"
        self.assertEqual(list(artifact_dir.glob("run_*.mp3")), [])

    def test_input_is_bounded_and_does_not_accept_output_path(self) -> None:
        with self.assertRaises(NativeVideoClawInputRejected):
            NativeVideoClawAdapter._parse_edge_tts_input({"text": "ok", "output_path": "x.mp3"})
        with self.assertRaises(NativeVideoClawInputRejected):
            NativeVideoClawAdapter._parse_edge_tts_input({"text": "x" * 20_001})
        with self.assertRaises(NativeVideoClawInputRejected):
            NativeVideoClawAdapter._parse_edge_tts_input({"text": "ok", "speed": 2.1})
        with self.assertRaises(NativeVideoClawInputRejected):
            NativeVideoClawAdapter._parse_edge_tts_input({"text": "ok", "voice": "bad voice"})

    def test_unknown_native_offer_has_no_dynamic_execution_fallback(self) -> None:
        adapter = NativeVideoClawAdapter(self.store, edge_tts_runtime=FakeEdgeTTSRuntime())
        offer = self._offer(offer_id="native_videoclaw.arbitrary_python_function")
        payload = {"text": "Hello"}
        with self.assertRaises(NativeVideoClawExecutionError):
            asyncio.run(
                adapter.execute(
                    project_id=self.project.project_id,
                    offer=offer,
                    preparation=self._preparation(offer, payload),
                    payload=payload,
                )
            )


if __name__ == "__main__":
    unittest.main()
