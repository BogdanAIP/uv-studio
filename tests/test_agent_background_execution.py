from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentBackgroundContextStale,
    AgentBackgroundLeaseConflict,
    AgentBackgroundLeaseStale,
    AgentBackgroundTaskCoordinator,
    AgentBackgroundWorker,
    AgentHarness,
    AgentPlanStepProposal,
    AgentTaskStatus,
    AgentTraceRecord,
    AgentTraceStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 28, 5, 30, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class _CrashOnSuccessTraceStore:
    """Simulate process loss after canonical commit but before success trace append."""

    def __init__(self, base: Any) -> None:
        self._base = base

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def append(self, record: AgentTraceRecord):
        if record.status is AgentTraceStatus.SUCCEEDED:
            raise SystemExit("simulated post-commit/pre-trace process loss")
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class _CrashAfterLeaseCoordinator(AgentBackgroundTaskCoordinator):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.crash_once = True
        super().__init__(*args, **kwargs)

    def _after_lease_persisted(self, lease) -> None:
        if self.crash_once:
            self.crash_once = False
            raise SystemExit("simulated crash after lease persistence")


class AgentBackgroundExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 18 background execution",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage18_background",
        )
        self.clock = _MutableClock()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    def _coordinator(
        self,
        *,
        crash_trace: bool = False,
        coordinator_type=AgentBackgroundTaskCoordinator,
    ) -> AgentBackgroundTaskCoordinator:
        harness = AgentHarness(self.store, self._registry())
        if crash_trace:
            harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        return coordinator_type(harness, clock=self.clock)

    def _scene_plan(
        self,
        coordinator: AgentBackgroundTaskCoordinator,
        *,
        plan_id: str,
        scene_id: str,
    ):
        return coordinator.create_plan(
            project_id=self.project.project_id,
            goal=f"Create {scene_id} in background",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": scene_id, "title": scene_id},
                ),
            ),
            plan_id=plan_id,
        )

    def test_background_task_completes_through_existing_harness_and_survives_reopen(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_success",
            scene_id="scene_background_success",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_a",
            lease_seconds=10,
            heartbeat_seconds=0,
        )

        result = worker.run_once(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
        )
        self.assertIsNotNone(result)
        self.assertEqual(
            coordinator.state(self.project.project_id, state.plan.plan_id).tasks[0].status,
            AgentTaskStatus.SUCCEEDED,
        )
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(production.scene("scene_background_success").title, "scene_background_success")

        reopened = self._coordinator()
        reopened_state = reopened.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(reopened_state.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        self.assertEqual(
            reopened.leases.get(
                self.project.project_id,
                state.plan.plan_id,
                "scene",
            ).outcome,
            "task_succeeded",
        )

    def test_two_workers_cannot_claim_the_same_task(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_exclusive",
            scene_id="scene_background_exclusive",
        )
        worker_a = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_a",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        worker_b = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_b",
            lease_seconds=10,
            heartbeat_seconds=0,
        )

        claim = worker_a.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        with self.assertRaises(AgentBackgroundLeaseConflict):
            worker_b.claim(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        worker_a.execute(claim)
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(production.scene("scene_background_exclusive").scene_id, "scene_background_exclusive")

    def test_durable_lease_never_persists_or_repr_exposes_bearer_token(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_token_privacy",
            scene_id="scene_token_privacy",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_token_privacy",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )

        lease = coordinator.leases.get(self.project.project_id, state.plan.plan_id, "scene")
        self.assertIsNotNone(lease)
        payload = lease.to_dict()
        self.assertNotIn("lease_token", payload)
        serialized_payload = json.dumps(payload, sort_keys=True)
        self.assertNotIn(claim.lease_token, serialized_payload)
        self.assertNotIn(claim.lease_token, repr(claim))

        lease_path = coordinator.leases.records.path(self.project.project_id, lease.record_id)
        durable_text = lease_path.read_text(encoding="utf-8")
        self.assertNotIn('"lease_token"', durable_text)
        self.assertNotIn(claim.lease_token, durable_text)

        worker.execute(claim)

    def test_forged_policy_digest_cannot_rebind_background_authority(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_policy_forgery",
            scene_id="scene_policy_forgery_must_not_exist",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_policy_forgery",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        forged = replace(claim, policy_digest="0" * 64)

        with self.assertRaises(AgentBackgroundLeaseStale):
            worker.execute(forged)

        production = ProductionSemanticService(self.store).state(self.project.project_id)
        with self.assertRaises(Exception):
            production.scene("scene_policy_forgery_must_not_exist")

        worker.execute(claim)

    def test_heartbeat_extends_live_lease_without_replacing_claim_authority(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_heartbeat",
            scene_id="scene_background_heartbeat",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_heartbeat",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        before = coordinator.leases.get(self.project.project_id, state.plan.plan_id, "scene")
        self.assertIsNotNone(before)

        self.clock.advance(5)
        extended = coordinator.heartbeat_claim(claim, lease_seconds=10)
        self.assertEqual(extended.generation, before.generation)
        self.assertEqual(extended.token_digest, before.token_digest)
        self.assertNotEqual(extended.heartbeat_at, before.heartbeat_at)
        self.assertNotEqual(extended.expires_at, before.expires_at)

        self.clock.advance(6)
        live_state = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(live_state.tasks[0].status, AgentTaskStatus.RUNNING)

        worker.execute(claim)
        final = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(final.tasks[0].status, AgentTaskStatus.SUCCEEDED)

    def test_context_change_after_claim_refuses_background_commit(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_context_stale",
            scene_id="scene_stale_context_must_not_exist",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_context_stale",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )

        coordinator.harness.execute(
            project_id=self.project.project_id,
            action_id="production.create_scene",
            inputs={
                "scene_id": "scene_external_context_change",
                "title": "External context change",
            },
        )

        with self.assertRaises(AgentBackgroundContextStale):
            worker.execute(claim)

        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(
            production.scene("scene_external_context_change").title,
            "External context change",
        )
        with self.assertRaises(Exception):
            production.scene("scene_stale_context_must_not_exist")

        self.clock.advance(11)
        recovered = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(recovered.tasks[0].status, AgentTaskStatus.FAILED)

    def test_expired_worker_cannot_authorize_canonical_mutation(self) -> None:
        coordinator = self._coordinator()
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_expired",
            scene_id="scene_must_not_exist",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_expired",
            lease_seconds=2,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        self.clock.advance(3)

        with self.assertRaises(AgentBackgroundLeaseStale):
            worker.execute(claim)

        recovered = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(recovered.tasks[0].status, AgentTaskStatus.FAILED)
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        with self.assertRaises(Exception):
            production.scene("scene_must_not_exist")

    def test_expired_pre_dispatch_claim_can_be_reclaimed_with_bounded_history(self) -> None:
        coordinator = self._coordinator(coordinator_type=_CrashAfterLeaseCoordinator)
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_claim_crash",
            scene_id="scene_after_claim_retry",
        )
        worker_a = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_claim_crash",
            lease_seconds=2,
            heartbeat_seconds=0,
        )
        with self.assertRaises(SystemExit):
            worker_a.claim(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        durable = coordinator.tasks.get(self.project.project_id, state.plan.plan_id, "scene")
        self.assertEqual(durable.status, AgentTaskStatus.READY)
        with self.assertRaises(AgentBackgroundLeaseConflict):
            AgentBackgroundWorker(
                coordinator,
                worker_id="worker_too_early",
                lease_seconds=2,
                heartbeat_seconds=0,
            ).claim(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        self.clock.advance(3)
        worker_b = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_retry",
            lease_seconds=2,
            heartbeat_seconds=0,
        )
        claim = worker_b.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        self.assertEqual(claim.generation, 2)
        lease = coordinator.leases.get(self.project.project_id, state.plan.plan_id, "scene")
        self.assertEqual(len(lease.history), 1)
        self.assertEqual(lease.history[0]["outcome"], "lease_expired_before_dispatch")
        worker_b.execute(claim)
        self.assertEqual(
            coordinator.state(self.project.project_id, state.plan.plan_id).tasks[0].status,
            AgentTaskStatus.SUCCEEDED,
        )

    def test_post_commit_pre_trace_crash_recovers_success_without_replay(self) -> None:
        coordinator = self._coordinator(crash_trace=True)
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_background_commit_crash",
            scene_id="scene_committed_once",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_commit_crash",
            lease_seconds=2,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        with self.assertRaises(SystemExit):
            worker.execute(claim)

        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(production.scene("scene_committed_once").scene_id, "scene_committed_once")
        self.assertEqual(
            coordinator.tasks.get(self.project.project_id, state.plan.plan_id, "scene").status,
            AgentTaskStatus.RUNNING,
        )

        self.clock.advance(3)
        reopened = self._coordinator()
        reopened_state = reopened.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(reopened_state.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(
            [scene.scene_id for scene in production.scenes].count("scene_committed_once"),
            1,
        )

    def test_cancellation_prevents_dependent_background_work(self) -> None:
        coordinator = self._coordinator()
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Cancel the dependency chain",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_cancelled", "title": "Cancelled"},
                ),
                AgentPlanStepProposal(
                    step_id="shot",
                    action_id="production.create_shot",
                    inputs={
                        "shot_id": "shot_cancelled",
                        "scene_id": "scene_cancelled",
                        "intent": "Must never run",
                    },
                    dependencies=("scene",),
                ),
            ),
            plan_id="agent_plan_background_cancelled",
        )
        coordinator.cancel_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_cancelled",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        self.assertIsNone(
            worker.run_once(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
            )
        )
        final = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(
            tuple(record.status for record in final.tasks),
            (AgentTaskStatus.CANCELLED, AgentTaskStatus.CANCELLED),
        )
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        with self.assertRaises(Exception):
            production.scene("scene_cancelled")


if __name__ == "__main__":
    unittest.main()
