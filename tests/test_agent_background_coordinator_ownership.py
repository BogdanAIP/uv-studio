from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from uv_studio.agent import (
    AgentBackgroundError,
    AgentBackgroundTaskCoordinator,
    AgentBackgroundWorker,
    AgentHarness,
    AgentPlanStepProposal,
    AgentSubagentCoordinator,
    AgentSubagentTaskCoordinator,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
)
from uv_studio.agent import _background_impl as background_impl
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentBackgroundCoordinatorOwnershipTests(unittest.TestCase):
    def test_other_coordinators_cannot_replace_background_harness_fences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(
                title="Stage 18 coordinator ownership",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage18_coordinator_ownership",
            )
            harness = AgentHarness(store, ModelRegistry(CapabilityRegistry()))
            first = AgentBackgroundTaskCoordinator(harness)
            production_fence = harness.production.uow
            timeline_fence = harness.timeline.unit_of_work
            generation_fence = harness.generation

            with self.assertRaisesRegex(
                AgentBackgroundError,
                "already has an AgentBackgroundTaskCoordinator",
            ):
                AgentBackgroundTaskCoordinator(harness)

            for coordinator_type in (AgentTaskCoordinator, AgentSubagentTaskCoordinator):
                with self.subTest(coordinator_type=coordinator_type.__name__):
                    with self.assertRaisesRegex(
                        AgentTaskStateError,
                        "owned by an AgentBackgroundTaskCoordinator",
                    ):
                        coordinator_type(harness)
                    self.assertIs(harness.production.uow, production_fence)
                    self.assertIs(harness.timeline.unit_of_work, timeline_fence)
                    self.assertIs(harness.generation, generation_fence)

            with self.assertRaisesRegex(
                AgentTaskStateError,
                "owned by an AgentBackgroundTaskCoordinator",
            ):
                AgentSubagentCoordinator(harness, object())
            self.assertIs(harness.production.uow, production_fence)
            self.assertIs(harness.timeline.unit_of_work, timeline_fence)
            self.assertIs(harness.generation, generation_fence)

            state = first.create_plan(
                project_id=project.project_id,
                goal="Prove the original coordinator still owns the harness fences",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={
                            "scene_id": "scene_original_coordinator",
                            "title": "Original coordinator",
                        },
                    ),
                ),
                plan_id="agent_plan_coordinator_ownership",
            )
            worker = AgentBackgroundWorker(
                first,
                worker_id="worker_original_coordinator",
                lease_seconds=10,
                heartbeat_seconds=0,
            )
            worker.run_once(
                project_id=project.project_id,
                plan_id=state.plan.plan_id,
            )

            reopened = first.state(project.project_id, state.plan.plan_id)
            self.assertEqual(reopened.tasks[0].status, AgentTaskStatus.SUCCEEDED)
            production = ProductionSemanticService(store).state(project.project_id)
            self.assertEqual(
                production.scene("scene_original_coordinator").title,
                "Original coordinator",
            )

    def test_concurrent_construction_reserves_harness_before_fence_installation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            store.create_project(
                title="Stage 18 concurrent coordinator ownership",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage18_concurrent_coordinator_ownership",
            )
            harness = AgentHarness(store, ModelRegistry(CapabilityRegistry()))

            entered_base = threading.Event()
            release_base = threading.Event()
            base_calls_lock = threading.Lock()
            base_calls = 0
            winners: list[AgentBackgroundTaskCoordinator] = []
            errors: list[BaseException] = []
            original_init = background_impl.AgentBackgroundTaskCoordinator.__init__

            def blocked_base_init(self, *args, **kwargs) -> None:
                nonlocal base_calls
                with base_calls_lock:
                    base_calls += 1
                    entered_base.set()
                if not release_base.wait(timeout=3.0):
                    raise AssertionError("timed out waiting to release background base constructor")
                original_init(self, *args, **kwargs)

            def construct() -> None:
                try:
                    winners.append(AgentBackgroundTaskCoordinator(harness))
                except BaseException as exc:  # pragma: no cover - parent assertion reports it
                    errors.append(exc)

            with patch.object(
                background_impl.AgentBackgroundTaskCoordinator,
                "__init__",
                blocked_base_init,
            ):
                first_thread = threading.Thread(target=construct, daemon=True)
                second_thread = threading.Thread(target=construct, daemon=True)
                first_thread.start()
                self.assertTrue(entered_base.wait(timeout=2.0))

                # The first constructor is paused before installing any fence. The
                # public reservation must already make the second constructor fail.
                second_thread.start()
                second_thread.join(timeout=1.0)
                self.assertFalse(
                    second_thread.is_alive(),
                    "second background constructor entered base initialization before ownership was reserved",
                )

                release_base.set()
                first_thread.join(timeout=3.0)
                second_thread.join(timeout=3.0)

            self.assertFalse(first_thread.is_alive())
            self.assertFalse(second_thread.is_alive())
            self.assertEqual(base_calls, 1)
            self.assertEqual(len(winners), 1)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], AgentBackgroundError)
            self.assertIn(
                "already has an AgentBackgroundTaskCoordinator",
                str(errors[0]),
            )

            winner = winners[0]
            with self.assertRaisesRegex(
                AgentBackgroundError,
                "already has an AgentBackgroundTaskCoordinator",
            ):
                AgentBackgroundTaskCoordinator(harness)
            self.assertIsNotNone(winner)


if __name__ == "__main__":
    unittest.main()
