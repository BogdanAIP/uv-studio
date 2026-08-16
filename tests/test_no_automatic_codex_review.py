from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GITHUB_CONFIG_ROOT = REPOSITORY_ROOT / ".github"
FORBIDDEN_CODE_REVIEW_TRIGGERS = (
    re.compile(r"@codex\b", re.IGNORECASE),
    re.compile(r"chatgpt-codex-connector", re.IGNORECASE),
    re.compile(r"\bcodex[ _-]+code[ _-]+review\b", re.IGNORECASE),
    re.compile(r"\bcodex[ _-]+review\b", re.IGNORECASE),
    re.compile(r"\bopenai/codex\b", re.IGNORECASE),
)


class NoAutomaticCodexReviewTests(unittest.TestCase):
    def test_github_configuration_does_not_trigger_codex_review(self) -> None:
        offending: list[str] = []
        for path in sorted(GITHUB_CONFIG_ROOT.rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in FORBIDDEN_CODE_REVIEW_TRIGGERS:
                if pattern.search(text):
                    relative = path.relative_to(REPOSITORY_ROOT).as_posix()
                    offending.append(f"{relative}: {pattern.pattern}")

        self.assertEqual(
            [],
            offending,
            "Automatic Codex review is excluded by D-040; remove GitHub-side Codex review triggers.",
        )


if __name__ == "__main__":
    unittest.main()
