from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from uv_studio.capabilities.adapters.native_videoclaw import NativeVideoClawAdapter
from uv_studio.capabilities.authorization import prepare_execution
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.projects.archive import export_project
from uv_studio.projects.store import ProjectStore


class FakeEdgeTTSRuntime:
    def available(self) -> bool:
        return True

    async def save(self, *, text, voice, rate, output_path) -> None:
        Path(output_path).write_bytes(b"ID3archive-native-edge-tts")


class NativeVideoClawArchiveTests(unittest.TestCase):
    def test_archive_keeps_portable_native_artifact_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProjectStore(root / "projects")
            project = store.create_project(title="Native archive")
            offer = CapabilityOffer(
                offer_id="native_videoclaw.edge_tts",
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
            payload = {"text": "Archive me", "voice": "en-US-GuyNeural", "speed": 1.0}
            preparation = prepare_execution(
                project_id=project.project_id,
                offer=offer,
                selection_policy=SelectionPolicy.PINNED_OFFER,
                payload=payload,
            )
            result = asyncio.run(
                NativeVideoClawAdapter(
                    store,
                    edge_tts_runtime=FakeEdgeTTSRuntime(),
                ).execute(
                    project_id=project.project_id,
                    offer=offer,
                    preparation=preparation,
                    payload=payload,
                )
            )
            artifact = result.output["artifact"]
            archive_path = export_project(
                store,
                project.project_id,
                root / "native.uvproj.zip",
            )

            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
                self.assertIn(f"project/{artifact}", names)
                task_names = sorted(
                    name
                    for name in names
                    if name.startswith("project/tasks/run_") and name.endswith(".json")
                )
                self.assertEqual(len(task_names), 1)
                record_text = archive.read(task_names[0]).decode("utf-8")
                record = json.loads(record_text)
                self.assertEqual(record["executor"]["kind"], "native_videoclaw")
                self.assertEqual(
                    record["result_summary"]["references"],
                    {"artifact": artifact},
                )
                self.assertNotIn(str(root.resolve()), record_text)
                self.assertNotIn("authorization_token", record_text)


if __name__ == "__main__":
    unittest.main()
