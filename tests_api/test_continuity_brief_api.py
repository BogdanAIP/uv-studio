from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects import AcceptedRangeEdit, ProjectStore, RangeEditStateStore
from uv_studio.server import app


class ContinuityBriefApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(recipe_id="general_video", title="Continuity API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.replacement = self.project_dir / "artifacts" / "replacement.mkv"
        self.source.write_bytes(b"source")
        self.replacement.write_bytes(b"replacement")
        (self.project_dir / "assets" / "reference.txt").write_text(
            "reference",
            encoding="utf-8",
        )
        self.edit = AcceptedRangeEdit(
            edit_id="edit_1",
            source_path="sources/source.mkv",
            start_us=1_000_000,
            end_us=2_000_000,
            replacement_path="artifacts/replacement.mkv",
        )
        RangeEditStateStore(self.store).accept(self.project.project_id, self.edit)
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _collection_url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/continuity-briefs"

    def _item_url(self, edit_id: str = "edit_1") -> str:
        return f"{self._collection_url()}/{edit_id}"

    def _payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "edit_id": self.edit.edit_id,
            "source_path": self.edit.source_path,
            "start_us": self.edit.start_us,
            "end_us": self.edit.end_us,
            "evidence": [
                {
                    "evidence_id": "ev_requested",
                    "role": "requested",
                    "path": self.edit.source_path,
                    "source_start_us": self.edit.start_us,
                    "source_end_us": self.edit.end_us,
                },
                {
                    "evidence_id": "ev_reference",
                    "role": "reference",
                    "path": "assets/reference.txt",
                    "source_start_us": None,
                    "source_end_us": None,
                },
            ],
            "mechanical_facts": [
                {
                    "fact_id": "fact_audio",
                    "key": "has_audio",
                    "value": False,
                    "unit": None,
                    "evidence_ids": ["ev_requested"],
                }
            ],
            "observations": [
                {
                    "observation_id": "obs_static",
                    "kind": "observation",
                    "statement": "The requested shot is visually static.",
                    "confidence": "high",
                    "evidence_ids": ["ev_requested"],
                }
            ],
            "constraints": [
                {
                    "constraint_id": "constraint_style",
                    "category": "style",
                    "requirement": "Preserve the existing visual style.",
                    "evidence_ids": ["ev_reference"],
                }
            ],
            "review_targets": [
                {
                    "target_id": "review_style",
                    "criterion": "Replacement remains consistent with the reference style.",
                    "required": True,
                    "evidence_ids": ["ev_reference"],
                }
            ],
        }

    def test_put_list_get_and_delete_round_trip(self) -> None:
        artifacts_before = sorted(
            path.name for path in (self.project_dir / "artifacts").iterdir()
        )
        saved = self.client.put(self._item_url(), json=self._payload())
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(len(saved.json()["briefs"]), 1)
        self.assertEqual(saved.json()["briefs"][0]["edit_id"], "edit_1")
        self.assertNotIn("replacement_path", saved.json()["briefs"][0])
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before,
        )

        listed = self.client.get(self._collection_url())
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json(), saved.json())

        fetched = self.client.get(self._item_url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json(), saved.json()["briefs"][0])

        deleted = self.client.delete(self._item_url())
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["briefs"], [])

    def test_brief_can_be_created_before_replacement_or_accepted_edit(self) -> None:
        RangeEditStateStore(self.store).remove(self.project.project_id, "edit_1")
        self.replacement.unlink()

        response = self.client.put(self._item_url(), json=self._payload())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["briefs"][0]["edit_id"], "edit_1")
        self.assertFalse(self.replacement.exists())

    def test_url_identity_mismatch_and_accepted_target_mismatch_are_422(self) -> None:
        wrong_url = self.client.put(self._item_url("edit_other"), json=self._payload())
        self.assertEqual(wrong_url.status_code, 422, wrong_url.text)

        wrong_range = self._payload()
        wrong_range["start_us"] = 1_100_000
        wrong_range["evidence"][0]["source_start_us"] = 1_100_000
        mismatch = self.client.put(self._item_url(), json=wrong_range)
        self.assertEqual(mismatch.status_code, 422, mismatch.text)
        self.assertIn("does not exactly match accepted edit", mismatch.text)

    def test_unknown_provider_runtime_fields_and_fact_keys_are_rejected(self) -> None:
        payload = self._payload()
        payload["provider_id"] = "forbidden-runtime-binding"
        response = self.client.put(self._item_url(), json=payload)
        self.assertEqual(response.status_code, 422, response.text)

        payload = self._payload()
        payload["mechanical_facts"][0]["key"] = "provider_id"
        response = self.client.put(self._item_url(), json=payload)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("runtime binding", response.text)

    def test_temporal_evidence_wrong_source_and_missing_evidence_file_are_422(self) -> None:
        wrong_source = self._payload()
        wrong_source["evidence"][0]["path"] = "assets/reference.txt"
        response = self.client.put(self._item_url(), json=wrong_source)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("must reference target source", response.text)

        missing_file = self._payload()
        missing_file["evidence"][1]["path"] = "assets/missing.txt"
        response = self.client.put(self._item_url(), json=missing_file)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("valid existing project file", response.text)

    def test_unknown_evidence_reference_is_422(self) -> None:
        unknown = self._payload()
        unknown["observations"][0]["evidence_ids"] = ["missing_evidence"]
        response = self.client.put(self._item_url(), json=unknown)
        self.assertEqual(response.status_code, 422, response.text)

    def test_missing_project_and_missing_brief_are_404(self) -> None:
        missing_project = self.client.get(
            "/api/uv/projects/prj_missing/continuity-briefs"
        )
        self.assertEqual(missing_project.status_code, 404, missing_project.text)

        missing_brief = self.client.get(self._item_url("edit_missing"))
        self.assertEqual(missing_brief.status_code, 404, missing_brief.text)

    def test_removed_accepted_edit_does_not_destroy_reusable_brief(self) -> None:
        saved = self.client.put(self._item_url(), json=self._payload())
        self.assertEqual(saved.status_code, 200, saved.text)
        RangeEditStateStore(self.store).remove(self.project.project_id, "edit_1")

        fetched = self.client.get(self._item_url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["edit_id"], "edit_1")

        deleted = self.client.delete(self._item_url())
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["briefs"], [])


if __name__ == "__main__":
    unittest.main()
