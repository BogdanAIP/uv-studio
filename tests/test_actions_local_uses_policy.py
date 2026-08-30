from __future__ import annotations

import unittest
from typing import Any

import test_actions_workflow_security as workflow_security


class LocalUsesPolicyError(ValueError):
    """Raised when a maintained workflow delegates to unscanned repository-local code."""


def _reject_local_use(name: str, value: Any, *, context: str) -> None:
    if isinstance(value, str) and value.startswith("./"):
        raise LocalUsesPolicyError(
            f"{name} {context} must not use repository-local Action/reusable workflow {value!r}; "
            "local uses are denied until a transitive immutable-uses policy is implemented"
        )


def _validate_no_local_uses(name: str, text: str) -> None:
    workflow = workflow_security._load_workflow(name, text)
    jobs = workflow_security._require_mapping(workflow.get("jobs"), f"{name} jobs")

    for job_name, raw_job in jobs.items():
        if not isinstance(job_name, str):
            raise LocalUsesPolicyError(f"{name} job identifiers must be strings")
        job = workflow_security._require_mapping(raw_job, f"{name} job {job_name}")

        if "uses" in job:
            _reject_local_use(name, job["uses"], context=f"job {job_name}")

        raw_steps = job.get("steps")
        if raw_steps is None:
            continue
        if not isinstance(raw_steps, list):
            raise LocalUsesPolicyError(f"{name} job {job_name} steps must be a sequence")

        for index, raw_step in enumerate(raw_steps):
            step = workflow_security._require_mapping(
                raw_step,
                f"{name} job {job_name} step {index}",
            )
            if "uses" in step:
                _reject_local_use(
                    name,
                    step["uses"],
                    context=f"job {job_name} step {index}",
                )


class ActionsLocalUsesPolicyTests(unittest.TestCase):
    def test_maintained_workflows_do_not_delegate_to_unscanned_local_uses(self) -> None:
        paths = workflow_security._workflow_paths()
        self.assertTrue(paths, "No maintained GitHub Actions workflows were found")
        for path in paths:
            with self.subTest(path=path.name):
                _validate_no_local_uses(path.name, path.read_text(encoding="utf-8"))

    def test_local_composite_action_call_is_rejected(self) -> None:
        workflow = """\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: ./.github/actions/example
"""
        with self.assertRaisesRegex(LocalUsesPolicyError, "repository-local"):
            _validate_no_local_uses("ci.yml", workflow)

    def test_local_reusable_workflow_call_is_rejected(self) -> None:
        workflow = """\
permissions:
  contents: read
jobs:
  delegate:
    uses: ./.github/workflows/delegate.yml
"""
        with self.assertRaisesRegex(LocalUsesPolicyError, "repository-local"):
            _validate_no_local_uses("ci.yml", workflow)


if __name__ == "__main__":
    unittest.main()
