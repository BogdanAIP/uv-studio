from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class StudioTimelineApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

        created = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Studio Timeline", "direction_id": "free_project"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        created_payload = created.json()
        self.assertEqual(created_payload["recipe_id"], "studio_v2")
        self.assertEqual(
            created_payload["extensions"]["studio"],
            {
                "schema_version": 2,
                "product_model": "production_directions",
                "direction_id": "free_project",
            },
        )
        self.project_id = created_payload["project_id"]

        media_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_api.mp4",
            allowed_roots=("sources",),
        )
        media_path.write_bytes(b"video")
        self.reference = ProjectReference(
            id="src_api",
            kind="video",
            path="sources/src_api.mp4",
            metadata={
                "duration_us": 12_000_000,
                "width": 1280,
                "height": 720,
                "avg_frame_rate": "30/1",
            },
        )
        self.store.update_project(self.project_id, sources=(self.reference,))

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _command(self, payload: dict) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/timeline/commands",
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_production_directions_are_product_composition_not_recipe_identity(self) -> None:
        response = self.client.get("/api/uv/projects/studio/directions")
        self.assertEqual(response.status_code, 200, response.text)
        directions = response.json()
        ids = [item["direction_id"] for item in directions]
        self.assertEqual(
            ids,
            [
                "micro_drama",
                "commercial",
                "music_video",
                "narrated_video",
                "dub_battle",
                "free_project",
            ],
        )
        self.assertIn("scenes", directions[0]["workspace_sections"])
        self.assertIn("cast", directions[4]["workspace_sections"])

        unknown = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Unknown", "direction_id": "not_a_direction"},
        )
        self.assertEqual(unknown.status_code, 422, unknown.text)
        self.assertIn("unknown production direction", unknown.json()["detail"])

    def test_commands_create_reload_and_mutate_canonical_timeline(self) -> None:
        empty = self.client.get(f"/api/uv/projects/{self.project_id}/studio/timeline")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json(), {"schema_version": 1, "timeline_id": "main", "tracks": []})

        created = self._command(
            {"command": "create_track", "kind": "video", "track_id": "trk_api"}
        )
        self.assertEqual(created["track_id"], "trk_api")
        self.assertEqual(created["timeline"]["tracks"][0]["title"], "Video 1")

        added = self._command(
            {
                "command": "add_clip",
                "track_id": "trk_api",
                "reference_id": self.reference.id,
                "timeline_start_us": 0,
                "source_start_us": 1_000_000,
                "duration_us": 4_000_000,
                "clip_id": "clip_api",
            }
        )
        self.assertEqual(added["clip_id"], "clip_api")

        moved = self._command(
            {"command": "move_clip", "clip_id": "clip_api", "timeline_start_us": 2_000_000}
        )
        clip = moved["timeline"]["tracks"][0]["clips"][0]
        self.assertEqual(clip["timeline_start_us"], 2_000_000)

        trimmed = self._command(
            {
                "command": "trim_clip",
                "clip_id": "clip_api",
                "source_start_us": 3_000_000,
                "duration_us": 2_000_000,
            }
        )
        clip = trimmed["timeline"]["tracks"][0]["clips"][0]
        self.assertEqual(clip["source_start_us"], 3_000_000)
        self.assertEqual(clip["duration_us"], 2_000_000)

        reloaded = self.client.get(f"/api/uv/projects/{self.project_id}/studio/timeline")
        self.assertEqual(reloaded.status_code, 200, reloaded.text)
        self.assertEqual(reloaded.json(), trimmed["timeline"])

        engine = self.client.get(f"/api/uv/projects/{self.project_id}/studio/timeline/engine")
        self.assertEqual(engine.status_code, 200, engine.text)
        engine_payload = engine.json()
        self.assertEqual(engine_payload["adapter_id"], "mlt")
        self.assertEqual(engine_payload["timeline_id"], "main")
        self.assertEqual(engine_payload["frame_rate"], "30/1")
        self.assertEqual(engine_payload["tracks"][0]["clips"][0]["clip_id"], "clip_api")
        self.assertNotIn(str(self.store.root.resolve()), repr(engine_payload))

        removed = self._command({"command": "remove_clip", "clip_id": "clip_api"})
        self.assertEqual(removed["timeline"]["tracks"][0]["clips"], [])

    def test_invalid_timeline_mutation_returns_422_without_partial_write(self) -> None:
        self._command({"command": "create_track", "kind": "video", "track_id": "trk_api"})
        self._command(
            {
                "command": "add_clip",
                "track_id": "trk_api",
                "reference_id": self.reference.id,
                "timeline_start_us": 0,
                "duration_us": 5_000_000,
                "clip_id": "clip_a",
            }
        )
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/timeline/commands",
            json={
                "command": "add_clip",
                "track_id": "trk_api",
                "reference_id": self.reference.id,
                "timeline_start_us": 4_000_000,
                "duration_us": 2_000_000,
                "clip_id": "clip_overlap",
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("must not overlap", response.json()["detail"])

        state = self.client.get(f"/api/uv/projects/{self.project_id}/studio/timeline")
        self.assertEqual(state.status_code, 200, state.text)
        clips = state.json()["tracks"][0]["clips"]
        self.assertEqual([clip["clip_id"] for clip in clips], ["clip_a"])

    def test_registered_studio_export_streams_only_from_exports_root(self) -> None:
        export_path = self.store.resolve_project_file(
            self.project_id,
            "exports/art_studio.mp4",
            allowed_roots=("exports",),
        )
        export_path.write_bytes(b"studio-export-bytes")
        project = self.store.load_project(self.project_id)
        artifact = ProjectReference(
            id="art_studio",
            kind="video",
            path="exports/art_studio.mp4",
            metadata={"role": "studio-export", "content_type": "video/mp4"},
        )
        self.store.update_project(
            self.project_id,
            artifacts=(*project.artifacts, artifact),
        )

        response = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/exports/{artifact.id}/media"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, b"studio-export-bytes")
        self.assertTrue(response.headers["content-type"].startswith("video/mp4"))

        legacy_path = self.store.resolve_project_file(
            self.project_id,
            "artifacts/art_other.mp4",
            allowed_roots=("artifacts",),
        )
        legacy_path.write_bytes(b"other")
        project = self.store.load_project(self.project_id)
        other = ProjectReference(
            id="art_other",
            kind="video",
            path="artifacts/art_other.mp4",
            metadata={"role": "other"},
        )
        self.store.update_project(self.project_id, artifacts=(*project.artifacts, other))
        rejected = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/exports/{other.id}/media"
        )
        self.assertEqual(rejected.status_code, 404, rejected.text)


if __name__ == "__main__":
    unittest.main()
