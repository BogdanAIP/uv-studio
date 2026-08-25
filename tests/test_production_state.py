from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.production_state import (
    ProductionDocumentNotFound,
    ProductionDocumentStore,
    ProductionStateError,
)
from uv_studio.projects.store import ProjectStore


class ProductionDocumentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Production",
            recipe_id="general_video",
            project_id="prj_production_root",
        )
        self.production = ProductionDocumentStore(self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_project_layout_reserves_bounded_production_root(self) -> None:
        production_root = self.store.project_directory(self.project.project_id) / "production"
        self.assertTrue(production_root.is_dir())
        path = self.store.resolve_project_file(
            self.project.project_id,
            "production/shared.json",
            allowed_roots=("production",),
        )
        self.assertEqual(path.parent, production_root)

    def test_versioned_production_document_round_trip(self) -> None:
        payload = {
            "schema_version": 1,
            "document_kind": "shared-production-placeholder",
            "entities": [],
        }
        saved = self.production.save(self.project.project_id, "shared", payload)
        self.assertEqual(saved, payload)
        self.assertEqual(self.production.load(self.project.project_id, "shared"), payload)

    def test_missing_and_nonportable_documents_fail_closed(self) -> None:
        with self.assertRaises(ProductionDocumentNotFound):
            self.production.load(self.project.project_id, "missing")
        with self.assertRaises(ProductionStateError):
            self.production.save(
                self.project.project_id,
                "bad",
                {"schema_version": 1, "value": float("nan")},
            )
        with self.assertRaises(ProductionStateError):
            self.production.save(
                self.project.project_id,
                "unversioned",
                {"entities": []},
            )


if __name__ == "__main__":
    unittest.main()
