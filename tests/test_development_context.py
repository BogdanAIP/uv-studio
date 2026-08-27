from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.close_development_context import close_context
from tools.validate_development_context import (
    ACTIVE_SLICE_PATH,
    DevelopmentContextError,
    NEXT_TASK_PATH,
    PROJECT_STATE_PATH,
    REQUIRED_CHECKS,
    validate_repository,
)


class DevelopmentContextValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.document = self._valid_active_document()
        self._write_repository()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _last_completed() -> dict:
        return {
            "id": "stage-5-dubbing-translation",
            "pull_request": 32,
            "merge_commit": "6f7531d9b87f569074a632972ca11e36562e8bd7",
        }

    @classmethod
    def _valid_active_document(cls, state: str = "draft") -> dict:
        return {
            "schema_version": 2,
            "lifecycle_state": state,
            "active_slice": {
                "id": "chore-agent-development-workflow",
                "kind": "chore",
                "roadmap_stage": "stage-5",
                "goal": "Make development state explicit and CI-checked.",
                "base_branch": "main",
                "branch": "chore/agent-development-workflow",
                "pull_request": 27,
                "write_scope": ["AGENTS.md", "project-context/**", "tools/**"],
            },
            "last_completed": cls._last_completed(),
            "handoff": {
                "next_slice_id": "stage-5-correctness-browser-e2e",
                "next_task_file": NEXT_TASK_PATH,
            },
            "coordination": {
                "integration_owner": "coordinator",
                "context_owner": "coordinator",
                "parallel_write_policy": "disjoint_paths",
            },
            "required_checks": sorted(REQUIRED_CHECKS),
        }

    @classmethod
    def _valid_idle_document(cls) -> dict:
        document = cls._valid_active_document()
        document["lifecycle_state"] = "idle"
        document["active_slice"] = None
        return document

    def _write_repository(self) -> None:
        active_path = self.root / ACTIVE_SLICE_PATH
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(json.dumps(self.document), encoding="utf-8")
        state = self.document["lifecycle_state"]
        if state == "idle":
            marker = (
                "<!-- uv-context-state: idle -->\n"
                "<!-- uv-last-completed: stage-5-dubbing-translation -->"
            )
        else:
            marker = (
                f"<!-- uv-context-state: {state} -->\n"
                "<!-- uv-active-slice: chore-agent-development-workflow -->"
            )
        (self.root / PROJECT_STATE_PATH).write_text(f"# State\n\n{marker}\n", encoding="utf-8")
        (self.root / NEXT_TASK_PATH).write_text(
            "# Next\n\n<!-- uv-next-slice: stage-5-correctness-browser-e2e -->\n",
            encoding="utf-8",
        )

    @staticmethod
    def _required_sections() -> tuple[str, ...]:
        return (
            "## Goal\nMake handoffs deterministic.",
            "## Changes\nAdd lifecycle validation.",
            "## Verification\nFocused tests pass.",
            "## Architecture impact\nRepository state becomes unambiguous.",
            "## Known limitations\nGitHub remains the source of live check results.",
            "## Next task\nClose Stage 5 correctness gaps.",
        )

    @classmethod
    def _valid_pr_body(cls) -> str:
        return "\n\n".join(
            (
                "<!-- uv-active-slice: chore-agent-development-workflow -->\n"
                "<!-- uv-next-slice: stage-5-correctness-browser-e2e -->",
                *cls._required_sections(),
            )
        )

    @classmethod
    def _valid_closure_pr_body(cls) -> str:
        return "\n\n".join(
            (
                "<!-- uv-lifecycle-closure: stage-5-dubbing-translation -->\n"
                "<!-- uv-next-slice: stage-5-correctness-browser-e2e -->",
                *cls._required_sections(),
            )
        )

    def _event(self, *, draft: bool, body: str | None = None) -> dict:
        return {
            "number": 27,
            "pull_request": {
                "draft": draft,
                "body": body if body is not None else self._valid_pr_body(),
                "head": {"ref": "chore/agent-development-workflow"},
                "base": {"ref": "main"},
            },
        }

    def _closure_event(
        self,
        *,
        draft: bool = False,
        body: str | None = None,
        head: str = "chore/stage-5-lifecycle-closure",
        base: str = "main",
    ) -> dict:
        return {
            "number": 33,
            "pull_request": {
                "draft": draft,
                "body": body if body is not None else self._valid_closure_pr_body(),
                "head": {"ref": head},
                "base": {"ref": base},
            },
        }

    def _event_path(self, payload: dict | str) -> Path:
        path = self.root / "event.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        return path

    def test_active_draft_repository_passes_local_and_push(self) -> None:
        local = validate_repository(self.root)
        pushed = validate_repository(self.root, event_name="push")
        self.assertEqual(local["lifecycle_state"], "draft")
        self.assertEqual(local["active_slice"]["id"], "chore-agent-development-workflow")
        self.assertEqual(local, pushed)

    def test_idle_repository_has_no_active_slice(self) -> None:
        self.document = self._valid_idle_document()
        self._write_repository()
        result = validate_repository(self.root, event_name="push")
        self.assertEqual(result["lifecycle_state"], "idle")
        self.assertIsNone(result["active_slice"])
        self.assertEqual(result["last_completed"]["pull_request"], 32)

    def test_idle_rejects_active_slice_and_active_state_rejects_null(self) -> None:
        idle = self._valid_idle_document()
        idle["active_slice"] = self._valid_active_document()["active_slice"]
        self.document = idle
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "active_slice must be null"):
            validate_repository(self.root)

        active = self._valid_active_document()
        active["active_slice"] = None
        self.document = active
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "active_slice"):
            validate_repository(self.root)

    def test_schema_and_last_completed_are_strict(self) -> None:
        cases = []
        wrong_version = self._valid_active_document()
        wrong_version["schema_version"] = 1
        cases.append(wrong_version)
        bad_sha = self._valid_active_document()
        bad_sha["last_completed"]["merge_commit"] = "abc"
        cases.append(bad_sha)
        bad_pr = self._valid_active_document()
        bad_pr["last_completed"]["pull_request"] = 0
        cases.append(bad_pr)
        for document in cases:
            self.document = document
            self._write_repository()
            with self.subTest(document=document):
                with self.assertRaises(DevelopmentContextError):
                    validate_repository(self.root)

    def test_review_requires_pull_request(self) -> None:
        self.document = self._valid_active_document("review")
        self.document["active_slice"]["pull_request"] = None
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "review state requires"):
            validate_repository(self.root)

    def test_branch_prefix_and_scope_remain_strict(self) -> None:
        self.document["active_slice"]["kind"] = "fix"
        self.document["active_slice"]["branch"] = "chore/wrong"
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "prefix"):
            validate_repository(self.root)

        self.document = self._valid_active_document()
        self.document["active_slice"]["write_scope"] = ["../outside"]
        self._write_repository()
        with self.assertRaises(DevelopmentContextError):
            validate_repository(self.root)

    def test_repository_markers_follow_lifecycle(self) -> None:
        (self.root / PROJECT_STATE_PATH).write_text(
            "<!-- uv-context-state: draft -->\n<!-- uv-last-completed: stage-5-dubbing-translation -->",
            encoding="utf-8",
        )
        with self.assertRaises(DevelopmentContextError):
            validate_repository(self.root)

        self.document = self._valid_idle_document()
        self._write_repository()
        (self.root / PROJECT_STATE_PATH).write_text(
            "<!-- uv-context-state: idle -->\n<!-- uv-active-slice: chore-agent-development-workflow -->",
            encoding="utf-8",
        )
        with self.assertRaises(DevelopmentContextError):
            validate_repository(self.root)

    def test_pull_request_draft_and_review_states_match_live_pr(self) -> None:
        for state, draft in (("draft", True), ("review", False)):
            self.document = self._valid_active_document(state)
            self._write_repository()
            validate_repository(
                self.root,
                event_name="pull_request",
                event_path=self._event_path(self._event(draft=draft)),
            )

    def test_pull_request_state_identity_and_body_fail_closed(self) -> None:
        self.document = self._valid_active_document("review")
        self._write_repository()
        wrong_draft = self._event(draft=True)
        with self.assertRaisesRegex(DevelopmentContextError, "lifecycle_state"):
            validate_repository(
                self.root,
                event_name="pull_request",
                event_path=self._event_path(wrong_draft),
            )

        bad_body = self._valid_pr_body().replace("## Changes", "## changes")
        with self.assertRaisesRegex(DevelopmentContextError, "## Changes"):
            validate_repository(
                self.root,
                event_name="pull_request",
                event_path=self._event_path(self._event(draft=False, body=bad_body)),
            )

    def test_idle_accepts_bounded_lifecycle_closure_pull_request(self) -> None:
        self.document = self._valid_idle_document()
        self._write_repository()
        result = validate_repository(
            self.root,
            event_name="pull_request",
            event_path=self._event_path(self._closure_event()),
        )
        self.assertEqual(result["lifecycle_state"], "idle")
        self.assertIsNone(result["active_slice"])

    def test_idle_rejects_ordinary_pull_request_event(self) -> None:
        self.document = self._valid_idle_document()
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "lifecycle-closure"):
            validate_repository(
                self.root,
                event_name="pull_request",
                event_path=self._event_path(self._event(draft=False)),
            )

    def test_lifecycle_closure_marker_and_pr_shape_fail_closed(self) -> None:
        self.document = self._valid_idle_document()
        self._write_repository()
        wrong_marker = self._valid_closure_pr_body().replace(
            "uv-lifecycle-closure: stage-5-dubbing-translation",
            "uv-lifecycle-closure: another-slice",
        )
        cases = (
            (self._closure_event(body=wrong_marker), "lifecycle-closure"),
            (self._closure_event(draft=True), "must not be draft"),
            (self._closure_event(head="fix/not-a-closure"), "chore/"),
            (self._closure_event(base="release"), "target main"),
        )
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(DevelopmentContextError, message):
                    validate_repository(
                        self.root,
                        event_name="pull_request",
                        event_path=self._event_path(payload),
                    )

    def test_review_rejects_placeholders_but_draft_allows_them(self) -> None:
        body = self._valid_pr_body().replace("Close Stage 5 correctness gaps.", "TODO")
        self.document = self._valid_active_document("draft")
        self._write_repository()
        validate_repository(
            self.root,
            event_name="pull_request",
            event_path=self._event_path(self._event(draft=True, body=body)),
        )
        self.document = self._valid_active_document("review")
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "placeholder"):
            validate_repository(
                self.root,
                event_name="pull_request",
                event_path=self._event_path(self._event(draft=False, body=body)),
            )

    def test_duplicate_json_keys_fail(self) -> None:
        path = self.root / ACTIVE_SLICE_PATH
        path.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
        with self.assertRaisesRegex(DevelopmentContextError, "duplicate JSON key"):
            validate_repository(self.root)

    def test_close_context_transitions_review_to_idle(self) -> None:
        self.document = self._valid_active_document("review")
        self._write_repository()
        result = close_context(
            self.root,
            pull_request=27,
            merge_commit="1" * 40,
        )
        self.assertEqual(result["lifecycle_state"], "idle")
        self.assertIsNone(result["active_slice"])
        self.assertEqual(result["last_completed"]["id"], "chore-agent-development-workflow")
        state_text = (self.root / PROJECT_STATE_PATH).read_text(encoding="utf-8")
        self.assertIn("<!-- uv-context-state: idle -->", state_text)
        self.assertIn("<!-- uv-last-completed: chore-agent-development-workflow -->", state_text)

    def test_close_context_rejects_nonreview_or_wrong_pr(self) -> None:
        with self.assertRaisesRegex(DevelopmentContextError, "only review"):
            close_context(self.root, pull_request=27, merge_commit="1" * 40)
        self.document = self._valid_active_document("review")
        self._write_repository()
        with self.assertRaisesRegex(DevelopmentContextError, "does not match"):
            close_context(self.root, pull_request=28, merge_commit="1" * 40)


if __name__ == "__main__":
    unittest.main()
