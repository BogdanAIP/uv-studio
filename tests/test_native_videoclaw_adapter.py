from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.adapters.native_videoclaw import NativeVideoClawAdapter
from uv_studio.capabilities.authorization import ConsentScope, prepare_execution
from uv_studio.capabilities.execution import (
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.projects.store import ProjectStore


def edge_offer() -> CapabilityOffer:
    return CapabilityOffer(
        offer_id="native_videoclaw.edge_tts",
        capability_id="speech.synthesize",
        adapter_id="native_videoclaw",
        title="Edge TTS",
        availability=OfferAvailability.AVAILABLE,
        reason="edge-tts installed",
        locality=LocalityClass.REMOTE,
        cost_class=CostClass.FREE,
        asynchronous=True,
        features=("speech.keyless",),
    )


class FakeCommunicate:
    def __init__(self, *, calls: list[dict[str, object]], text: str, voice: str, rate: str) -> None:
        self.calls = calls
        self.text = text
        self.voice = voice
        self.rate = rate

    async def save(self, path: str) -> None:
        self.calls.append(
            {
                "text": self.text,
                "voice": self.voice,
                "rate": self.rate,
                "path": path,
            }
        )
        Path(path).write_bytes(b"ID3-uv-studio-edge-tts-test")


class FailingCommunicate(FakeCommunicate):
    async def save(self, path: str) -> None:
        self.calls.append(
            {
                "text": self.text,
                "voice": self.voice,
                "rate": self.rate,
                "path": path,
            }
        )
        Path(path).write_bytes(b"partial")
        raise RuntimeError("provider detail that must not be returned")


class EmptyCommunicate(FakeCommunicate):
    async def save(self, path: str) -> None:
        self.calls.append(
            {
                "text": self.text,
                "voice": self.voice,
                "rate": self.rate,
                "path": path,
            }
        )
        Path(path).write_bytes(b"")


class NativeVideoClawAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Native TTS")
        self.offer = edge_offer()
        self.calls: list[dict[str, object]] = []

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def preparation(self, payload: dict[str, object]):
        return prepare_execution(
            project_id=self.project.project_id,
            offer=self.offer,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload=payload,
        )

    def factory(self, *, text: str, voice: str, rate: str):
        return FakeCommunicate(calls=self.calls, text=text, voice=voice, rate=rate)

    async def test_success_matches_pinned_videoclaw_contract_and_registers_portable_artifact(self) -> None:
        payload = {
            "text": "Hello from UV Studio",
            "voice": "en-US-AriaNeural",
            "speed": 1.25,
        }
        preparation = self.preparation(payload)
        self.assertEqual(preparation.consent_required, (ConsentScope.REMOTE_EXECUTION,))

        result = await NativeVideoClawAdapter(
            self.store,
            communicate_factory=self.factory,
        ).execute(
            project_id=self.project.project_id,
            offer=self.offer,
            preparation=preparation,
            payload=payload,
        )

        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["text"], payload["text"])
        self.assertEqual(self.calls[0]["voice"], payload["voice"])
        self.assertEqual(self.calls[0]["rate"], "+25%")
        output_path = result.output["path"]
        self.assertTrue(output_path.startswith("artifacts/art_"))
        self.assertTrue(output_path.endswith(".mp3"))
        self.assertNotIn(str(self.store.root), json.dumps(result.to_dict()))
        resolved = self.store.resolve_project_file(
            self.project.project_id,
            output_path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertTrue(resolved.is_file())
        self.assertGreater(resolved.stat().st_size, 0)

        loaded = self.store.load_project(self.project.project_id)
        self.assertEqual(len(loaded.artifacts), 1)
        artifact = loaded.artifacts[0]
        self.assertEqual(artifact.kind, "audio")
        self.assertEqual(artifact.path, output_path)
        self.assertEqual(artifact.metadata["offer_id"], "native_videoclaw.edge_tts")
        self.assertNotIn("text", artifact.metadata)

        run_path = self.store.resolve_project_file(
            self.project.project_id,
            f"tasks/{result.output['run_id']}.json",
            must_exist=True,
            allowed_roots=("tasks",),
        )
        run = json.loads(run_path.read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "succeeded")
        self.assertEqual(run["profile_id"], "native_videoclaw")
        self.assertEqual(run["tool_name"], "edge_tts")
        self.assertEqual(run["authorization"]["consent_scopes"], ["remote_execution"])
        self.assertEqual(run["input_digest"], preparation.intent.input_digest)
        serialized_run = json.dumps(run, ensure_ascii=False)
        self.assertNotIn(payload["text"], serialized_run)
        self.assertNotIn(str(self.store.root), serialized_run)

    async def test_default_voice_and_video_claw_speed_rounding_are_preserved(self) -> None:
        payload = {"text": "Default voice", "speed": 0.9}
        await NativeVideoClawAdapter(
            self.store,
            communicate_factory=self.factory,
        ).execute(
            project_id=self.project.project_id,
            offer=self.offer,
            preparation=self.preparation(payload),
            payload=payload,
        )
        self.assertEqual(self.calls[0]["voice"], "zh-CN-YunjianNeural")
        self.assertEqual(self.calls[0]["rate"], "-10%")

    async def test_arbitrary_native_videoclaw_offer_is_never_executed(self) -> None:
        other = CapabilityOffer(
            offer_id="native_videoclaw.video_generate",
            capability_id="video.generate",
            adapter_id="native_videoclaw",
            title="Video",
            availability=OfferAvailability.AVAILABLE,
            reason="test",
            locality=LocalityClass.REMOTE,
            cost_class=CostClass.FREE,
            asynchronous=True,
        )
        preparation = prepare_execution(
            project_id=self.project.project_id,
            offer=other,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={"prompt": "x"},
        )
        with self.assertRaises(UnsupportedCapabilityExecution):
            await NativeVideoClawAdapter(
                self.store,
                communicate_factory=self.factory,
            ).execute(
                project_id=self.project.project_id,
                offer=other,
                preparation=preparation,
                payload={"prompt": "x"},
            )
        self.assertEqual(self.calls, [])

    async def test_caller_cannot_choose_output_path_or_unknown_fields(self) -> None:
        payload = {"text": "x", "output_path": "artifacts/chosen.mp3"}
        with self.assertRaises(InvalidCapabilityInput):
            await NativeVideoClawAdapter(
                self.store,
                communicate_factory=self.factory,
            ).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                preparation=self.preparation(payload),
                payload=payload,
            )
        self.assertEqual(self.calls, [])

    async def test_broken_edge_tts_dependency_fails_before_provenance_or_network(self) -> None:
        payload = {"text": "dependency check"}
        for import_failure in (
            ImportError("edge_tts missing"),
            RuntimeError("broken optional dependency detail"),
        ):
            with self.subTest(import_failure=type(import_failure).__name__):
                adapter = NativeVideoClawAdapter(self.store)
                with mock.patch(
                    "uv_studio.capabilities.adapters.native_videoclaw.importlib.import_module",
                    side_effect=import_failure,
                ):
                    with self.assertRaises(CapabilityToolUnavailable) as caught:
                        await adapter.execute(
                            project_id=self.project.project_id,
                            offer=self.offer,
                            preparation=self.preparation(payload),
                            payload=payload,
                        )
                self.assertEqual(
                    str(caught.exception),
                    "edge-tts could not be loaded in this installation",
                )
        project_dir = self.store.project_directory(self.project.project_id)
        self.assertEqual(list((project_dir / "artifacts").iterdir()), [])
        self.assertEqual(list((project_dir / "tasks").iterdir()), [])

    async def test_constructor_failure_is_sanitized_and_recorded(self) -> None:
        payload = {"text": "constructor failure"}

        def failing_factory(*, text: str, voice: str, rate: str):
            raise RuntimeError("constructor provider detail that must not escape")

        with self.assertRaises(CapabilityToolFailed) as caught:
            await NativeVideoClawAdapter(
                self.store,
                communicate_factory=failing_factory,
            ).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                preparation=self.preparation(payload),
                payload=payload,
            )
        self.assertEqual(str(caught.exception), "edge-tts synthesis failed")
        project_dir = self.store.project_directory(self.project.project_id)
        self.assertEqual(list((project_dir / "artifacts").iterdir()), [])
        task_files = list((project_dir / "tasks").glob("run_*.json"))
        self.assertEqual(len(task_files), 1)
        run = json.loads(task_files[0].read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["error"]["code"], "capability_tool_failed")
        self.assertNotIn("constructor provider detail", json.dumps(run))

    async def test_empty_provider_output_is_rejected_and_removed(self) -> None:
        payload = {"text": "empty output"}

        def empty_factory(*, text: str, voice: str, rate: str):
            return EmptyCommunicate(calls=self.calls, text=text, voice=voice, rate=rate)

        with self.assertRaises(CapabilityToolFailed) as caught:
            await NativeVideoClawAdapter(
                self.store,
                communicate_factory=empty_factory,
            ).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                preparation=self.preparation(payload),
                payload=payload,
            )
        self.assertEqual(
            str(caught.exception),
            "edge-tts reported success but output file is empty or missing",
        )
        project_dir = self.store.project_directory(self.project.project_id)
        self.assertEqual(list((project_dir / "artifacts").iterdir()), [])
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())
        task_files = list((project_dir / "tasks").glob("run_*.json"))
        self.assertEqual(len(task_files), 1)
        run = json.loads(task_files[0].read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["error"]["code"], "capability_tool_failed")

    async def test_provider_failure_removes_partial_artifact_and_writes_sanitized_failure(self) -> None:
        payload = {"text": "failure"}

        def failing_factory(*, text: str, voice: str, rate: str):
            return FailingCommunicate(calls=self.calls, text=text, voice=voice, rate=rate)

        with self.assertRaises(CapabilityToolFailed) as caught:
            await NativeVideoClawAdapter(
                self.store,
                communicate_factory=failing_factory,
            ).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                preparation=self.preparation(payload),
                payload=payload,
            )
        self.assertEqual(str(caught.exception), "edge-tts synthesis failed")
        self.assertEqual(list((self.store.project_directory(self.project.project_id) / "artifacts").iterdir()), [])
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

        task_files = list((self.store.project_directory(self.project.project_id) / "tasks").glob("run_*.json"))
        self.assertEqual(len(task_files), 1)
        run = json.loads(task_files[0].read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["error"]["code"], "capability_tool_failed")
        self.assertNotIn("provider detail", json.dumps(run))


if __name__ == "__main__":
    unittest.main()
