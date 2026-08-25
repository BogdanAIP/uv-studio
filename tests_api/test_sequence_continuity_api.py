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


class SequenceContinuityApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"recipe_id": "general_video", "title": "Sequence API"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        self.project_dir = self.store.project_directory(self.project_id)
        self.source_a = self._register_video("src_a", "a.mp4", b"anchor-api", 4_000_000)
        self.source_b = self._register_video("src_b", "b.mp4", b"candidate-api", 3_000_000)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _register_video(
        self, reference_id: str, filename: str, payload: bytes, duration_us: int
    ) -> ProjectReference:
        path = self.project_dir / "sources" / filename
        path.write_bytes(payload)
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
        project = self.store.load_project(self.project_id)
        self.store.update_project(
            self.project_id,
            sources=(*project.sources, reference),
        )
        return reference

    def _command(self, payload: dict, expected: int = 201) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/sequence/commands",
            json=payload,
        )
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def test_optional_sequence_user_path_and_timeline_context(self) -> None:
        empty = self.client.get(f"/api/uv/projects/{self.project_id}/sequence/state")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json(), {"schema_version": 1, "sequences": []})

        created = self._command(
            {
                "command": "create_sequence",
                "sequence_id": "seq_main",
                "title": "Two linked shots",
            }
        )
        self.assertEqual(created["payload"]["plans"], [])

        plan_1 = self._command(
            {
                "command": "upsert_sequence_shot",
                "sequence_id": "seq_main",
                "shot_id": "shot_01",
                "order": 0,
                "intent": "Establish subject.",
                "anchor_take_id": None,
                "locks": [
                    {
                        "rule_id": "lock_subject",
                        "category": "content",
                        "requirement": "Keep subject identity.",
                    }
                ],
                "allowed_changes": [],
                "review_targets": [
                    {
                        "target_id": "target_subject",
                        "criterion": "Subject identity is consistent.",
                        "required": True,
                    }
                ],
            }
        )["payload"]
        self.assertEqual(plan_1["anchor_take_id"], None)
        take_1 = self._command(
            {
                "command": "register_sequence_take",
                "sequence_id": "seq_main",
                "shot_id": "shot_01",
                "reference_id": self.source_a.id,
                "take_id": "take_01",
            }
        )["payload"]
        self.assertEqual(take_1["status"], "prepared")

        context_1 = self.client.get(
            f"/api/uv/projects/{self.project_id}/sequence/seq_main/takes/take_01/context"
        )
        self.assertEqual(context_1.status_code, 200, context_1.text)
        self.assertIsNone(context_1.json()["anchor"])

        review_1 = self._command(
            {
                "command": "review_sequence_take",
                "sequence_id": "seq_main",
                "take_id": "take_01",
                "verdict": "approved",
                "results": [
                    {
                        "target_id": "target_subject",
                        "outcome": "pass",
                        "note": "Manual boundary review.",
                    }
                ],
                "observations": [
                    {
                        "observation_id": "obs_exit",
                        "kind": "observation",
                        "category": "motion",
                        "statement": "Subject exits screen-right.",
                        "confidence": "high",
                    }
                ],
                "note": "First take accepted for continuity.",
            }
        )["payload"]
        self.assertEqual(review_1["verdict"], "approved")
        accepted_1 = self._command(
            {
                "command": "accept_sequence_take",
                "sequence_id": "seq_main",
                "review_id": review_1["review_id"],
            }
        )["payload"]
        self.assertEqual(accepted_1["status"], "accepted")
        anchor_1 = self._command(
            {
                "command": "reanchor_sequence",
                "sequence_id": "seq_main",
                "take_id": "take_01",
            }
        )["payload"]
        self.assertEqual(anchor_1["anchor_take_id"], "take_01")

        plan_2 = self._command(
            {
                "command": "upsert_sequence_shot",
                "sequence_id": "seq_main",
                "shot_id": "shot_02",
                "order": 1,
                "intent": "Continue into a closer framing.",
                "anchor_take_id": "take_01",
                "locks": [
                    {
                        "rule_id": "lock_direction",
                        "category": "motion",
                        "requirement": "Keep screen-right direction.",
                    }
                ],
                "allowed_changes": [
                    {
                        "rule_id": "allow_scale",
                        "category": "visual",
                        "requirement": "Framing may get closer.",
                    }
                ],
                "review_targets": [
                    {
                        "target_id": "target_direction",
                        "criterion": "Candidate continues accepted direction.",
                        "required": True,
                    }
                ],
            }
        )["payload"]
        self.assertEqual(plan_2["anchor_take_id"], "take_01")
        self._command(
            {
                "command": "register_sequence_take",
                "sequence_id": "seq_main",
                "shot_id": "shot_02",
                "reference_id": self.source_b.id,
                "take_id": "take_02",
            }
        )
        context_2 = self.client.get(
            f"/api/uv/projects/{self.project_id}/sequence/seq_main/takes/take_02/context",
            params={"window_us": 1_000_000, "samples": 3},
        )
        self.assertEqual(context_2.status_code, 200, context_2.text)
        payload = context_2.json()
        self.assertEqual(payload["anchor"]["take_id"], "take_01")
        self.assertEqual(payload["anchor"]["sample_times_us"], [3_000_000, 3_500_000, 4_000_000])
        self.assertEqual(payload["candidate"]["sample_times_us"], [0, 500_000, 1_000_000])

        state = self.client.get(f"/api/uv/projects/{self.project_id}/sequence/state")
        self.assertEqual(state.status_code, 200, state.text)
        sequence = state.json()["sequences"][0]
        self.assertEqual(sequence["anchor_take_id"], "take_01")
        self.assertEqual([plan["shot_id"] for plan in sequence["plans"]], ["shot_01", "shot_02"])
        self.assertEqual(
            sequence["reviews"][0]["observations"][0]["statement"],
            "Subject exits screen-right.",
        )

    def test_approved_review_cannot_omit_required_target(self) -> None:
        self._command(
            {
                "command": "create_sequence",
                "sequence_id": "seq_main",
                "title": "Guard",
            }
        )
        self._command(
            {
                "command": "upsert_sequence_shot",
                "sequence_id": "seq_main",
                "shot_id": "shot_01",
                "order": 0,
                "intent": "Guard review.",
                "anchor_take_id": None,
                "locks": [],
                "allowed_changes": [],
                "review_targets": [
                    {
                        "target_id": "required",
                        "criterion": "Must pass.",
                        "required": True,
                    }
                ],
            }
        )
        self._command(
            {
                "command": "register_sequence_take",
                "sequence_id": "seq_main",
                "shot_id": "shot_01",
                "reference_id": self.source_a.id,
                "take_id": "take_01",
            }
        )
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/sequence/commands",
            json={
                "command": "review_sequence_take",
                "sequence_id": "seq_main",
                "take_id": "take_01",
                "verdict": "approved",
                "results": [],
                "observations": [],
                "note": None,
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("cover each current review target", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
