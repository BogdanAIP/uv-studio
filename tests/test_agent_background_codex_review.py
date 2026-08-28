from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentBackgroundContextStale,
    AgentBackgroundTaskCoordinator,
    AgentBackgroundWorker,
    AgentHarness,
    AgentPlanStepProposal,
)
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.editor.timeline_commands import (
    AddClipCommand,
    CreateTrackCommand,
    MoveClipCommand,
    TimelineCommandService,
)
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.generation.service import GenerationService
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.timeline import TimelineStore


class _PausingProductionService(ProductionSemanticService):
    def __init__(self, *args, entered: threading.Event, release: threading.Event, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.entered = entered
        self.release = release

    def _commit_production(self, *args, **kwargs):
        self.entered.set()
        if not self.release.wait(timeout=3.0):
            raise AssertionError("production concurrency test was not released")
        return super()._commit_production(*args, **kwargs)


class _PausingTimelineService(TimelineCommandService):
    def __init__(self, *args, entered: threading.Event, release: threading.Event, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.entered = entered
        self.release = release

    def _commit_timeline(self, *args, **kwargs):
        self.entered.set()
        if not self.release.wait(timeout=3.0):
            raise AssertionError("timeline concurrency test was not released")
        return super()._commit_timeline(*args, **kwargs)


class _CountingAuthorizationStore(OneShotAuthorizationStore):
    def __init__(self) -> None:
        super().__init__()
        self.consume_calls = 0
        self._count_lock = threading.Lock()

    def consume(self, *args, **kwargs):
        with self._count_lock:
            self.consume_calls += 1
        return super().consume(*args, **kwargs)


class _PausingGenerationService(GenerationService):
    def __init__(
        self,
        *args,
        entered: threading.Event | None = None,
        release: threading.Event | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.entered = entered
        self.release = release

    def prepare(self, *args, **kwargs):
        if self.entered is not None:
            self.entered.set()
        if self.release is not None and not self.release.wait(timeout=3.0):
            raise AssertionError("generation concurrency test was not released")
        return super().prepare(*args, **kwargs)


class AgentBackgroundCodexReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.root)
        self.project = self.store.create_project(
            title="Stage 18 Codex P1 review",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage18_codex_review",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _generation_registry() -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Bounded generation race proof.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "codex_review_generator",
            "Codex review generator",
            "Test-only local generator.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="codex_review_generator.image_generate",
                capability_id="image.generate",
                adapter_id="codex_review_generator",
                title="Codex review image generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available in test.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.codex_review",
                    title="Codex Review Image",
                    description="Test-only named model.",
                    capability_id="image.generate",
                    offer_id="codex_review_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def test_production_read_modify_commit_is_serialized_across_store_runtimes(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        first = _PausingProductionService(
            ProjectStore(self.root),
            entered=entered,
            release=release,
        )
        second = ProductionSemanticService(ProjectStore(self.root))
        second_finished = threading.Event()
        errors: list[BaseException] = []

        def first_call() -> None:
            try:
                first.create_scene(
                    self.project.project_id,
                    scene_id="scene_first_runtime",
                    title="First runtime",
                )
            except BaseException as exc:  # pragma: no cover - parent assertion reports it
                errors.append(exc)

        def second_call() -> None:
            try:
                second.create_scene(
                    self.project.project_id,
                    scene_id="scene_second_runtime",
                    title="Second runtime",
                )
            except BaseException as exc:  # pragma: no cover - parent assertion reports it
                errors.append(exc)
            finally:
                second_finished.set()

        first_thread = threading.Thread(target=first_call, daemon=True)
        second_thread = threading.Thread(target=second_call, daemon=True)
        first_thread.start()
        self.assertTrue(entered.wait(timeout=2.0))
        second_thread.start()
        self.assertFalse(
            second_finished.wait(timeout=0.2),
            "second Production runtime entered read/modify/commit while first owned project fence",
        )

        release.set()
        first_thread.join(timeout=3.0)
        second_thread.join(timeout=3.0)
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(errors, [])

        scenes = ProductionSemanticService(ProjectStore(self.root)).state(
            self.project.project_id
        ).scenes
        self.assertEqual(
            {scene.scene_id for scene in scenes},
            {"scene_first_runtime", "scene_second_runtime"},
        )

    def test_timeline_read_modify_commit_is_serialized_across_store_runtimes(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        first = _PausingTimelineService(
            ProjectStore(self.root),
            entered=entered,
            release=release,
        )
        second = TimelineCommandService(ProjectStore(self.root))
        second_finished = threading.Event()
        errors: list[BaseException] = []

        def first_call() -> None:
            try:
                first.create_track(
                    self.project.project_id,
                    CreateTrackCommand(kind="video", track_id="trk_first_runtime"),
                )
            except BaseException as exc:  # pragma: no cover
                errors.append(exc)

        def second_call() -> None:
            try:
                second.create_track(
                    self.project.project_id,
                    CreateTrackCommand(kind="video", track_id="trk_second_runtime"),
                )
            except BaseException as exc:  # pragma: no cover
                errors.append(exc)
            finally:
                second_finished.set()

        first_thread = threading.Thread(target=first_call, daemon=True)
        second_thread = threading.Thread(target=second_call, daemon=True)
        first_thread.start()
        self.assertTrue(entered.wait(timeout=2.0))
        second_thread.start()
        self.assertFalse(
            second_finished.wait(timeout=0.2),
            "second Timeline runtime entered read/modify/commit while first owned project fence",
        )

        release.set()
        first_thread.join(timeout=3.0)
        second_thread.join(timeout=3.0)
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(errors, [])

        timeline = TimelineStore(ProjectStore(self.root)).load(self.project.project_id)
        self.assertEqual(
            {track.track_id for track in timeline.tracks},
            {"trk_first_runtime", "trk_second_runtime"},
        )

    def test_same_generation_key_is_one_atomic_reservation_across_runtimes(self) -> None:
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_generation_race",
            title="Generation race",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_generation_race",
            scene_id="scene_generation_race",
            intent="Prove one idempotent reservation",
        )
        registry = self._generation_registry()
        authorizations = _CountingAuthorizationStore()
        first_entered = threading.Event()
        release_first = threading.Event()
        second_entered = threading.Event()
        first = _PausingGenerationService(
            ProjectStore(self.root),
            registry,
            authorizations,
            entered=first_entered,
            release=release_first,
        )
        second = _PausingGenerationService(
            ProjectStore(self.root),
            registry,
            authorizations,
            entered=second_entered,
        )
        contract = GenerationContract(
            fixed_constraints=("identity",),
            editable_variables=("camera",),
            forbidden_changes=("subject",),
        )
        kwargs = {
            "project_id": self.project.project_id,
            "shot_id": "shot_generation_race",
            "model_id": "uv.image.codex_review",
            "inputs": {"prompt": "portrait", "seed": 18},
            "contract": contract,
            "idempotency_key": "idem_cross_runtime_single_reservation",
            "authorization_token": None,
        }
        results = []
        errors: list[BaseException] = []

        def submit(service: GenerationService) -> None:
            try:
                results.append(service.submit(**kwargs))
            except BaseException as exc:  # pragma: no cover
                errors.append(exc)

        first_thread = threading.Thread(target=submit, args=(first,), daemon=True)
        second_thread = threading.Thread(target=submit, args=(second,), daemon=True)
        first_thread.start()
        self.assertTrue(first_entered.wait(timeout=2.0))
        second_thread.start()
        self.assertFalse(
            second_entered.wait(timeout=0.2),
            "second Generation runtime passed project fence before first reserved its Job",
        )

        release_first.set()
        first_thread.join(timeout=3.0)
        second_thread.join(timeout=3.0)
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].job.job_id, results[1].job.job_id)
        self.assertEqual(sorted(result.reused for result in results), [False, True])
        self.assertEqual(authorizations.consume_calls, 1)
        self.assertEqual(
            len(first.jobs.list(self.project.project_id)),
            1,
        )

    def test_timeline_timing_change_invalidates_exact_background_freshness(self) -> None:
        source_path = self.store.resolve_project_file(
            self.project.project_id,
            "sources/freshness.mp4",
            allowed_roots=("sources",),
        )
        source_path.write_bytes(b"freshness-video")
        reference = ProjectReference(
            id="src_freshness",
            kind="video",
            path="sources/freshness.mp4",
            metadata={"duration_us": 20_000_000, "width": 1920, "height": 1080},
        )
        self.store.update_project(self.project.project_id, sources=(reference,))
        timeline = TimelineCommandService(self.store)
        timeline.create_track(
            self.project.project_id,
            CreateTrackCommand(kind="video", track_id="trk_freshness"),
        )
        timeline.add_clip(
            self.project.project_id,
            AddClipCommand(
                track_id="trk_freshness",
                reference_id=reference.id,
                timeline_start_us=0,
                source_start_us=0,
                duration_us=4_000_000,
                clip_id="clip_freshness",
            ),
        )

        coordinator = AgentBackgroundTaskCoordinator(
            AgentHarness(self.store, ModelRegistry(CapabilityRegistry()))
        )
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Refuse stale background scene after Timeline timing edit",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_stale_timeline_must_not_exist",
                        "title": "Must not exist",
                    },
                ),
            ),
            plan_id="agent_plan_exact_timeline_freshness",
        )
        worker = AgentBackgroundWorker(
            coordinator,
            worker_id="worker_exact_timeline_freshness",
            lease_seconds=10,
            heartbeat_seconds=0,
        )
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )

        foreign_timeline = TimelineCommandService(ProjectStore(self.root))
        foreign_timeline.move_clip(
            self.project.project_id,
            MoveClipCommand(
                clip_id="clip_freshness",
                timeline_start_us=5_000_000,
            ),
        )

        # This is the exact Codex regression: the bounded observation context
        # intentionally omits clip timing, so it remains equal.  The separate
        # canonical byte digest must still fence the stale background claim.
        self.assertEqual(
            coordinator.harness.context.build(self.project.project_id).digest,
            claim.context_digest,
        )
        with self.assertRaises(AgentBackgroundContextStale):
            worker.execute(claim)

        moved = TimelineStore(ProjectStore(self.root)).load(self.project.project_id)
        self.assertEqual(
            moved.locate_clip("clip_freshness")[1].timeline_start_us,
            5_000_000,
        )
        with self.assertRaises(Exception):
            ProductionSemanticService(ProjectStore(self.root)).state(
                self.project.project_id
            ).scene("scene_stale_timeline_must_not_exist")


if __name__ == "__main__":
    unittest.main()
