from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectStore, ProjectStoreError


class Stage19GenerationReferenceShapeTests(unittest.TestCase):
    @staticmethod
    def _metadata(*, continuation: str | None = None, lineage=..., job_id: str = "genjob_shape"):
        contract = {
            "schema_version": 1,
            "fixed_constraints": [],
            "editable_variables": [],
            "forbidden_changes": [],
            "approved_reference_id": None,
            "continuation_source_reference_id": continuation,
        }
        expected_lineage = (
            None
            if continuation is None
            else {"kind": "continuation", "source_reference_id": continuation}
        )
        if lineage is ...:
            lineage = expected_lineage
        return {
            "size_bytes": 7,
            "sha256": "0" * 64,
            "generation": {
                "job_id": job_id,
                "attempt_id": "attempt_shape",
                "model_id": "uv.image.shape",
                "capability_id": "image.generate",
                "offer_id": "shape.image_generate",
                "adapter_id": "shape",
                "request_digest": "1" * 64,
                "contract": contract,
                "lineage": lineage,
            },
        }

    def test_direct_generation_reference_with_consistent_lineage_is_valid(self) -> None:
        reference = ProjectReference(
            id="artifact_shape",
            kind="image",
            path="artifacts/generated_attempt_shape.png",
            metadata=self._metadata(),
        )
        self.assertEqual(reference.path, "artifacts/generated_attempt_shape.png")

        continued = ProjectReference(
            id="artifact_shape_continued",
            kind="image",
            path="artifacts/generated_attempt_shape.png",
            metadata=self._metadata(continuation="artifact_source"),
        )
        self.assertEqual(
            continued.metadata["generation"]["lineage"],
            {"kind": "continuation", "source_reference_id": "artifact_source"},
        )

    def test_generation_reference_rejects_nested_artifacts_path(self) -> None:
        with self.assertRaisesRegex(ProjectValidationError, "canonical artifacts|Generation artifact path"):
            ProjectReference(
                id="artifact_nested",
                kind="image",
                path="artifacts/nested/generated_attempt_shape.png",
                metadata=self._metadata(),
            )

    def test_generation_reference_rejects_lineage_drift(self) -> None:
        with self.assertRaisesRegex(ProjectValidationError, "lineage"):
            ProjectReference(
                id="artifact_bad_lineage",
                kind="image",
                path="artifacts/generated_attempt_shape.png",
                metadata=self._metadata(
                    continuation="artifact_source",
                    lineage={"kind": "continuation", "source_reference_id": "artifact_other"},
                ),
            )

    def test_generation_namespace_rejects_non_object_authority(self) -> None:
        for malformed in (None, [], "legacy", 7):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(ProjectValidationError, "generation.*object|Generation authority"):
                    ProjectReference(
                        id="artifact_bad_generation_namespace",
                        kind="image",
                        path="artifacts/generated_attempt_shape.png",
                        metadata={"generation": malformed},
                    )

    def test_generation_reference_rejects_unsafe_job_identity(self) -> None:
        with self.assertRaisesRegex(ProjectValidationError, "job_id"):
            ProjectReference(
                id="artifact_unsafe_job",
                kind="image",
                path="artifacts/generated_attempt_shape.png",
                metadata=self._metadata(job_id="../other-project/tasks/job_escape"),
            )

    def test_generation_reference_cannot_move_into_sources_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStore(Path(temp) / "projects")
            project = store.create_project(
                title="Stage 19 Generation source role",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage19_generation_source_role",
            )
            reference = ProjectReference(
                id="artifact_source_role",
                kind="image",
                path="artifacts/generated_attempt_shape.png",
                metadata=self._metadata(),
            )
            with self.assertRaisesRegex(ProjectValidationError, "Generation.*sources|artifact authority"):
                store.update_project(
                    project.project_id,
                    sources=(reference,),
                    artifacts=(),
                )

    def test_store_rejects_durable_generation_shape_corruption_before_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStore(Path(temp) / "projects")
            project = store.create_project(
                title="Stage 19 Generation shape",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage19_generation_shape",
            )
            path = store.project_path(project.project_id)
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["artifacts"].append(
                {
                    "id": "artifact_corrupt_shape",
                    "kind": "image",
                    "path": "artifacts/nested/generated_attempt_shape.png",
                    "metadata": self._metadata(),
                }
            )
            store._atomic_write_json(path, raw)

            with self.assertRaisesRegex(ProjectStoreError, "Invalid project document"):
                store.load_project(project.project_id)


if __name__ == "__main__":
    unittest.main()
