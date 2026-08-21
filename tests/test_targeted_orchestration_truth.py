from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uv_studio.orchestration import (
    _current_targeted_outcome,
    _targeted_readiness,
    _without_consumed_accept_actions,
)
from uv_studio.orchestration.models import (
    ProjectWorkflowState,
    WorkflowAction,
    WorkflowArtifact,
    WorkflowDiagnostic,
    WorkflowPrerequisite,
    WorkflowReadiness,
)


def _accept_action(*review_ids: str) -> WorkflowAction:
    return WorkflowAction(
        action_id="accept_replacement",
        title="Accept",
        explanation="Accept current approved review",
        enabled=bool(review_ids),
        blocked_by=() if review_ids else ("edit.review",),
        prerequisite_ids=("edit.review",),
        input_schema={
            "type": "object",
            "properties": {"review_id": {"type": "string", "enum": list(review_ids)}},
        },
        suggested_input={"review_id": review_ids[0]} if review_ids else {},
        execution_class="domain_command",
        authorization_class="none",
        capability_id=None,
        expected_result="accepted_range_edit",
    )


def _prerequisite(prerequisite_id: str, satisfied: bool) -> WorkflowPrerequisite:
    return WorkflowPrerequisite(
        prerequisite_id=prerequisite_id,
        title=prerequisite_id,
        explanation=prerequisite_id,
        satisfied=satisfied,
        resolution=None if satisfied else f"resolve {prerequisite_id}",
    )


def _state(
    *,
    actions: tuple[WorkflowAction, ...] = (),
    artifacts: tuple[WorkflowArtifact, ...] = (),
    prerequisites: tuple[WorkflowPrerequisite, ...] = (),
    diagnostics: tuple[WorkflowDiagnostic, ...] = (),
) -> ProjectWorkflowState:
    return ProjectWorkflowState(
        project_id="proj_truth",
        recipe_id="free_project",
        recipe_title="Free project",
        readiness=WorkflowReadiness.READY,
        summary="truth fixture",
        current_outcome=None,
        prerequisites=prerequisites,
        relevant_workspaces=(),
        next_actions=actions,
        active_jobs=(),
        user_decisions=(
            {
                "kind": "accepted_range_edit",
                "edit_id": "edit_used",
                "source_path": "sources/source.mp4",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
            },
        ),
        recent_artifacts=artifacts,
        diagnostics=diagnostics,
    )


class TargetedOrchestrationTruthTests(unittest.TestCase):
    def test_consumed_review_is_removed_but_pending_review_remains(self) -> None:
        state = _state(actions=(_accept_action("review_used", "review_pending"),))
        loaded = SimpleNamespace(
            reviews=(
                SimpleNamespace(review_id="review_used", edit_id="edit_used"),
                SimpleNamespace(review_id="review_pending", edit_id="edit_pending"),
            )
        )
        source_media = SimpleNamespace(project_store=object())

        with patch("uv_studio.orchestration.ReplacementReviewStore") as store_type:
            store_type.return_value.load.return_value = loaded
            actions = _without_consumed_accept_actions(state, source_media)

        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(
            action.input_schema["properties"]["review_id"]["enum"],
            ("review_pending",),
        )
        self.assertEqual(action.suggested_input, {"review_id": "review_pending"})

    def test_accept_action_disappears_when_every_approved_review_is_already_consumed(self) -> None:
        state = _state(actions=(_accept_action("review_used"),))
        loaded = SimpleNamespace(
            reviews=(SimpleNamespace(review_id="review_used", edit_id="edit_used"),)
        )
        source_media = SimpleNamespace(project_store=object())

        with patch("uv_studio.orchestration.ReplacementReviewStore") as store_type:
            store_type.return_value.load.return_value = loaded
            actions = _without_consumed_accept_actions(state, source_media)

        self.assertEqual(actions, ())

    def test_current_outcome_requires_exact_current_accepted_edit_revision(self) -> None:
        stale = WorkflowArtifact(
            artifact_id="art_stale",
            kind="video",
            path="artifacts/stale.mkv",
            lifecycle="render",
            metadata={"source_path": "sources/source.mp4", "edit_ids": []},
        )
        current = WorkflowArtifact(
            artifact_id="art_current",
            kind="video",
            path="artifacts/current.mkv",
            lifecycle="render",
            metadata={"source_path": "sources/source.mp4", "edit_ids": ["edit_used"]},
        )
        state = _state(artifacts=(stale, current))

        self.assertEqual(_current_targeted_outcome(state), current)
        self.assertIsNone(_current_targeted_outcome(_state(artifacts=(stale,))))

    def test_readiness_requires_replacement_after_brief_exists(self) -> None:
        state = _state(
            prerequisites=(
                _prerequisite("capability.video.render_edits", True),
                _prerequisite("source.video", True),
                _prerequisite("edit.brief", True),
                _prerequisite("source.replacement_video", False),
                _prerequisite("edit.accepted", False),
            )
        )

        readiness, summary = _targeted_readiness(state, None)

        self.assertEqual(readiness, WorkflowReadiness.SETUP_REQUIRED)
        self.assertIn("видеоклип", summary)

    def test_readiness_returns_to_ready_when_replacement_is_present(self) -> None:
        state = _state(
            prerequisites=(
                _prerequisite("capability.video.render_edits", True),
                _prerequisite("source.video", True),
                _prerequisite("edit.brief", True),
                _prerequisite("source.replacement_video", True),
                _prerequisite("edit.accepted", False),
            )
        )

        readiness, summary = _targeted_readiness(state, None)

        self.assertEqual(readiness, WorkflowReadiness.READY)
        self.assertEqual(summary, "truth fixture")

    def test_missing_required_render_runtime_is_unavailable(self) -> None:
        state = _state(
            prerequisites=(
                _prerequisite("capability.video.render_edits", False),
                _prerequisite("source.video", True),
                _prerequisite("edit.brief", False),
                _prerequisite("source.replacement_video", False),
                _prerequisite("edit.accepted", False),
            ),
            diagnostics=(
                WorkflowDiagnostic(
                    code="targeted_edit_render_capability_unknown",
                    severity="error",
                    message="render capability missing",
                ),
            ),
        )

        readiness, summary = _targeted_readiness(state, None)

        self.assertEqual(readiness, WorkflowReadiness.UNAVAILABLE)
        self.assertIn("финальная сборка недоступна", summary)

    def test_current_master_is_reported_as_current_outcome_not_pending_render(self) -> None:
        current = WorkflowArtifact(
            artifact_id="art_current",
            kind="video",
            path="artifacts/current.mkv",
            lifecycle="render",
            metadata={"source_path": "sources/source.mp4", "edit_ids": ["edit_used"]},
        )
        state = _state(
            prerequisites=(
                _prerequisite("capability.video.render_edits", True),
                _prerequisite("source.video", True),
                _prerequisite("edit.brief", True),
                _prerequisite("source.replacement_video", True),
                _prerequisite("edit.accepted", True),
            )
        )

        readiness, summary = _targeted_readiness(state, current)

        self.assertEqual(readiness, WorkflowReadiness.READY)
        self.assertIn("мастер точно соответствует", summary)


if __name__ == "__main__":
    unittest.main()
