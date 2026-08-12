from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from uv_studio.capabilities.adapters.mcp_execution import (
    MCPExecutionAdapter,
    MCPExecutionInputRejected,
    MCPExecutionOutputRejected,
)
from uv_studio.capabilities.authorization import prepare_execution
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
)
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.mcp.models import (
    MCPConfigurationError,
    MCPProjectFileInput,
    MCPProjectFileOutput,
    MCPToolBinding,
)
from uv_studio.projects import ProjectStore


class _FakeManager:
    def __init__(self, binding: MCPToolBinding, mode: str = "write") -> None:
        self.binding = binding
        self.mode = mode
        self.last_arguments = None

    def resolve_execution_target(self, offer):
        return SimpleNamespace(
            profile=SimpleNamespace(profile_id=self.binding.profile_id),
            binding=self.binding,
        )

    async def invoke_target(self, target, arguments):
        self.last_arguments = dict(arguments)
        path = Path(arguments["output_path"])
        if self.mode == "write":
            path.write_bytes(b"generated-video")
        elif self.mode == "empty":
            path.write_bytes(b"")
        elif self.mode == "missing":
            pass
        else:
            raise RuntimeError("unexpected fake mode")
        return {"ok": True}


class MCPProjectOutputModelTests(unittest.TestCase):
    def test_output_contract_is_strict_and_disjoint_from_inputs(self) -> None:
        output = MCPProjectFileOutput(
            argument_name="output_path",
            media_kind="video",
            suffix=".MP4",
        )
        self.assertEqual(output.media_kind, MediaKind.VIDEO)
        self.assertEqual(output.suffix, ".mp4")
        self.assertEqual(MCPProjectFileOutput.from_dict(output.to_dict()), output)

        with self.assertRaises(MCPConfigurationError):
            MCPProjectFileOutput(
                argument_name="output_path",
                media_kind="metadata",
                suffix=".json",
            )
        with self.assertRaises(MCPConfigurationError):
            MCPProjectFileOutput(
                argument_name="output_path",
                media_kind="video",
                suffix="../escape.mp4",
            )
        with self.assertRaises(MCPConfigurationError):
            MCPToolBinding(
                binding_id="binding_overlap",
                profile_id="profile_test",
                tool_name="tool",
                capability_id="video.generate",
                title="Overlap",
                locality="remote",
                cost_class="paid",
                asynchronous=True,
                project_file_inputs=(
                    MCPProjectFileInput(
                        argument_name="output_path",
                        allowed_roots=("sources",),
                    ),
                ),
                project_file_outputs=(output,),
            )


class MCPProjectOutputExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="MCP output")
        self.binding = MCPToolBinding(
            binding_id="binding_output",
            profile_id="profile_test",
            tool_name="write_project_output",
            capability_id="video.generate",
            title="Write output",
            locality="remote",
            cost_class="paid",
            asynchronous=True,
            project_file_outputs=(
                MCPProjectFileOutput(
                    argument_name="output_path",
                    media_kind="video",
                    suffix=".mp4",
                ),
            ),
        )
        self.offer = CapabilityOffer(
            offer_id="mcp.profile_test.binding_output",
            capability_id="video.generate",
            adapter_id="mcp.profile_test.binding_output",
            title="Write output",
            availability=OfferAvailability.AVAILABLE,
            reason="fixture ready",
            locality=LocalityClass.REMOTE,
            cost_class=CostClass.PAID,
            asynchronous=True,
        )
        self.payload = {"prompt": "test"}
        self.preparation = prepare_execution(
            project_id=self.project.project_id,
            offer=self.offer,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload=self.payload,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_adapter_injects_owned_path_and_registers_nonempty_artifact(self) -> None:
        manager = _FakeManager(self.binding, "write")
        result = await MCPExecutionAdapter(manager, self.store).execute(
            project_id=self.project.project_id,
            offer=self.offer,
            preparation=self.preparation,
            payload=self.payload,
        )

        self.assertIsNotNone(result.artifact)
        artifact = result.artifact
        self.assertEqual(artifact["kind"], "video")
        self.assertTrue(artifact["path"].startswith("artifacts/art_"))
        self.assertTrue((self.store.project_directory(self.project.project_id) / artifact["path"]).is_file())
        injected = manager.last_arguments["output_path"]
        self.assertTrue(Path(injected).is_absolute())
        self.assertEqual(Path(injected).name, Path(artifact["path"]).name)
        project = self.store.load_project(self.project.project_id)
        self.assertEqual(len(project.artifacts), 1)
        self.assertEqual(project.artifacts[0].id, artifact["id"])
        self.assertNotIn(str(self.store.root), str(project.to_dict()))

    async def test_missing_or_empty_required_output_rolls_back(self) -> None:
        for mode in ("missing", "empty"):
            with self.subTest(mode=mode):
                manager = _FakeManager(self.binding, mode)
                adapter = MCPExecutionAdapter(manager, self.store)
                with self.assertRaises(MCPExecutionOutputRejected):
                    await adapter.execute(
                        project_id=self.project.project_id,
                        offer=self.offer,
                        preparation=self.preparation,
                        payload=self.payload,
                    )
                project = self.store.load_project(self.project.project_id)
                self.assertEqual(project.artifacts, ())
                self.assertEqual(list((self.store.project_directory(self.project.project_id) / "artifacts").iterdir()), [])

    async def test_caller_cannot_supply_binding_owned_output_argument(self) -> None:
        manager = _FakeManager(self.binding, "write")
        adapter = MCPExecutionAdapter(manager, self.store)
        payload = {"prompt": "test", "output_path": "artifacts/user.mp4"}
        preparation = prepare_execution(
            project_id=self.project.project_id,
            offer=self.offer,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload=payload,
        )
        with self.assertRaises(MCPExecutionInputRejected):
            await adapter.execute(
                project_id=self.project.project_id,
                offer=self.offer,
                preparation=preparation,
                payload=payload,
            )
        self.assertIsNone(manager.last_arguments)
        self.assertEqual(list((self.store.project_directory(self.project.project_id) / "artifacts").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
