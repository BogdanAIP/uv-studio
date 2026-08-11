from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
        self.document = self._valid_document()
        self._write_repository()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _valid_document() -> dict:
        return {
            "schema_version": 1,
            "active_slice": {
                "id": "chore-agent-development-workflow",
                "kind": "chore",
                "roadmap_stage": "stage-4",
                "goal": "Make development state explicit and CI-checked.",
                "base_branch": "main",
                "branch": "chore/agent-development-workflow",
                "pull_request": None,
                "phase": "draft",
                "write_scope": [
                    "AGENTS.md",
                    ".github/workflows/ci.yml",
                    "project-context/**",
                ],
            },
            "handoff": {
                "next_slice_id": "stage-4-range-continuity-brief",
                "next_task_file": NEXT_TASK_PATH,
            },
            "coordination": {
                "integration_owner": "coordinator",
                "context_owner": "coordinator",
                "parallel_write_policy": "disjoint_paths",
            },
            "required_checks": sorted(REQUIRED_CHECKS),
        }

    def _write_repository(self) -> None:
        active_path = self.root / ACTIVE_SLICE_PATH
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(json.dumps(self.document), encoding="utf-8")
        (self.root / PROJECT_STATE_PATH).write_text(
            "# State\n\n<!-- uv-active-slice: chore-agent-development-workflow -->\n",
            encoding="utf-8",
        )
        (self.root / NEXT_TASK_PATH).write_text(
            "# Next\n\n<!-- uv-next-slice: stage-4-range-continuity-brief -->\n",
            encoding="utf-8",
        )

    def _event(self, *, draft: bool = True, body: str | None = None) -> dict:
        return {
            "number": 27,
            "pull_request": {
                "draft": draft,
                "body": body if body is not None else self._valid_pr_body(),
                "head": {"ref": "chore/agent-development-workflow"},
                "base": {"ref": "main"},
            },
        }

    @staticmethod
    def _valid_pr_body() -> str:
        return "\n".join(
            (
                "<!-- uv-active-slice: chore-agent-development-workflow -->",
                "<!-- uv-next-slice: stage-4-range-continuity-brief -->",
                "",
                "## Goal",
                "Make handoffs deterministic.",
                "",
                "## Changes",
                "Add a strict validator.",
                "",
                "## Verification",
                "Focused tests pass.",
                "",
                "## Architecture impact",
                "Repository state becomes machine-readable.",
                "",
                "## Known limitations",
                "GitHub remains the source of live PR state.",
                "",
                "## Next task",
                "Build the continuity brief.",
            )
        )

    def _write_event(self, payload: dict | str) -> Path:
        event_path = self.root / "event.json"
        event_path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload),
            encoding="utf-8",
        )
        return event_path

    def test_valid_repository_passes_for_local_and_push(self) -> None:
        local = validate_repository(self.root)
        pushed = validate_repository(self.root, event_name="push")
        self.assertEqual(local["active_slice"]["id"], "chore-agent-development-workflow")
        self.assertEqual(local, pushed)

    def test_duplicate_json_key_fails_at_any_depth(self) -> None:
        path = self.root / ACTIVE_SLICE_PATH
        raw = path.read_text(encoding="utf-8")
        raw = raw.replace(
            '"goal": "Make development state explicit and CI-checked."',
            '"goal": "first", "goal": "second"',
        )
        path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(DevelopmentContextError, "duplicate JSON key"):
            validate_repository(self.root)

    def test_nonstandard_json_constants_fail(self) -> None:
        path = self.root / ACTIVE_SLICE_PATH
        raw = path.read_text(encoding="utf-8").replace(
            '"schema_version": 1', '"schema_version": NaN'
        )
        path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(DevelopmentContextError, "non-standard JSON"):
            validate_repository(self.root)

    def test_unknown_and_missing_schema_keys_fail_closed(self) -> None:
        scenarios = []
        unknown = json.loads(json.dumps(self.document))
        unknown["active_slice"]["provider"] = "forbidden"
        scenarios.append(unknown)
        missing = json.loads(json.dumps(self.document))
        del missing["coordination"]["context_owner"]
        scenarios.append(missing)

        for document in scenarios:
            with self.subTest(keys=document.keys()):
                self.document = document
                self._write_repository()
                with self.assertRaisesRegex(DevelopmentContextError, "invalid keys"):
                    validate_repository(self.root)

    def test_schema_version_ids_enums_and_pull_request_are_strict(self) -> None:
        mutations = (
            ("schema_version", True),
            ("active_slice.id", "Bad_ID"),
            ("active_slice.kind", "feature"),
            ("active_slice.kind", []),
            ("active_slice.roadmap_stage", "Stage 4"),
            ("active_slice.pull_request", True),
            ("active_slice.pull_request", 0),
            ("active_slice.phase", "ready"),
            ("active_slice.phase", {}),
        )
        for field, invalid in mutations:
            document = self._valid_document()
            target = document
            parts = field.split(".")
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = invalid
            with self.subTest(field=field, value=invalid):
                self.document = document
                self._write_repository()
                with self.assertRaises(DevelopmentContextError):
                    validate_repository(self.root)

    def test_branch_prefix_must_match_slice_kind(self) -> None:
        cases = (
            ("stage", "stage-4/continuity", True),
            ("stage", "stage-x/continuity", False),
            ("fix", "chore/not-a-fix", False),
            ("research", "research/provider-contract", True),
        )
        for kind, branch, valid in cases:
            self.document = self._valid_document()
            self.document["active_slice"]["kind"] = kind
            self.document["active_slice"]["branch"] = branch
            self._write_repository()
            with self.subTest(kind=kind, branch=branch):
                if valid:
                    validate_repository(self.root)
                else:
                    with self.assertRaisesRegex(DevelopmentContextError, "prefix"):
                        validate_repository(self.root)

    def test_write_scope_rejects_duplicates_and_nonportable_paths(self) -> None:
        invalid_scopes = (
            ["tools/**", "tools/**"],
            ["../outside"],
            ["tools\\script.py"],
            ["C:/outside"],
            ["/absolute"],
            ["tools//script.py"],
            ["tools/./script.py"],
            ["tools/"],
            ["tools/file:name.py"],
        )
        for scope in invalid_scopes:
            self.document = self._valid_document()
            self.document["active_slice"]["write_scope"] = scope
            self._write_repository()
            with self.subTest(scope=scope):
                with self.assertRaises(DevelopmentContextError):
                    validate_repository(self.root)

    def test_required_checks_must_be_unique_and_exact(self) -> None:
        invalid_sets = (
            ["development-context"],
            sorted(REQUIRED_CHECKS) + ["unexpected"],
            sorted(REQUIRED_CHECKS) + ["development-context"],
        )
        for checks in invalid_sets:
            self.document = self._valid_document()
            self.document["required_checks"] = checks
            self._write_repository()
            with self.subTest(checks=checks):
                with self.assertRaises(DevelopmentContextError):
                    validate_repository(self.root)

    def test_handoff_and_coordination_values_are_fixed(self) -> None:
        documents = []
        wrong_handoff = self._valid_document()
        wrong_handoff["handoff"]["next_task_file"] = "docs/NEXT.md"
        documents.append(wrong_handoff)
        wrong_owner = self._valid_document()
        wrong_owner["coordination"]["context_owner"] = "worker"
        documents.append(wrong_owner)
        wrong_policy = self._valid_document()
        wrong_policy["coordination"]["parallel_write_policy"] = "shared"
        documents.append(wrong_policy)

        for document in documents:
            self.document = document
            self._write_repository()
            with self.assertRaises(DevelopmentContextError):
                validate_repository(self.root)

    def test_repository_markers_must_match_and_appear_once(self) -> None:
        marker_cases = (
            (
                PROJECT_STATE_PATH,
                "<!-- uv-active-slice: wrong -->",
            ),
            (
                NEXT_TASK_PATH,
                "<!-- uv-next-slice: wrong -->",
            ),
            (
                PROJECT_STATE_PATH,
                "<!-- uv-active-slice: chore-agent-development-workflow -->\n" * 2,
            ),
        )
        for relative_path, contents in marker_cases:
            self._write_repository()
            (self.root / relative_path).write_text(contents, encoding="utf-8")
            with self.subTest(path=relative_path, contents=contents):
                with self.assertRaisesRegex(DevelopmentContextError, "exactly one marker"):
                    validate_repository(self.root)

    def test_matching_pull_request_event_passes(self) -> None:
        self.document["active_slice"]["pull_request"] = 27
        self._write_repository()
        event_path = self._write_event(self._event())
        validate_repository(
            self.root,
            event_name="pull_request",
            event_path=event_path,
        )

    def test_pull_request_event_requires_configured_matching_identity(self) -> None:
        scenarios = []
        null_number = self._valid_document()
        scenarios.append((null_number, self._event()))
        wrong_number = self._valid_document()
        wrong_number["active_slice"]["pull_request"] = 28
        scenarios.append((wrong_number, self._event()))
        wrong_head = self._valid_document()
        wrong_head["active_slice"]["pull_request"] = 27
        head_event = self._event()
        head_event["pull_request"]["head"]["ref"] = "chore/other"
        scenarios.append((wrong_head, head_event))
        wrong_base = self._valid_document()
        wrong_base["active_slice"]["pull_request"] = 27
        base_event = self._event()
        base_event["pull_request"]["base"]["ref"] = "release"
        scenarios.append((wrong_base, base_event))

        for document, event in scenarios:
            self.document = document
            self._write_repository()
            event_path = self._write_event(event)
            with self.subTest(document=document["active_slice"], event=event):
                with self.assertRaises(DevelopmentContextError):
                    validate_repository(
                        self.root,
                        event_name="pull_request",
                        event_path=event_path,
                    )

    def test_pull_request_draft_state_must_match_phase(self) -> None:
        cases = (
            ("draft", True, True),
            ("draft", False, False),
            ("review", False, True),
            ("review", True, False),
        )
        for phase, draft, valid in cases:
            self.document = self._valid_document()
            self.document["active_slice"]["pull_request"] = 27
            self.document["active_slice"]["phase"] = phase
            self._write_repository()
            event_path = self._write_event(self._event(draft=draft))
            with self.subTest(phase=phase, draft=draft):
                if valid:
                    validate_repository(
                        self.root,
                        event_name="pull_request",
                        event_path=event_path,
                    )
                else:
                    with self.assertRaisesRegex(DevelopmentContextError, "phase"):
                        validate_repository(
                            self.root,
                            event_name="pull_request",
                            event_path=event_path,
                        )

    def test_pr_body_requires_markers_sections_order_and_content(self) -> None:
        valid_body = self._valid_pr_body()
        cases = (
            valid_body.replace(
                "<!-- uv-active-slice: chore-agent-development-workflow -->",
                "<!-- uv-active-slice: wrong -->",
            ),
            valid_body.replace("## Verification", "## verification"),
            valid_body.replace("## Changes\nAdd a strict validator.", "## Changes\n<!-- none -->"),
            valid_body.replace(
                "## Goal\nMake handoffs deterministic.\n\n## Changes\nAdd a strict validator.",
                "## Changes\nAdd a strict validator.\n\n## Goal\nMake handoffs deterministic.",
            ),
        )
        self.document["active_slice"]["pull_request"] = 27
        self._write_repository()
        for body in cases:
            event_path = self._write_event(self._event(body=body))
            with self.subTest(body=body):
                with self.assertRaises(DevelopmentContextError):
                    validate_repository(
                        self.root,
                        event_name="pull_request",
                        event_path=event_path,
                    )

    def test_review_phase_rejects_placeholders_but_draft_allows_them(self) -> None:
        placeholders = (
            "TODO",
            "TBD",
            "Still to do",
            "replace-with-active-slice-id",
        )
        for phase in ("draft", "review"):
            for placeholder in placeholders:
                self.document = self._valid_document()
                self.document["active_slice"]["pull_request"] = 27
                self.document["active_slice"]["phase"] = phase
                self._write_repository()
                body = self._valid_pr_body().replace(
                    "Build the continuity brief.", placeholder
                )
                event_path = self._write_event(
                    self._event(draft=phase == "draft", body=body)
                )
                with self.subTest(phase=phase, placeholder=placeholder):
                    if phase == "draft":
                        validate_repository(
                            self.root,
                            event_name="pull_request",
                            event_path=event_path,
                        )
                    else:
                        with self.assertRaisesRegex(
                            DevelopmentContextError, "placeholder"
                        ):
                            validate_repository(
                                self.root,
                                event_name="pull_request",
                                event_path=event_path,
                            )

    def test_review_phase_allows_replace_as_domain_language(self) -> None:
        self.document["active_slice"]["pull_request"] = 27
        self.document["active_slice"]["phase"] = "review"
        self._write_repository()
        body = self._valid_pr_body().replace(
            "Build the continuity brief.",
            "Replace the exact interval through video.replace_range.",
        )
        event_path = self._write_event(self._event(draft=False, body=body))
        validate_repository(
            self.root,
            event_name="pull_request",
            event_path=event_path,
        )

    def test_pull_request_event_json_rejects_duplicate_keys(self) -> None:
        self.document["active_slice"]["pull_request"] = 27
        self._write_repository()
        event_path = self._write_event(
            '{"number":27,"number":28,"pull_request":{}}'
        )
        with self.assertRaisesRegex(DevelopmentContextError, "duplicate JSON key"):
            validate_repository(
                self.root,
                event_name="pull_request",
                event_path=event_path,
            )

    def test_unsupported_event_name_and_missing_event_path_fail(self) -> None:
        with self.assertRaisesRegex(DevelopmentContextError, "unsupported"):
            validate_repository(self.root, event_name="schedule")
        with self.assertRaisesRegex(DevelopmentContextError, "GITHUB_EVENT_PATH"):
            validate_repository(self.root, event_name="pull_request")


if __name__ == "__main__":
    unittest.main()
