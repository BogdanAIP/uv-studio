from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ContinuityConstraint,
    ContinuityEvidence,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReviewTarget,
)
from uv_studio.server import app


class ReplacementPlanApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Replacement plan API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        self.brief_store = RangeContinuityBriefStore(self.store)
        self.brief_store.upsert(self.project.project_id, self._brief())
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _brief(self, *, changed: bool = False) -> RangeContinuityBrief:
        suffix = " updated" if changed else ""
        return RangeContinuityBrief(
            edit_id="edit_1",
            source_path="sources/source.mkv",
            start_us=1_000_000,
            end_us=2_000_000,
            evidence=(
                ContinuityEvidence(
                    evidence_id="requested",
                    role="requested",
                    path="sources/source.mkv",
                    source_start_us=1_000_000,
                    source_end_us=2_000_000,
                ),
            ),
            constraints=(
                ContinuityConstraint(
                    constraint_id="keep_motion",
                    category="motion",
                    requirement=f"Preserve camera motion{suffix}.",
                    evidence_ids=("requested",),
                ),
            ),
            review_targets=(
                ReviewTarget(
                    target_id="review_motion",
                    criterion="Verify camera motion continuity.",
                    required=True,
                    evidence_ids=("requested",),
                ),
            ),
        )

    def _collection_url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/replacement-plans"

    def _item_url(self, edit_id: str = "edit_1") -> str:
        return f"{self._collection_url()}/{edit_id}"

    def _proposal(self, *, method_class: str = "deterministic_edit") -> dict[str, object]:
        return {
            "edit_id": "edit_1",
            "method_class": method_class,
            "goal": "Remove the unwanted object while preserving continuity.",
            "required_changes": ["Remove the unwanted object."],
            "allowed_changes": ["Minor local texture repair."],
            "forbidden_changes": ["Do not change camera motion."],
            "audio_strategy": "preserve_source",
        }

    def test_approve_list_get_delete_without_replacement_artifact(self) -> None:
        before = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        approved = self.client.put(self._item_url(), json=self._proposal())
        self.assertEqual(approved.status_code, 200, approved.text)
        plan = approved.json()["plans"][0]
        self.assertEqual(plan["source_path"], "sources/source.mkv")
        self.assertEqual(plan["start_us"], 1_000_000)
        self.assertEqual(plan["end_us"], 2_000_000)
        self.assertEqual(plan["constraint_ids"], ["keep_motion"])
        self.assertEqual(plan["review_target_ids"], ["review_motion"])
        self.assertEqual(plan["sample_policy"], "not_required")
        self.assertEqual(len(plan["brief_sha256"]), 64)
        self.assertNotIn("provider_id", plan)
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            before,
        )

        listed = self.client.get(self._collection_url())
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json(), approved.json())

        fetched = self.client.get(self._item_url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json(), plan)

        deleted = self.client.delete(self._item_url())
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["plans"], [])

    def test_generative_approval_derives_sample_first_policy(self) -> None:
        response = self.client.put(
            self._item_url(),
            json=self._proposal(method_class="generative_transform"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["plans"][0]["sample_policy"],
            "required_before_full_generation",
        )

    def test_missing_brief_and_url_identity_mismatch_are_422(self) -> None:
        self.brief_store.remove(self.project.project_id, "edit_1")
        missing = self.client.put(self._item_url(), json=self._proposal())
        self.assertEqual(missing.status_code, 422, missing.text)
        self.assertIn("requires a current valid RangeContinuityBrief", missing.text)

        self.brief_store.upsert(self.project.project_id, self._brief())
        wrong_url = self.client.put(self._item_url("edit_other"), json=self._proposal())
        self.assertEqual(wrong_url.status_code, 422, wrong_url.text)

    def test_provider_runtime_fields_and_unknown_method_are_rejected(self) -> None:
        payload = self._proposal()
        payload["provider_id"] = "forbidden"
        response = self.client.put(self._item_url(), json=payload)
        self.assertEqual(response.status_code, 422, response.text)

        payload = self._proposal()
        payload["method_class"] = "kling"
        response = self.client.put(self._item_url(), json=payload)
        self.assertEqual(response.status_code, 422, response.text)

    def test_change_scope_conflict_is_422(self) -> None:
        payload = self._proposal()
        payload["forbidden_changes"] = ["Remove the unwanted object."]
        response = self.client.put(self._item_url(), json=payload)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("must be disjoint", response.text)

    def test_brief_change_does_not_hide_structural_plan(self) -> None:
        approved = self.client.put(self._item_url(), json=self._proposal())
        self.assertEqual(approved.status_code, 200, approved.text)
        old_digest = approved.json()["plans"][0]["brief_sha256"]
        self.brief_store.upsert(self.project.project_id, self._brief(changed=True))

        fetched = self.client.get(self._item_url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["brief_sha256"], old_digest)

        reapproved = self.client.put(self._item_url(), json=self._proposal())
        self.assertEqual(reapproved.status_code, 200, reapproved.text)
        self.assertNotEqual(reapproved.json()["plans"][0]["brief_sha256"], old_digest)

    def test_missing_project_and_plan_are_404(self) -> None:
        missing_project = self.client.get("/api/uv/projects/prj_missing/replacement-plans")
        self.assertEqual(missing_project.status_code, 404, missing_project.text)

        missing_plan = self.client.get(self._item_url("edit_missing"))
        self.assertEqual(missing_plan.status_code, 404, missing_plan.text)


if __name__ == "__main__":
    unittest.main()
