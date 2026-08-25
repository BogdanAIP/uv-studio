from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.continuity_brief import RangeContinuityBriefStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class EditorCommandsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"recipe_id": "general_video", "title": "Editor Project"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

        media_store = ProjectSourceMediaStore(self.store)
        allocation = media_store.allocate(self.project_id, "source.mp4")
        allocation.absolute_path.write_bytes(b"registered-video")
        project = media_store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "source.mp4",
                "content_type": "video/mp4",
                "size_bytes": len(b"registered-video"),
                "sha256": "0" * 64,
                "duration_us": 20_000_000,
                "has_audio": True,
                "width": 1920,
                "height": 1080,
            },
        )
        self.source = project.sources[0]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _select_range(self) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "select_range",
                "source_id": self.source.id,
                "start_us": 7_000_000,
                "end_us": 11_000_000,
                "change_request": "Replace the selected action while preserving continuity.",
                "context_before_us": 3_000_000,
                "context_after_us": 2_000_000,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_select_range_creates_canonical_brief_from_source_id(self) -> None:
        result = self._select_range()
        self.assertEqual(result["command"], "select_range")
        self.assertEqual(result["source_id"], self.source.id)
        self.assertTrue(result["edit_id"].startswith("edit_"))
        self.assertEqual(result["resolved_range"]["source_path"], self.source.path)
        self.assertEqual(result["resolved_range"]["requested"]["start_us"], 7_000_000)
        self.assertEqual(result["resolved_range"]["requested"]["end_us"], 11_000_000)
        self.assertEqual(result["resolved_range"]["context"]["start_us"], 4_000_000)
        self.assertEqual(result["resolved_range"]["context"]["end_us"], 13_000_000)

        brief = result["brief"]
        self.assertEqual(brief["source_path"], self.source.path)
        self.assertEqual(brief["start_us"], 7_000_000)
        self.assertEqual(brief["end_us"], 11_000_000)
        self.assertEqual(
            [(item["evidence_id"], item["role"]) for item in brief["evidence"]],
            [("requested", "requested"), ("before", "before"), ("after", "after")],
        )
        self.assertEqual(
            {item["target_id"] for item in brief["review_targets"]},
            {"requested_change", "boundary_continuity"},
        )
        self.assertTrue(all(item["required"] for item in brief["review_targets"]))
        self.assertIn(
            "Replace the selected action",
            next(
                item["criterion"]
                for item in brief["review_targets"]
                if item["target_id"] == "requested_change"
            ),
        )

        persisted = RangeContinuityBriefStore(self.store).load(
            self.project_id,
            validate_references=True,
        )
        self.assertEqual(len(persisted.briefs), 1)
        self.assertEqual(persisted.briefs[0].edit_id, result["edit_id"])

        state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(state.status_code, 200, state.text)
        payload = state.json()
        self.assertEqual([item["id"] for item in payload["sources"]], [self.source.id])
        self.assertEqual([item["edit_id"] for item in payload["briefs"]], [result["edit_id"]])
        self.assertEqual(payload["artifacts"], [])
        self.assertEqual(payload["replacement_plans"], [])
        self.assertEqual(payload["replacement_candidates"], [])
        self.assertEqual(payload["sample_approvals"], [])
        self.assertEqual(payload["replacement_reviews"], [])
        self.assertEqual(payload["accepted_edits"], [])

    def test_editor_state_exposes_complete_prepared_asset_review_chain(self) -> None:
        selected = self._select_range()
        edit_id = selected["edit_id"]

        plan_response = self.client.put(
            f"/api/uv/projects/{self.project_id}/replacement-plans/{edit_id}",
            json={
                "edit_id": edit_id,
                "method_class": "prepared_asset",
                "goal": "Use the prepared project video as the exact selected replacement.",
                "required_changes": ["Replace the selected action while preserving continuity."],
                "allowed_changes": [],
                "forbidden_changes": ["Do not change media outside the selected range."],
                "audio_strategy": "preserve_source",
            },
        )
        self.assertEqual(plan_response.status_code, 200, plan_response.text)

        candidate_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/replacement-candidates/prepared-asset",
            json={"edit_id": edit_id, "source_path": self.source.path},
        )
        self.assertEqual(candidate_response.status_code, 200, candidate_response.text)
        candidate = candidate_response.json()["candidate"]
        self.assertEqual(candidate["edit_id"], edit_id)
        self.assertEqual(candidate["stage"], "full")
        self.assertEqual(candidate["method_class"], "prepared_asset")

        state_before_review = self.client.get(
            f"/api/uv/projects/{self.project_id}/editor/state"
        )
        self.assertEqual(state_before_review.status_code, 200, state_before_review.text)
        payload = state_before_review.json()
        self.assertEqual([item["edit_id"] for item in payload["replacement_plans"]], [edit_id])
        self.assertEqual(
            [item["candidate_id"] for item in payload["replacement_candidates"]],
            [candidate["candidate_id"]],
        )
        self.assertEqual([item["id"] for item in payload["artifacts"]], [candidate["artifact_id"]])

        artifact_media = self.client.get(
            f"/api/uv/projects/{self.project_id}/artifacts/{candidate['artifact_id']}/media"
        )
        self.assertEqual(artifact_media.status_code, 200, artifact_media.text)
        self.assertEqual(artifact_media.content, b"registered-video")
        self.assertEqual(artifact_media.headers["content-type"], "video/mp4")

        observation_id = "obs_exact_candidate"
        review_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/replacement-reviews",
            json={
                "candidate_id": candidate["candidate_id"],
                "verdict": "approved",
                "observations": [
                    {
                        "observation_id": observation_id,
                        "kind": "observation",
                        "statement": "The exact full candidate satisfies the requested replacement and joins the selected boundaries.",
                        "confidence": "high",
                        "evidence": [
                            {"kind": "candidate_artifact", "ref_id": candidate["artifact_id"]},
                            {"kind": "brief_evidence", "ref_id": "requested"},
                        ],
                    }
                ],
                "assessments": [
                    {
                        "target_id": target["target_id"],
                        "outcome": "pass",
                        "observation_ids": [observation_id],
                    }
                    for target in selected["brief"]["review_targets"]
                ],
            },
        )
        self.assertEqual(review_response.status_code, 201, review_response.text)
        review = review_response.json()
        self.assertEqual(review["candidate_id"], candidate["candidate_id"])
        self.assertEqual(review["verdict"], "approved")

        state_with_review = self.client.get(
            f"/api/uv/projects/{self.project_id}/editor/state"
        )
        self.assertEqual(state_with_review.status_code, 200, state_with_review.text)
        self.assertEqual(
            [item["review_id"] for item in state_with_review.json()["replacement_reviews"]],
            [review["review_id"]],
        )

        accepted_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/replacement-reviews/{review['review_id']}/accept"
        )
        self.assertEqual(accepted_response.status_code, 201, accepted_response.text)

        final_state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(final_state.status_code, 200, final_state.text)
        accepted = final_state.json()["accepted_edits"]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["edit_id"], edit_id)
        self.assertEqual(accepted[0]["replacement_path"], candidate["artifact_path"])

    def test_select_range_clamps_context_without_changing_requested_identity(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "select_range",
                "source_id": self.source.id,
                "start_us": 1_000_000,
                "end_us": 19_000_000,
                "change_request": "Change the scene.",
                "context_before_us": 5_000_000,
                "context_after_us": 5_000_000,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        resolved = response.json()["resolved_range"]
        self.assertEqual(resolved["requested"]["start_us"], 1_000_000)
        self.assertEqual(resolved["requested"]["end_us"], 19_000_000)
        self.assertEqual(resolved["context"]["start_us"], 0)
        self.assertEqual(resolved["context"]["end_us"], 20_000_000)

    def test_invalid_range_or_source_does_not_create_brief(self) -> None:
        outside = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "select_range",
                "source_id": self.source.id,
                "start_us": 19_000_000,
                "end_us": 21_000_000,
                "change_request": "Too long.",
            },
        )
        self.assertEqual(outside.status_code, 422, outside.text)
        self.assertEqual(RangeContinuityBriefStore(self.store).load(self.project_id).briefs, ())

        missing = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "select_range",
                "source_id": "src_missing",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "change_request": "Missing source.",
            },
        )
        self.assertEqual(missing.status_code, 404, missing.text)
        self.assertEqual(RangeContinuityBriefStore(self.store).load(self.project_id).briefs, ())

    def test_raw_path_and_unknown_command_fields_are_rejected(self) -> None:
        bypass = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "select_range",
                "source_id": self.source.id,
                "source_path": "sources/attacker.mp4",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "change_request": "Do not accept raw paths.",
            },
        )
        self.assertEqual(bypass.status_code, 422, bypass.text)

        unknown = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "mutate_mlt_xml",
                "source_id": self.source.id,
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "change_request": "Bypass.",
            },
        )
        self.assertEqual(unknown.status_code, 422, unknown.text)
        self.assertEqual(RangeContinuityBriefStore(self.store).load(self.project_id).briefs, ())


if __name__ == "__main__":
    unittest.main()
