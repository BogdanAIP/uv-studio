from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.consent import CostEstimateState, ExecutionCostEstimate
from uv_studio.capabilities.external_runs import (
    ExternalRunStatus,
    ExternalRunStore,
)
from uv_studio.projects.store import ProjectStore


class ExternalRunStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.projects.create_project(title="External runs")
        self.runs = ExternalRunStore(self.projects)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _start(self):
        return self.runs.start(
            project_id=self.project.project_id,
            capability_id="media.understand",
            offer_id="mcp.fixture.echo",
            adapter_id="mcp.fixture",
            tool_identity="fixture/echo_metadata",
            input_digest="a" * 64,
            authorization_mode="one_shot",
            authorization_grant_id="grant_1234567890abcdef",
            cost_estimate=ExecutionCostEstimate(CostEstimateState.UNKNOWN),
        )

    def test_start_succeed_and_load_round_trip(self) -> None:
        running = self._start()
        self.assertEqual(running.status, ExternalRunStatus.RUNNING)
        completed = self.runs.succeed(
            running,
            result_summary={"content_count": 1, "structured": True},
        )
        loaded = self.runs.load(self.project.project_id, running.run_id)
        self.assertEqual(loaded.status, ExternalRunStatus.SUCCEEDED)
        self.assertEqual(loaded.result_summary["content_count"], 1)
        self.assertEqual(loaded.completed_at, completed.completed_at)

    def test_failure_is_durable_and_error_is_bounded(self) -> None:
        running = self._start()
        failed = self.runs.fail(running, RuntimeError("boom" * 1000))
        loaded = self.runs.load(self.project.project_id, running.run_id)
        self.assertEqual(loaded.status, ExternalRunStatus.FAILED)
        self.assertEqual(loaded.error_class, "RuntimeError")
        self.assertLessEqual(len(loaded.error_message), 2000)
        self.assertEqual(loaded.completed_at, failed.completed_at)

    def test_record_contains_grant_id_but_no_authorization_token_or_secret(self) -> None:
        running = self._start()
        path = self.projects.project_directory(self.project.project_id) / "tasks" / f"{running.run_id}.external.json"
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        self.assertEqual(payload["authorization_grant_id"], "grant_1234567890abcdef")
        self.assertNotIn("authorization_token", raw)
        self.assertNotIn("super-secret", raw)


if __name__ == "__main__":
    unittest.main()
