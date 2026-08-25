from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters.mcp_execution import (
    MCPExecutionAdapter,
    MCPExecutionInputRejected,
)
from uv_studio.capabilities.models import CostClass, LocalityClass
from uv_studio.mcp.models import MCPProjectFileInput, MCPToolBinding
from uv_studio.projects.store import ProjectStore


class MCPExecutionAdapterInputTests(unittest.TestCase):
    def test_rejects_absolute_posix_path(self) -> None:
        with self.assertRaises(MCPExecutionInputRejected):
            MCPExecutionAdapter._reject_raw_host_paths({"path": "/tmp/private.mp4"})

    def test_rejects_absolute_windows_path(self) -> None:
        with self.assertRaises(MCPExecutionInputRejected):
            MCPExecutionAdapter._reject_raw_host_paths({"path": "C:\\Users\\user\\private.mp4"})

    def test_rejects_unc_and_file_uri(self) -> None:
        with self.assertRaises(MCPExecutionInputRejected):
            MCPExecutionAdapter._reject_raw_host_paths({"path": "\\\\server\\share\\file.mp4"})
        with self.assertRaises(MCPExecutionInputRejected):
            MCPExecutionAdapter._reject_raw_host_paths({"path": "file:///tmp/private.mp4"})

    def test_relative_project_reference_remains_opaque_without_contract(self) -> None:
        MCPExecutionAdapter._reject_raw_host_paths(
            {"source": "sources/clip.mp4", "nested": ["assets/reference.png"]}
        )

    def test_declared_file_input_resolves_only_declared_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(recipe_id="general_video", title="File input")
            source = store.project_directory(project.project_id) / "sources" / "clip.txt"
            source.write_text("portable input\n", encoding="utf-8")
            adapter = MCPExecutionAdapter(object(), store)
            binding = self._binding(
                project_file_inputs=(
                    MCPProjectFileInput(argument_name="path", allowed_roots=("sources",)),
                )
            )

            translated = adapter._translate_project_file_inputs(
                project_id=project.project_id,
                binding=binding,
                payload={"path": "sources/clip.txt", "label": "assets/not-a-file-translation.png"},
            )

            self.assertEqual(Path(translated["path"]), source.resolve())
            self.assertTrue(Path(translated["path"]).is_absolute())
            self.assertEqual(translated["label"], "assets/not-a-file-translation.png")

    def test_declared_file_input_rejects_wrong_root_missing_file_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(recipe_id="general_video", title="File input rejection")
            asset = store.project_directory(project.project_id) / "assets" / "asset.txt"
            asset.write_text("asset\n", encoding="utf-8")
            adapter = MCPExecutionAdapter(object(), store)
            binding = self._binding(
                project_file_inputs=(
                    MCPProjectFileInput(argument_name="path", allowed_roots=("sources",)),
                )
            )

            for value in ("assets/asset.txt", "sources/missing.txt", "sources/../assets/asset.txt"):
                with self.subTest(value=value), self.assertRaises(MCPExecutionInputRejected):
                    adapter._translate_project_file_inputs(
                        project_id=project.project_id,
                        binding=binding,
                        payload={"path": value},
                    )

    def test_required_declared_file_input_must_be_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(recipe_id="general_video", title="Required file")
            adapter = MCPExecutionAdapter(object(), store)
            binding = self._binding(
                project_file_inputs=(
                    MCPProjectFileInput(argument_name="path", allowed_roots=("sources",)),
                )
            )
            with self.assertRaises(MCPExecutionInputRejected):
                adapter._translate_project_file_inputs(
                    project_id=project.project_id,
                    binding=binding,
                    payload={},
                )

    @staticmethod
    def _binding(*, project_file_inputs=()) -> MCPToolBinding:
        return MCPToolBinding(
            binding_id="fixture.file",
            profile_id="fixture",
            tool_name="read_project_file",
            capability_id="media.understand",
            title="Fixture file",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            project_file_inputs=project_file_inputs,
        )


if __name__ == "__main__":
    unittest.main()
