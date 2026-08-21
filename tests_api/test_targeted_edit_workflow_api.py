from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
)
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityExecutionResult,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


def _registry() -> CapabilityRegistry:
    render = CapabilityDefinition(
        "video.render_edits",
        "Render accepted edits",
        "Materialize accepted targeted edits",
        OperationKind.DETERMINISTIC_MEDIA,
        (MediaKind.VIDEO,),
        (MediaKind.VIDEO,),
    )
    adapter = AdapterDefinition("local_ffmpeg", "FFmpeg", "local", AdapterKind.LOCAL)
    offer = CapabilityOffer(
        "local_ffmpeg.video_render_edits",
        render.capability_id,
        adapter.adapter_id,
        "Render accepted edits",
        OfferAvailability.AVAILABLE,
        "test runtime",
        LocalityClass.LOCAL,
        CostClass.FREE,
        False,
    )
    return CapabilityRegistry((render,), (adapter,), (offer,))


class StubLocalFFmpegExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"artifact_id": "art_render_test", "path": "artifacts/art_render_test.mkv"},
        )


class TargetedEditWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Targeted edit", recipe_id="free_project")
        self.registry = _registry()
        self.executor = StubLocalFFmpegExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = OneShotAuthorizationStore
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self, suffix: str = "workflow") -> str:
        return f"/api/uv/projects/{self.project.project_id}/{suffix}"

    def _add_video(self, filename: str, body: bytes) -> tuple[str, str]:
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project.project_id, filename)
        allocation.absolute_path.write_bytes(body)
        project = media.register(
            self.project.project_id,
            allocation,
            media_kind="video",
            metadata={
                "original_name": filename,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
                "duration_us": 6_000_000,
                "width": 640,
                "height": 360,
            },
        )
        reference = next(item for item in project.sources if item.id == allocation.source_id)
        return reference.id, reference.path

    def _action(self, state: dict, action_id: str) -> dict:
        return next(item for item in state["next_actions"] if item["action_id"] == action_id)

    def _select_range(self, source_id: str) -> dict:
        response = self.client.post(
            self._url("workflow/actions/select_target_range"),
            json={
                "source_id": source_id,
                "start_us": 1_000_000,
                "end_us": 3_000_000,
                "change_request": "Replace the selected interval with the prepared clip.",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]

    def _prepare(self, edit_id: str, replacement_source_id: str) -> dict:
        response = self.client.post(
            self._url("workflow/actions/prepare_replacement"),
            json={"edit_id": edit_id, "replacement_source_id": replacement_source_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]

    def test_empty_free_project_projects_targeted_edit_workspace(self) -> None:
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()
        self.assertEqual(state["readiness"], "setup_required")
        self.assertEqual(
            [item["workspace_id"] for item in state["relevant_workspaces"]],
            ["targeted_edit"],
        )
        select_action = self._action(state, "select_target_range")
        self.assertFalse(select_action["enabled"])
        self.assertEqual(select_action["blocked_by"], ["source.video"])
        self.assertIsNone(select_action["capability_id"])
        self.assertEqual(self._action(state, "render_accepted_edits")["capability_id"], "video.render_edits")

    def test_verified_video_enables_select_and_tamper_fails_closed(self) -> None:
        source_id, _source_path = self._add_video("source.mp4", b"verified source bytes")
        ready = self.client.get(self._url()).json()
        self.assertEqual(ready["readiness"], "ready")
        action = self._action(ready, "select_target_range")
        self.assertTrue(action["enabled"])
        self.assertEqual(action["input_schema"]["properties"]["source_id"]["enum"], [source_id])

        _reference, path = ProjectSourceMediaStore(self.store).resolve(
            self.project.project_id,
            source_id,
            expected_kind="video",
        )
        path.write_bytes(b"tampered source bytes")
        blocked = self.client.get(self._url()).json()
        self.assertEqual(blocked["readiness"], "setup_required")
        self.assertFalse(self._action(blocked, "select_target_range")["enabled"])
        self.assertEqual(blocked["diagnostics"][0]["code"], "source_media_unverified")

    def test_select_range_projects_brief_and_requires_distinct_replacement(self) -> None:
        source_id, _source_path = self._add_video("source.mp4", b"source bytes")
        selected = self._select_range(source_id)
        edit_id = selected["edit_id"]

        after_select = self.client.get(self._url()).json()
        prerequisite = next(item for item in after_select["prerequisites"] if item["prerequisite_id"] == "edit.brief")
        self.assertTrue(prerequisite["satisfied"])
        prepare = self._action(after_select, "prepare_replacement")
        self.assertFalse(prepare["enabled"])
        self.assertIn("source.replacement_video", prepare["blocked_by"])

        replacement_id, _replacement_path = self._add_video("replacement.mp4", b"replacement bytes")
        ready = self.client.get(self._url()).json()
        prepare = self._action(ready, "prepare_replacement")
        self.assertTrue(prepare["enabled"])
        self.assertEqual(
            prepare["input_schema"]["x-allowed-pairs"],
            [{"edit_id": edit_id, "replacement_source_id": replacement_id}],
        )

        rejected = self.client.post(
            self._url("workflow/actions/prepare_replacement"),
            json={"edit_id": edit_id, "replacement_source_id": source_id},
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["detail"]["code"], "workflow_action_input_rejected")

    def test_targeted_edit_chain_reaches_accepted_and_renderable_state(self) -> None:
        source_id, source_path = self._add_video("source.mp4", b"source bytes")
        replacement_id, _replacement_path = self._add_video("replacement.mp4", b"replacement bytes")
        selected = self._select_range(source_id)
        brief = selected["brief"]
        prepared = self._prepare(selected["edit_id"], replacement_id)
        candidate = prepared["candidate"]

        candidate_state = self.client.get(self._url()).json()
        self.assertTrue(
            next(
                item for item in candidate_state["prerequisites"]
                if item["prerequisite_id"] == "edit.candidate"
            )["satisfied"]
        )
        self.assertTrue(self._action(candidate_state, "review_replacement")["enabled"])

        observations = []
        assessments = []
        for index, target in enumerate(brief["review_targets"], start=1):
            observation_id = f"obs_{index}"
            observations.append(
                {
                    "observation_id": observation_id,
                    "kind": "observation",
                    "statement": f"Verified target {target['target_id']} against the candidate.",
                    "confidence": "high",
                    "evidence": [
                        {"kind": "candidate_artifact", "ref_id": candidate["artifact_id"]},
                        *[
                            {"kind": "brief_evidence", "ref_id": evidence_id}
                            for evidence_id in target["evidence_ids"]
                        ],
                    ],
                }
            )
            assessments.append(
                {
                    "target_id": target["target_id"],
                    "outcome": "pass",
                    "observation_ids": [observation_id],
                }
            )

        review_response = self.client.post(
            self._url("workflow/actions/review_replacement"),
            json={
                "candidate_id": candidate["candidate_id"],
                "verdict": "approved",
                "observations": observations,
                "assessments": assessments,
            },
        )
        self.assertEqual(review_response.status_code, 200, review_response.text)
        review = review_response.json()["result"]

        review_state = self.client.get(self._url()).json()
        self.assertTrue(self._action(review_state, "accept_replacement")["enabled"])

        accept_response = self.client.post(
            self._url("workflow/actions/accept_replacement"),
            json={"review_id": review["review_id"]},
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.text)
        self.assertEqual(len(accept_response.json()["result"]["edits"]), 1)

        accepted_state = self.client.get(self._url()).json()
        render_action = self._action(accepted_state, "render_accepted_edits")
        self.assertTrue(render_action["enabled"])
        self.assertEqual(render_action["suggested_input"], {"source_path": source_path})

        wrong_render = self.client.post(
            self._url("workflow/actions/render_accepted_edits"),
            json={"source_path": "sources/not-current.mp4"},
        )
        self.assertEqual(wrong_render.status_code, 422, wrong_render.text)
        self.assertEqual(self.executor.calls, [])

        rendered = self.client.post(
            self._url("workflow/actions/render_accepted_edits"),
            json={"source_path": source_path},
        )
        self.assertEqual(rendered.status_code, 200, rendered.text)
        self.assertEqual(rendered.json()["action_id"], "render_accepted_edits")
        self.assertEqual(
            self.executor.calls,
            [
                (
                    self.project.project_id,
                    "local_ffmpeg.video_render_edits",
                    {"source_path": source_path},
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
