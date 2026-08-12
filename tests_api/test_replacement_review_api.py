from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ContinuityEvidence,
    ProjectReference,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementCandidateStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
    ReviewTarget,
)
from uv_studio.server import app


class ReplacementReviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Review API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        self.briefs = RangeContinuityBriefStore(self.store)
        self.plans = ReplacementPlanStore(self.store)
        self.candidates = ReplacementCandidateStore(self.store)
        self.briefs.upsert(self.project.project_id, self._brief())
        self.plans.approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="prepared_asset",
                goal="Prepare replacement.",
                required_changes=("Use the reviewed candidate.",),
            ),
        )
        artifact_path = "artifacts/art_candidate.mp4"
        (self.project_dir / artifact_path).write_bytes(b"candidate")
        reference = ProjectReference(id="art_candidate", kind="video", path=artifact_path)
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, reference),
        )
        candidate = self.candidates.make_candidate(
            self.project.project_id,
            candidate_id="cand_full",
            edit_id="edit_1",
            stage="full",
            artifact_id=reference.id,
            artifact_path=reference.path,
        )
        self.candidates.register(self.project.project_id, candidate)
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _brief(self, *, suffix: str = "") -> RangeContinuityBrief:
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
            review_targets=(
                ReviewTarget(
                    target_id="review_motion",
                    criterion=f"Check replacement continuity{suffix}.",
                    required=True,
                    evidence_ids=("requested",),
                ),
            ),
        )

    def _url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/replacement-reviews"

    def _body(self, *, verdict: str = "approved", outcome: str = "pass") -> dict[str, object]:
        return {
            "candidate_id": "cand_full",
            "verdict": verdict,
            "observations": [
                {
                    "observation_id": "obs_candidate",
                    "kind": "observation",
                    "statement": "The exact candidate satisfies the continuity target.",
                    "confidence": "high",
                    "evidence": [
                        {"kind": "brief_evidence", "ref_id": "requested"},
                        {"kind": "candidate_artifact", "ref_id": "art_candidate"},
                    ],
                }
            ],
            "assessments": [
                {
                    "target_id": "review_motion",
                    "outcome": outcome,
                    "observation_ids": ["obs_candidate"],
                }
            ],
        }

    def test_approved_review_is_created_then_accepts_exact_candidate(self) -> None:
        created = self.client.post(self._url(), json=self._body())
        self.assertEqual(created.status_code, 201, created.text)
        review = created.json()
        self.assertEqual(review["candidate_id"], "cand_full")
        self.assertEqual(review["source_path"], "sources/source.mkv")
        self.assertEqual((review["start_us"], review["end_us"]), (1_000_000, 2_000_000))
        self.assertNotIn("replacement_path", review)
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        validation = self.client.get(f"{self._url()}/{review['review_id']}/validation")
        self.assertEqual(validation.status_code, 200, validation.text)
        self.assertTrue(validation.json()["current"])

        accepted = self.client.post(f"{self._url()}/{review['review_id']}/accept")
        self.assertEqual(accepted.status_code, 201, accepted.text)
        edit = accepted.json()["edits"][0]
        self.assertEqual(edit["edit_id"], "edit_1")
        self.assertEqual(edit["source_path"], "sources/source.mkv")
        self.assertEqual((edit["start_us"], edit["end_us"]), (1_000_000, 2_000_000))
        self.assertEqual(edit["replacement_path"], "artifacts/art_candidate.mp4")

        listed = self.client.get(self._url())
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual([item["review_id"] for item in listed.json()["reviews"]], [review["review_id"]])

    def test_rejected_or_needs_revision_review_cannot_accept(self) -> None:
        rejected = self.client.post(self._url(), json=self._body(verdict="rejected", outcome="fail"))
        self.assertEqual(rejected.status_code, 201, rejected.text)
        blocked = self.client.post(f"{self._url()}/{rejected.json()['review_id']}/accept")
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(blocked.json()["detail"]["code"], "replacement_review_not_acceptable")

        revision = self.client.post(
            self._url(),
            json=self._body(verdict="needs_revision", outcome="uncertain"),
        )
        self.assertEqual(revision.status_code, 201, revision.text)
        blocked_revision = self.client.post(f"{self._url()}/{revision.json()['review_id']}/accept")
        self.assertEqual(blocked_revision.status_code, 409, blocked_revision.text)
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

    def test_review_becomes_stale_after_brief_and_plan_revision_but_remains_readable(self) -> None:
        created = self.client.post(self._url(), json=self._body())
        self.assertEqual(created.status_code, 201, created.text)
        review_id = created.json()["review_id"]

        self.briefs.upsert(self.project.project_id, self._brief(suffix=" after revision"))
        self.plans.approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="prepared_asset",
                goal="Prepare revised replacement.",
                required_changes=("Use revised approval.",),
            ),
        )

        structural = self.client.get(f"{self._url()}/{review_id}")
        self.assertEqual(structural.status_code, 200, structural.text)
        stale = self.client.get(f"{self._url()}/{review_id}/validation")
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(stale.json()["detail"]["code"], "replacement_review_stale")
        accept = self.client.post(f"{self._url()}/{review_id}/accept")
        self.assertEqual(accept.status_code, 409, accept.text)

    def test_canonical_acceptance_fields_are_server_owned_and_unknown_fields_fail(self) -> None:
        body = self._body()
        body["source_path"] = "sources/other.mkv"
        body["replacement_path"] = "artifacts/other.mp4"
        response = self.client.post(self._url(), json=body)
        self.assertEqual(response.status_code, 422, response.text)

        wrong_candidate_artifact = self._body()
        observations = wrong_candidate_artifact["observations"]
        assert isinstance(observations, list)
        evidence = observations[0]["evidence"]
        evidence[1]["ref_id"] = "art_other"
        rejected = self.client.post(self._url(), json=wrong_candidate_artifact)
        self.assertEqual(rejected.status_code, 422, rejected.text)


if __name__ == "__main__":
    unittest.main()
