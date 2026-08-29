from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
APPROVED_WRITER = "vendor-videoclaw.yml"
USES_VALUE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.MULTILINE)
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
CONTENTS_WRITE = re.compile(
    r"^\s*contents:\s*['\"]?write['\"]?\s*(?:#.*)?$",
    re.MULTILINE,
)
WRITE_ALL = re.compile(r"^\s*permissions:\s*['\"]?write-all['\"]?\s*(?:#.*)?$", re.MULTILINE)


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")))


def _step_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)-\s+", line)
        if match:
            starts.append((index, len(match.group(1))))

    blocks: list[str] = []
    for position, (start, indent) in enumerate(starts):
        end = len(lines)
        for candidate_start, candidate_indent in starts[position + 1 :]:
            if candidate_indent == indent:
                end = candidate_start
                break
        blocks.append("\n".join(lines[start:end]))
    return blocks


def _uses_values(text: str) -> list[str]:
    return [value.strip("'\"") for value in USES_VALUE.findall(text)]


class ActionsWorkflowSecurityTests(unittest.TestCase):
    def test_first_party_actions_are_pinned_to_full_commit_shas(self) -> None:
        paths = _workflow_paths()
        self.assertTrue(paths, "No maintained GitHub Actions workflows were found")

        seen = 0
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for value in _uses_values(text):
                if not value.startswith("actions/"):
                    continue
                seen += 1
                action, separator, ref = value.rpartition("@")
                self.assertEqual(
                    separator,
                    "@",
                    f"{path.relative_to(ROOT)} has malformed first-party Action use: {value}",
                )
                self.assertTrue(
                    FULL_COMMIT_SHA.fullmatch(ref),
                    f"{path.relative_to(ROOT)} uses floating {action}@{ref}",
                )
        self.assertGreater(seen, 0, "No first-party actions/* uses were found to guard")

    def test_write_permission_is_limited_to_vendoring_writer(self) -> None:
        paths = _workflow_paths()
        writers = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(WRITE_ALL.search(text), f"{path.relative_to(ROOT)} must not use permissions: write-all")
            if CONTENTS_WRITE.search(text):
                writers.append(path.name)
        self.assertEqual(writers, [APPROVED_WRITER])

        for path in paths:
            text = path.read_text(encoding="utf-8")
            expected = (
                "permissions:\n  contents: write"
                if path.name == APPROVED_WRITER
                else "permissions:\n  contents: read"
            )
            self.assertIn(expected, text, f"Unexpected permissions in {path.relative_to(ROOT)}")

    def test_checkout_credentials_are_not_persisted_in_read_only_workflows(self) -> None:
        for path in _workflow_paths():
            text = path.read_text(encoding="utf-8")
            checkout_steps = [
                block
                for block in _step_blocks(text)
                if re.search(r"uses:\s*['\"]?actions/checkout@", block)
            ]
            self.assertTrue(
                checkout_steps,
                f"{path.relative_to(ROOT)} has no checkout step for credential-policy validation",
            )

            expected_value = "true" if path.name == APPROVED_WRITER else "false"
            expected_pattern = re.compile(
                rf"^\s*persist-credentials:\s*{expected_value}\s*(?:#.*)?$",
                re.MULTILINE,
            )
            for step in checkout_steps:
                self.assertRegex(
                    step,
                    expected_pattern,
                    (
                        f"{path.relative_to(ROOT)} checkout must set "
                        f"persist-credentials: {expected_value}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
