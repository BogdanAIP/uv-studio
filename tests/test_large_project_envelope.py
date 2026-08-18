from __future__ import annotations

import json
import tempfile
import tracemalloc
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class LargeProjectMetadataEnvelopeTests(unittest.TestCase):
    def test_thousands_of_references_load_and_serialize_in_bounded_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Large metadata envelope")
            sources = tuple(
                ProjectReference(
                    id=f"src_{index:04d}",
                    kind="video",
                    path=f"sources/source-{index:04d}.mp4",
                    metadata={"ordinal": index, "duration_us": 120_000_000},
                )
                for index in range(2_000)
            )
            artifacts = tuple(
                ProjectReference(
                    id=f"art_{index:04d}",
                    kind="video",
                    path=f"artifacts/render-{index:04d}.mkv",
                    metadata={"ordinal": index, "lifecycle": "render"},
                )
                for index in range(2_000)
            )
            store.update_project(
                project.project_id,
                sources=sources,
                artifacts=artifacts,
            )

            tracemalloc.start()
            try:
                loaded = store.load_project(project.project_id)
                encoded = json.dumps(loaded.to_dict(), ensure_ascii=False)
                _, peak_bytes = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()

            self.assertEqual(len(loaded.sources), 2_000)
            self.assertEqual(len(loaded.artifacts), 2_000)
            self.assertLess(len(encoded.encode("utf-8")), 4 * 1024**2)
            self.assertLess(
                peak_bytes,
                128 * 1024**2,
                "loading and serializing 4,000 project references should remain metadata-bounded",
            )


if __name__ == "__main__":
    unittest.main()
