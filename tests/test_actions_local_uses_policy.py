from __future__ import annotations

import unittest
from typing import Any

import test_actions_workflow_security as workflow_security


ALLOWED_STEP_USES = frozenset(
    {
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    }
)


class TransitiveUsesPolicyError(ValueError):
    """Raised when a workflow delegates execution outside the reviewed direct-use set."""


def _validate_job_use(name: str, value: Any, *, context: str) -> None:
    if not isinstance(value, str):
        raise TransitiveUsesPolicyError(f"{name} {context} uses value must be a string")
    raise TransitiveUsesPolicyError(
        f"{name} {context} uses {value!r}, but no reusable workflow is approved; "
        "reusable workflows require a separate reviewed transitive immutable-uses policy"
    )


def _validate_step_use(name: str, value: Any, *, context: str) -> None:
    if not isinstance(value, str):
        raise TransitiveUsesPolicyError(f"{name} {context} uses value must be a string")

    normalized = value.casefold()
    if normalized.startswith("./"):
        raise TransitiveUsesPolicyError(
            f"{name} {context} must not use repository-local Action {value!r}; "
            "local Actions are denied until a transitive immutable-uses policy is implemented"
        )
    if normalized not in ALLOWED_STEP_USES:
        raise TransitiveUsesPolicyError(
            f"{name} {context} uses unapproved remote Action {value!r}; "
            "new Actions require explicit transitive review before entering the allowlist"
        )


def _validate_reviewed_uses_boundary(name: str, text: str) -> None:
    workflow = workflow_security._load_workflow(name, text)
    jobs = workflow_security._require_mapping(workflow.get("jobs"), f"{name} jobs")

    for job_name, raw_job in jobs.items():
        if not isinstance(job_name, str):
            raise TransitiveUsesPolicyError(f"{name} job identifiers must be strings")
        job = workflow_security._require_mapping(raw_job, f"{name} job {job_name}")

        if "uses" in job:
            _validate_job_use(name, job["uses"], context=f"job {job_name}")

        raw_steps = job.get("steps")
        if raw_steps is None:
            continue
        if not isinstance(raw_steps, list):
            raise TransitiveUsesPolicyError(f"{name} job {job_name} steps must be a sequence")

        for index, raw_step in enumerate(raw_steps):
            step = workflow_security._require_mapping(
                raw_step,
                f"{name} job {job_name} step {index}",
            )
            if "uses" in step:
                _validate_step_use(
                    name,
                    step["uses"],
                    context=f"job {job_name} step {index}",
                )


class ActionsTransitiveUsesPolicyTests(unittest.TestCase):
    def test_maintained_workflows_use_only_reviewed_direct_actions(self) -> None:
        paths = workflow_security._workflow_paths()
        self.assertTrue(paths, "No maintained GitHub Actions workflows were found")
        for path in paths:
            with self.subTest(path=path.name):
                _validate_reviewed_uses_boundary(path.name, path.read_text(encoding="utf-8"))

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
        with self.assertRaisesRegex(TransitiveUsesPolicyError, "repository-local"):
            _validate_reviewed_uses_boundary("ci.yml", workflow)

    def test_local_reusable_workflow_call_is_rejected(self) -> None:
        workflow = """\
permissions:
  contents: read
jobs:
  delegate:
    uses: ./.github/workflows/delegate.yml
"""
        with self.assertRaisesRegex(TransitiveUsesPolicyError, "no reusable workflow is approved"):
            _validate_reviewed_uses_boundary("ci.yml", workflow)

    def test_unreviewed_remote_composite_action_is_rejected_even_when_sha_pinned(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: example/composite@{'1' * 40}
"""
        with self.assertRaisesRegex(TransitiveUsesPolicyError, "unapproved remote Action"):
            _validate_reviewed_uses_boundary("ci.yml", workflow)

    def test_known_node_action_is_allowed_case_insensitively(self) -> None:
        workflow = """\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: AcTiOnS/ChEcKoUt@11D5960A326750D5838078E36CF38B85AF677262
        with:
          persist-credentials: false
"""
        _validate_reviewed_uses_boundary("ci.yml", workflow)


if __name__ == "__main__":
    unittest.main()
