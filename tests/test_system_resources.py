from __future__ import annotations

import json
import unittest

from uv_studio.system_resources import build_system_resource_snapshot


class SystemResourceDiagnosticsTests(unittest.TestCase):
    def test_snapshot_reports_cpu_and_memory_without_machine_identity(self) -> None:
        snapshot = build_system_resource_snapshot(
            cpu_probe=lambda: 4,
            memory_probe=lambda: (
                8 * 1024**3,
                3 * 1024**3,
                "windows_global_memory_status",
            ),
        )
        self.assertEqual(snapshot["logical_cpu_count"], 4)
        self.assertEqual(snapshot["memory"]["total_bytes"], 8 * 1024**3)
        self.assertEqual(snapshot["memory"]["available_bytes"], 3 * 1024**3)
        encoded = json.dumps(snapshot).lower()
        self.assertNotIn("hostname", encoded)
        self.assertNotIn("username", encoded)
        self.assertNotIn("environment", encoded)
        self.assertNotIn("processes", encoded)

    def test_invalid_or_unavailable_probe_values_fail_soft(self) -> None:
        snapshot = build_system_resource_snapshot(
            cpu_probe=lambda: 0,
            memory_probe=lambda: (1024, 2048, "unknown-provider"),
        )
        self.assertIsNone(snapshot["logical_cpu_count"])
        self.assertEqual(snapshot["memory"]["total_bytes"], 1024)
        self.assertIsNone(snapshot["memory"]["available_bytes"])
        self.assertEqual(snapshot["memory"]["source"], "unavailable")

    def test_probe_exceptions_do_not_break_product_diagnostics(self) -> None:
        def cpu_probe():
            raise OSError("cpu probe unavailable")

        def memory_probe():
            raise RuntimeError("memory probe unavailable")

        snapshot = build_system_resource_snapshot(
            cpu_probe=cpu_probe,
            memory_probe=memory_probe,
        )
        self.assertIsNone(snapshot["logical_cpu_count"])
        self.assertIsNone(snapshot["memory"]["total_bytes"])
        self.assertIsNone(snapshot["memory"]["available_bytes"])
        self.assertEqual(snapshot["memory"]["source"], "unavailable")


if __name__ == "__main__":
    unittest.main()
