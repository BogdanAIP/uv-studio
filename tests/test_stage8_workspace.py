from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.archive import export_project, import_project
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.stage8_workspace import (
    Stage8WorkspaceError,
    get_stage8_workspace,
    save_stage8_workspace,
)
from uv_studio.projects.store import ProjectStore


class Stage8WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root / "projects")
        self.project = self.store.create_project(title="Story workspace", recipe_id="story_video")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _source(self, source_id: str, kind: str, filename: str, body: bytes) -> ProjectReference:
        project_dir = self.store.project_directory(self.project.project_id)
        path = project_dir / "sources" / filename
        path.write_bytes(body)
        reference = ProjectReference(
            id=source_id,
            kind=kind,
            path=f"sources/{filename}",
            metadata={
                "original_name": filename,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        current = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            sources=(*current.sources, reference),
        )
        return reference

    def test_workspace_is_revisioned_and_exact_source_bound(self) -> None:
        image = self._source("src_image", "image", "scene.png", b"scene-image")
        audio = self._source("src_audio", "audio", "score.wav", b"story-audio")
        workspace = save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="История о возвращении домой",
            script="Сцена 1. Герой входит в дом.",
            source_ids=[image.id, audio.id],
        )
        self.assertEqual(workspace.recipe_id, "story_video")
        self.assertEqual([item.role for item in workspace.sources], ["story_image", "story_audio"])
        self.assertEqual(len(workspace.revision_sha256), 64)

        reopened = get_stage8_workspace(self.store, self.project.project_id)
        self.assertEqual(reopened, workspace)

        image_path = self.store.resolve_project_file(
            self.project.project_id,
            image.path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        image_path.write_bytes(b"substituted-image")
        with self.assertRaises(Stage8WorkspaceError):
            get_stage8_workspace(self.store, self.project.project_id)

    def test_story_and_commercial_require_brief_while_free_project_does_not(self) -> None:
        with self.assertRaises(Stage8WorkspaceError):
            save_stage8_workspace(
                self.store,
                self.project.project_id,
                brief="",
                script="",
                source_ids=[],
            )

        free = self.store.create_project(title="Free workspace", recipe_id="free_project")
        workspace = save_stage8_workspace(
            self.store,
            free.project_id,
            brief="",
            script="",
            source_ids=[],
        )
        self.assertEqual(workspace.brief, "")
        self.assertEqual(workspace.sources, ())

    def test_workspace_survives_project_archive_round_trip(self) -> None:
        video = self._source("src_video", "video", "scene.mp4", b"story-video")
        saved = save_stage8_workspace(
            self.store,
            self.project.project_id,
            brief="Архивируемая история",
            script="Финальный сценарий",
            source_ids=[video.id],
        )
        archive = self.root / "story.uvproj.zip"
        export_project(self.store, self.project.project_id, archive)

        with tempfile.TemporaryDirectory() as target_tmp:
            target = ProjectStore(Path(target_tmp) / "projects")
            imported = import_project(target, archive)
            self.assertEqual(imported.project_id, self.project.project_id)
            reopened = get_stage8_workspace(target, imported.project_id)
            self.assertIsNotNone(reopened)
            assert reopened is not None
            self.assertEqual(reopened.revision_sha256, saved.revision_sha256)
            self.assertEqual(reopened.sources[0].source_id, video.id)
            self.assertEqual(reopened.sources[0].sha256, hashlib.sha256(b"story-video").hexdigest())


if __name__ == "__main__":
    unittest.main()
