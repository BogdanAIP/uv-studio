from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentContextSnapshot,
    AgentHarness,
    AgentPortableStateError,
    AgentTraceStatus,
    AgentUnknownAction,
)
from uv_studio.agent.models import portable_json
from uv_studio.capabilities.authorization import ExecutionConsentRequired
from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityEffects,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import (
    GenerationContract,
    ModelDefinition,
    ModelRegistry,
)
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.production.semantics import ProductionSemanticError
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.timeline import TimelineClip, TimelineDocument, TimelineStore, TimelineTrack


class AgentHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Agent harness",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            settings={"api_key": "SHOULD_NOT_LEAK", "workspace_hint": "portable"},
            project_id="prj_agent_harness",
        )
        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_1",
            title="Scene",
        )
        self.production.create_shot(
            self.project.project_id,
            shot_id="shot_1",
            scene_id="scene_1",
            intent="Bounded target",
        )
        self.registry = self._model_registry(
            locality=LocalityClass.LOCAL,
            cost=CostClass.FREE,
        )
        self.harness = AgentHarness(self.store, self.registry)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _model_registry(
        *,
        locality: LocalityClass,
        cost: CostClass,
        availability: OfferAvailability = OfferAvailability.AVAILABLE,
    ) -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Agent harness test generation capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
            effects=CapabilityEffects(
                mutates_project=True,
                generates_media=True,
                long_running=True,
                reversible=False,
                cost_bearing=cost is not CostClass.FREE,
            ),
        )
        adapter = AdapterDefinition(
            "agent_test_generator",
            "Agent test generator",
            "Bounded test transport.",
            AdapterKind.LOCAL if locality is LocalityClass.LOCAL else AdapterKind.RUNTIME,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="agent_test_generator.image_generate",
                capability_id="image.generate",
                adapter_id="agent_test_generator",
                title="Agent test image generator",
                availability=availability,
                reason=(
                    "Available inside the bounded Agent Harness test."
                    if availability is OfferAvailability.AVAILABLE
                    else "Provider configuration is required."
                ),
                locality=locality,
                cost_class=cost,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.agent_test",
                    title="UV Agent Test Image",
                    description="Test named model for Agent Harness policy projection.",
                    capability_id="image.generate",
                    offer_id="agent_test_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def test_context_is_deterministic_bounded_and_does_not_copy_settings(self) -> None:
        first = self.harness.context.build(
            self.project.project_id,
            shot_id="shot_1",
        )
        second = self.harness.context.build(
            self.project.project_id,
            shot_id="shot_1",
        )

        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.target_kind, "shot")
        self.assertEqual(first.target_id, "shot_1")
        self.assertEqual(first.content["project"]["direction_id"], "micro_drama")
        self.assertEqual(first.content["production"]["target_shot"]["shot_id"], "shot_1")
        encoded = json.dumps(first.to_dict(), ensure_ascii=False, sort_keys=True)
        self.assertNotIn("SHOULD_NOT_LEAK", encoded)
        self.assertNotIn('"settings"', encoded)
        self.assertNotIn('"extensions"', encoded)

    def test_context_bounds_nested_timeline_identity_collections(self) -> None:
        asset_path = self.store.resolve_project_file(
            self.project.project_id,
            "assets/bounded.mp4",
            allowed_roots=("assets",),
        )
        asset_path.write_bytes(b"bounded")
        reference = ProjectReference(
            id="asset_bounded",
            kind="video",
            path="assets/bounded.mp4",
            metadata={"duration_us": 1_000_000},
        )
        self.store.update_project(self.project.project_id, artifacts=(reference,))

        clips = tuple(
            TimelineClip(
                clip_id=f"clip_bounded_{index}",
                reference_id=reference.id,
                timeline_start_us=index * 1_000,
                source_start_us=0,
                duration_us=1_000,
            )
            for index in range(110)
        )
        tracks = (
            TimelineTrack(
                track_id="trk_bounded_0",
                kind="video",
                title="Bounded 0",
                clips=clips,
            ),
            *tuple(
                TimelineTrack(
                    track_id=f"trk_bounded_{index}",
                    kind="video",
                    title=f"Bounded {index}",
                )
                for index in range(1, 60)
            ),
        )
        TimelineStore(self.store).save(
            self.project.project_id,
            TimelineDocument(tracks=tracks),
        )

        snapshot = self.harness.context.build(self.project.project_id, shot_id="shot_1")
        timeline = snapshot.content["timeline"]
        self.assertEqual(timeline["track_count"], 60)
        self.assertEqual(len(timeline["tracks"]), 50)
        self.assertEqual(timeline["tracks_omitted"], 10)
        self.assertEqual(len(timeline["tracks"][0]["clip_ids"]), 100)
        self.assertEqual(timeline["tracks"][0]["clip_ids_omitted"], 10)

    def test_catalog_is_deterministic_and_unknown_actions_fail_closed(self) -> None:
        actions = self.harness.catalog.list()
        ids = tuple(item.action_id for item in actions)
        self.assertEqual(ids, tuple(sorted(ids)))
        self.assertIn("production.create_shot", ids)
        self.assertIn("timeline.create_track", ids)
        self.assertIn("generation.submit", ids)
        self.assertNotIn("project.write_file", ids)
        self.assertTrue(
            all(
                item.authority.startswith(
                    (
                        "uv_studio.production.commands.",
                        "uv_studio.editor.timeline_commands.",
                        "uv_studio.generation.service.",
                    )
                )
                for item in actions
            )
        )
        with self.assertRaises(AgentUnknownAction):
            self.harness.catalog.get("project.write_file")

    def test_bounded_execution_uses_existing_semantic_authority_and_reopens_trace(self) -> None:
        result = self.harness.execute(
            project_id=self.project.project_id,
            action_id="production.create_shot",
            target_shot_id="shot_1",
            inputs={
                "shot_id": "shot_2",
                "scene_id": "scene_1",
                "intent": "Created through bounded Agent Harness",
            },
        )

        self.assertTrue(result.transaction_id.startswith("tx_"))
        shared = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(shared.shot("shot_2").scene_id, "scene_1")

        traces = self.harness.traces.list(self.project.project_id)
        self.assertEqual(len(traces), 1)
        trace = traces[0]
        self.assertEqual(trace.status, AgentTraceStatus.SUCCEEDED)
        self.assertEqual(trace.action_id, "production.create_shot")
        self.assertEqual(trace.result_references["transaction_id"], result.transaction_id)
        self.assertIn("shot_1", trace.canonical_references)
        self.assertIn("shot_2", trace.canonical_references)
        self.assertIn("scene_1", trace.canonical_references)
        self.assertNotIn("Created through bounded Agent Harness", json.dumps(trace.to_dict()))

        reopened = AgentHarness(
            ProjectStore(self.store.root),
            self.registry,
        ).traces.list(self.project.project_id)
        self.assertEqual(reopened, traces)

    def test_failed_existing_command_leaves_failure_trace_without_false_success(self) -> None:
        with self.assertRaises(ProductionSemanticError):
            self.harness.execute(
                project_id=self.project.project_id,
                action_id="production.create_shot",
                target_shot_id="shot_1",
                inputs={
                    "shot_id": "shot_missing_parent",
                    "scene_id": "scene_missing",
                    "intent": "Must fail",
                },
            )

        with self.assertRaises(ProductionSemanticError):
            self.production.state(self.project.project_id).shot("shot_missing_parent")
        trace = self.harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(trace.status, AgentTraceStatus.FAILED)
        self.assertEqual(trace.action_id, "production.create_shot")
        self.assertEqual(trace.result_references, {})
        self.assertEqual(trace.error_type, "ProductionSemanticError")

    def test_context_and_input_validation_failures_are_traced_without_rejected_values(self) -> None:
        with self.assertRaises(ProductionSemanticError):
            self.harness.execute(
                project_id=self.project.project_id,
                action_id="production.create_scene",
                target_shot_id="shot_missing_context",
                inputs={"scene_id": "scene_never_created", "title": "Never created"},
            )
        context_failure = self.harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(context_failure.status, AgentTraceStatus.FAILED)
        self.assertEqual(context_failure.action_id, "production.create_scene")
        self.assertEqual(context_failure.error_type, "ProductionSemanticError")
        self.assertIn(self.project.project_id, context_failure.canonical_references)

        rejected_path = r"C:\Users\agent\private\prompt.txt"
        with self.assertRaises(AgentPortableStateError):
            self.harness.execute(
                project_id=self.project.project_id,
                action_id="production.create_scene",
                target_shot_id="shot_1",
                inputs={"scene_id": "scene_rejected", "title": rejected_path},
            )
        input_failure = self.harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(input_failure.status, AgentTraceStatus.FAILED)
        self.assertEqual(input_failure.error_type, "AgentPortableStateError")
        self.assertNotIn(rejected_path, json.dumps(input_failure.to_dict()))
        with self.assertRaises(ProductionSemanticError):
            self.production.state(self.project.project_id).scene("scene_rejected")

    def test_unknown_action_is_traced_and_cannot_become_direct_project_write(self) -> None:
        with self.assertRaises(AgentUnknownAction):
            self.harness.execute(
                project_id=self.project.project_id,
                action_id="project.write_file",
                inputs={"relative_path": "notes/agent.txt", "content": "blocked"},
            )

        trace = self.harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(trace.status, AgentTraceStatus.FAILED)
        self.assertEqual(trace.action_id, "project.write_file")
        self.assertEqual(trace.error_type, "AgentUnknownAction")
        self.assertFalse(
            (self.store.project_directory(self.project.project_id) / "notes" / "agent.txt").exists()
        )

    def test_trace_contract_rejects_tokens_and_absolute_host_paths(self) -> None:
        with self.assertRaises(AgentPortableStateError):
            portable_json(
                {"authorization_token": "secret-token"},
                field_name="trace payload",
            )
        with self.assertRaises(AgentPortableStateError):
            AgentContextSnapshot(
                project_id=self.project.project_id,
                target_kind="project",
                target_id=self.project.project_id,
                content={"leak": r"C:\Users\agent\secret.txt"},
            )

    def test_unavailable_model_fails_before_job_creation_and_records_policy(self) -> None:
        registry = self._model_registry(
            locality=LocalityClass.REMOTE,
            cost=CostClass.POTENTIALLY_PAID,
            availability=OfferAvailability.CONFIGURATION_REQUIRED,
        )
        harness = AgentHarness(self.store, registry)
        with self.assertRaisesRegex(RuntimeError, "Provider configuration is required"):
            harness.execute(
                project_id=self.project.project_id,
                action_id="generation.submit",
                target_shot_id="shot_1",
                inputs={
                    "shot_id": "shot_1",
                    "model_id": "uv.image.agent_test",
                    "inputs": {"prompt": "portrait"},
                    "contract": GenerationContract().to_dict(),
                    "idempotency_key": "idem_unavailable",
                    "authorization_token": None,
                },
            )

        self.assertEqual(harness.jobs.list(self.project.project_id), ())
        trace = harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(trace.status, AgentTraceStatus.FAILED)
        self.assertFalse(trace.policy.available)
        self.assertTrue(trace.policy.authorization_required)
        self.assertTrue(trace.policy.effects.generates_media)

    def test_remote_paid_generation_preserves_exact_d017_one_shot_authorization(self) -> None:
        registry = self._model_registry(
            locality=LocalityClass.REMOTE,
            cost=CostClass.POTENTIALLY_PAID,
        )
        harness = AgentHarness(self.store, registry)
        inputs = {
            "shot_id": "shot_1",
            "model_id": "uv.image.agent_test",
            "inputs": {"prompt": "portrait"},
            "contract": GenerationContract().to_dict(),
            "idempotency_key": "idem_remote_agent",
            "authorization_token": None,
        }

        with self.assertRaises(ExecutionConsentRequired):
            harness.execute(
                project_id=self.project.project_id,
                action_id="generation.submit",
                target_shot_id="shot_1",
                inputs=inputs,
            )
        self.assertEqual(harness.jobs.list(self.project.project_id), ())
        failed = harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(failed.status, AgentTraceStatus.FAILED)
        self.assertTrue(failed.policy.authorization_required)
        self.assertNotIn("authorization_token", json.dumps(failed.to_dict()))

        prepared = harness.generation.prepare(
            project_id=self.project.project_id,
            shot_id="shot_1",
            model_id="uv.image.agent_test",
            inputs={"prompt": "portrait"},
            contract=GenerationContract(),
        )
        token, _expires = harness.authorizations.issue(
            prepared.execution,
            acknowledgements=set(prepared.execution.consent_required),
        )
        authorized_inputs = dict(inputs)
        authorized_inputs["authorization_token"] = token
        submitted = harness.execute(
            project_id=self.project.project_id,
            action_id="generation.submit",
            target_shot_id="shot_1",
            inputs=authorized_inputs,
        )

        self.assertFalse(submitted.reused)
        self.assertEqual(len(harness.jobs.list(self.project.project_id)), 1)
        succeeded = harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(succeeded.status, AgentTraceStatus.SUCCEEDED)
        self.assertEqual(succeeded.result_references["job_id"], submitted.job.job_id)
        encoded = json.dumps(succeeded.to_dict())
        self.assertNotIn(token, encoded)


if __name__ == "__main__":
    unittest.main()
