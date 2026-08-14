from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class SequenceReviewAssistApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        response = self.client.post("/api/uv/projects", json={"title": "Review assist API"})
        self.assertEqual(response.status_code, 201, response.text)
        self.project_id = response.json()["project_id"]
        self.project_dir = self.store.project_directory(self.project_id)
        self._register_video("src", "candidate.mp4", b"candidate-assist", 3_000_000)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _register_video(
        self, reference_id: str, filename: str, payload: bytes, duration_us: int
    ) -> None:
        path = self.project_dir / "sources" / filename
        path.write_bytes(payload)
        project = self.store.load_project(self.project_id)
        reference = ProjectReference(
            id=reference_id,
            kind="video",
            path=f"sources/{filename}",
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": duration_us,
            },
        )
        self.store.update_project(
            self.project_id,
            sources=(*project.sources, reference),
        )

    def _command(self, payload: dict) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/sequence/commands",
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["payload"]

    def _prepare_take(self) -> None:
        self._command(
            {
                "command": "create_sequence",
                "sequence_id": "seq",
                "title": "Review assist",
            }
        )
        self._command(
            {
                "command": "upsert_sequence_shot",
                "sequence_id": "seq",
                "shot_id": "shot",
                "order": 0,
                "intent": "Hold subject identity.",
                "anchor_take_id": None,
                "locks": [
                    {
                        "rule_id": "identity_lock",
                        "category": "content",
                        "requirement": "Keep subject identity.",
                    }
                ],
                "allowed_changes": [],
                "review_targets": [
                    {
                        "target_id": "identity",
                        "criterion": "Subject identity matches.",
                        "required": True,
                    }
                ],
            }
        )
        self._command(
            {
                "command": "register_sequence_take",
                "sequence_id": "seq",
                "shot_id": "shot",
                "reference_id": "src",
                "take_id": "take",
            }
        )

    def test_missing_take_remains_not_found(self) -> None:
        self._prepare_take()
        response = self.client.get(
            f"/api/uv/projects/{self.project_id}/sequence/seq/takes/missing/review-assist"
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"], "Sequence take not found")

    def test_vlm_assist_round_trip_requires_human_review(self) -> None:
        self._prepare_take()
        assist = self.client.get(
            f"/api/uv/projects/{self.project_id}/sequence/seq/takes/take/review-assist",
            params={"window_us": 1_000_000, "samples": 3},
        )
        self.assertEqual(assist.status_code, 200, assist.text)
        package = assist.json()
        self.assertEqual(package["capability_id"], "media.understand")
        self.assertTrue(package["requires_human_confirmation"])
        self.assertFalse(package["canonical_state_mutated"])
        self.assertEqual(
            package["capability_input"]["media"][0]["project_reference"],
            "sources/candidate.mp4",
        )

        normalized = self.client.post(
            f"/api/uv/projects/{self.project_id}/sequence/seq/takes/take/review-assist/normalize",
            json={
                "binding": package["binding"],
                "verdict": "approved",
                "results": [
                    {
                        "target_id": "identity",
                        "outcome": "pass",
                        "note": "Bounded candidate evidence matches.",
                    }
                ],
                "observations": [
                    {
                        "observation_id": "identity_observed",
                        "kind": "observation",
                        "category": "content",
                        "statement": "Subject appearance remains consistent.",
                        "confidence": "medium",
                    }
                ],
                "note": "VLM suggestion only.",
            },
        )
        self.assertEqual(normalized.status_code, 200, normalized.text)
        suggestion = normalized.json()
        self.assertEqual(suggestion["verdict"], "approved")
        self.assertTrue(suggestion["requires_human_confirmation"])
        self.assertFalse(suggestion["canonical_state_mutated"])

        state = self.client.get(
            f"/api/uv/projects/{self.project_id}/sequence/state"
        )
        self.assertEqual(state.status_code, 200, state.text)
        sequence = state.json()["sequences"][0]
        take = sequence["takes"][0]
        self.assertEqual(take["status"], "prepared")
        self.assertIsNone(take["current_review_id"])
        self.assertEqual(sequence["reviews"], [])

        review = self._command(
            {
                "command": "review_sequence_take",
                "sequence_id": "seq",
                "take_id": "take",
                "verdict": suggestion["verdict"],
                "results": suggestion["results"],
                "observations": suggestion["observations"],
                "note": "Human confirmed the suggested evidence.",
            }
        )
        self.assertEqual(review["verdict"], "approved")
        state_after_human = self.client.get(
            f"/api/uv/projects/{self.project_id}/sequence/state"
        ).json()["sequences"][0]
        self.assertEqual(len(state_after_human["reviews"]), 1)
        self.assertEqual(
            state_after_human["takes"][0]["current_review_id"],
            review["review_id"],
        )


if __name__ == "__main__":
    unittest.main()
