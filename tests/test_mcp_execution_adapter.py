from __future__ import annotations

import unittest

from uv_studio.capabilities.adapters.mcp_execution import (
    MCPExecutionAdapter,
    MCPExecutionInputRejected,
)


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

    def test_relative_project_reference_remains_opaque_data(self) -> None:
        MCPExecutionAdapter._reject_raw_host_paths(
            {"source": "sources/clip.mp4", "nested": ["assets/reference.png"]}
        )


if __name__ == "__main__":
    unittest.main()
