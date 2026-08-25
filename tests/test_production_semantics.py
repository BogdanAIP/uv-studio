from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.production.commands import ProductionSemanticService
from uv_studio.production.micro_drama import (
    Character,
    Location,
    MicroDramaDocument,
    SceneContinuity,
    Story,
)
from uv_studio.production.semantics import ProductionSemanticError
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore
from uv_studio.projects.timeline import MAIN_TIMELINE_PATH, TimelineStore
from uv_studio.projects.transactions import ProjectUnitOfWork


class ProductionSemanticServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Micro drama",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_micro_drama",
        )
        self.take_1 = self._video_reference(
            self.project.project_id,
            reference_id="asset_take_1",
            filename="take_1.mp4",
            body=b"take-one",
            duration_us=4_000_000,
        )
        self.take_2 = self._video_reference(
            self.project.project_id,
            reference_id="asset_take_2",
            filename="take_2.mp4",
            body=b"take-two",
            duration_us=5_000_000,
        )
        self.store.update_project(
            self.project.project_id,
            artifacts=(self.take_1, self.take_2),
        )
        self.service = ProductionSemanticService(self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _video_reference(
        self,
        project_id: str,
        *,
        reference_id: str,
        filename: str,
        body: bytes,
        duration_us: int,
    ) -> ProjectReference:
        path = self.store.resolve_project_file(
            project_id,
            f"assets/{filename}",
            allowed_roots=("assets",),
        )
        path.write_bytes(body)
        return ProjectReference(
            id=reference_id,
            kind="video",
            path=f"assets/{filename}",
            metadata={"duration_us": duration_us},
        )

    def test_micro_drama_scene_shot_take_acceptance_is_one_atomic_timeline_projection(self) -> None:
        project_id = self.project.project_id

        self.service.create_scene(
            project_id,
            scene_id="scene_1",
            title="Встреча",
            summary="Героиня замечает незнакомца.",
        )
        self.service.create_shot(
            project_id,
            shot_id="shot_1",
            scene_id="scene_1",
            intent="Средний план, напряжённый первый взгляд.",
            reference_ids=(self.take_1.id,),
        )
        self.service.register_take(
            project_id,
            take_id="take_1",
            shot_id="shot_1",
            reference_id=self.take_1.id,
            label="Спокойный вариант",
        )
        self.service.register_take(
            project_id,
            take_id="take_2",
            shot_id="shot_1",
            reference_id=self.take_2.id,
            label="Более напряжённый вариант",
        )
        self.service.set_micro_drama_context(
            project_id,
            MicroDramaDocument(
                story=Story(
                    title="Случайная встреча",
                    premise="Одна встреча меняет решение героини.",
                ),
                characters=(
                    Character(
                        character_id="char_anna",
                        name="Анна",
                        description="Главная героиня",
                    ),
                ),
                locations=(
                    Location(
                        location_id="loc_cafe",
                        name="Кафе",
                        description="Вечерний интерьер",
                    ),
                ),
                scene_continuity=(
                    SceneContinuity(
                        scene_id="scene_1",
                        character_ids=("char_anna",),
                        location_id="loc_cafe",
                        canon_facts=("У Анны красный шарф",),
                    ),
                ),
            ),
        )

        accepted = self.service.accept_take(
            project_id,
            take_id="take_2",
            timeline_start_us=0,
            source_start_us=500_000,
            duration_us=3_000_000,
            track_id="trk_story",
            clip_id="clip_shot_1",
        )

        self.assertEqual(accepted.command, "production.accept_take")
        self.assertTrue(accepted.transaction_id.startswith("tx_"))
        shot = accepted.production.shot("shot_1")
        self.assertEqual(shot.take_ids, ("take_1", "take_2"))
        self.assertEqual(shot.accepted_take_id, "take_2")
        self.assertEqual(shot.timeline_clip_ids, ("clip_shot_1",))

        timeline = TimelineStore(self.store).load(project_id, validate_references=True)
        self.assertEqual(timeline.tracks[0].track_id, "trk_story")
        clip = timeline.tracks[0].clips[0]
        self.assertEqual(clip.reference_id, self.take_2.id)
        self.assertEqual(clip.source_start_us, 500_000)
        self.assertEqual(clip.duration_us, 3_000_000)

        project = self.store.load_project(project_id)
        accepted_reference = next(
            item for item in project.artifacts if item.id == self.take_2.id
        )
        self.assertEqual(accepted_reference.metadata["production_role"], "accepted_take")
        self.assertEqual(accepted_reference.metadata["shot_id"], "shot_1")
        self.assertEqual(accepted_reference.metadata["take_id"], "take_2")

        history = ProjectUnitOfWork(self.store).history(project_id)
        last = history.entries[-1]
        self.assertEqual(last.transaction_id, accepted.transaction_id)
        self.assertEqual(last.command, "production.accept_take")
        self.assertEqual(
            set(last.changed_paths),
            {PROJECT_FILENAME, "production/semantics.json", MAIN_TIMELINE_PATH},
        )

        ProjectUnitOfWork(self.store).undo(project_id)
        undone = self.service.state(project_id).shot("shot_1")
        self.assertIsNone(undone.accepted_take_id)
        self.assertEqual(undone.timeline_clip_ids, ())
        self.assertEqual(TimelineStore(self.store).load(project_id).tracks, ())
        project_after_undo = self.store.load_project(project_id)
        reference_after_undo = next(
            item for item in project_after_undo.artifacts if item.id == self.take_2.id
        )
        self.assertNotIn("production_role", reference_after_undo.metadata)

        ProjectUnitOfWork(self.store).redo(project_id)
        redone = self.service.state(project_id).shot("shot_1")
        self.assertEqual(redone.accepted_take_id, "take_2")
        self.assertEqual(
            TimelineStore(self.store).load(project_id).tracks[0].clips[0].clip_id,
            "clip_shot_1",
        )
        context = self.service.micro_drama_state(project_id)
        self.assertEqual(context.story.title, "Случайная встреча")
        self.assertEqual(context.scene_continuity[0].scene_id, "scene_1")

    def test_shared_scene_shot_take_contracts_are_reusable_by_commercial(self) -> None:
        project = self.store.create_project(
            title="Commercial",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("commercial"),
            project_id="prj_commercial",
        )
        reference = self._video_reference(
            project.project_id,
            reference_id="asset_product_take",
            filename="product_take.mp4",
            body=b"product",
            duration_us=2_000_000,
        )
        self.store.update_project(project.project_id, artifacts=(reference,))
        service = ProductionSemanticService(self.store)

        service.create_scene(
            project.project_id,
            scene_id="scene_product",
            title="Product reveal",
        )
        service.create_shot(
            project.project_id,
            shot_id="shot_product",
            scene_id="scene_product",
            intent="Macro product reveal.",
        )
        service.register_take(
            project.project_id,
            take_id="take_product",
            shot_id="shot_product",
            reference_id=reference.id,
        )

        state = service.state(project.project_id)
        self.assertEqual(state.scene("scene_product").shot_ids, ("shot_product",))
        self.assertEqual(state.shot("shot_product").take_ids, ("take_product",))
        with self.assertRaisesRegex(
            ProductionSemanticError,
            "requires direction_id='micro_drama'",
        ):
            service.micro_drama_state(project.project_id)

    def test_micro_drama_continuity_must_reference_shared_scene(self) -> None:
        with self.assertRaisesRegex(ProductionSemanticError, "unknown shared scene"):
            self.service.set_micro_drama_context(
                self.project.project_id,
                MicroDramaDocument(
                    scene_continuity=(
                        SceneContinuity(scene_id="scene_missing"),
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
