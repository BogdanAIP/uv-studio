from __future__ import annotations

import re
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.resolver import BaseResolver


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
APPROVED_WRITER = "vendor-videoclaw.yml"
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class WorkflowPolicyError(ValueError):
    """Raised when a maintained workflow cannot be proven to satisfy policy."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that fails closed on duplicate YAML mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "expected a mapping node", node.start_mark)

    # Resolve YAML merge keys before duplicate detection. Overrides introduced
    # through merge syntax are rejected rather than silently changing policy.
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")))


def _load_workflow(name: str, text: str) -> Mapping[str, Any]:
    try:
        document = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise WorkflowPolicyError(f"{name} is not unambiguous safe YAML: {exc}") from exc
    if not isinstance(document, Mapping):
        raise WorkflowPolicyError(f"{name} workflow root must be a mapping")
    return document


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkflowPolicyError(f"{label} must be a mapping")
    return value


def _validate_permission_value(
    name: str,
    value: Any,
    *,
    context: str,
    writer_workflow: bool,
) -> None:
    if isinstance(value, str):
        if value == "write-all":
            raise WorkflowPolicyError(f"{name} {context} must not use permissions: write-all")
        if value == "read-all":
            return
        raise WorkflowPolicyError(f"{name} {context} has unsupported permissions scalar: {value!r}")

    mapping = _require_mapping(value, f"{name} {context} permissions")
    for scope, level in mapping.items():
        if not isinstance(scope, str) or not isinstance(level, str):
            raise WorkflowPolicyError(
                f"{name} {context} permissions must use string scope/value pairs"
            )
        if level not in {"read", "write", "none"}:
            raise WorkflowPolicyError(
                f"{name} {context} has unsupported {scope} permission: {level!r}"
            )
        if level == "write" and not (writer_workflow and scope == "contents"):
            raise WorkflowPolicyError(f"{name} {context} must not grant {scope}: write")


def _normalize_action_use(value: str) -> str:
    # GitHub repository identity is case-insensitive. Normalize the complete
    # owner/repository/ref string before classifying first-party Actions while
    # preserving the original value for human-facing error messages.
    return value.casefold()


def _validate_action_use(name: str, value: Any, *, context: str) -> bool:
    if not isinstance(value, str):
        raise WorkflowPolicyError(f"{name} {context} uses value must be a string")

    normalized = _normalize_action_use(value)
    if not normalized.startswith("actions/"):
        return False

    action, separator, ref = normalized.rpartition("@")
    if separator != "@" or not action or not FULL_COMMIT_SHA.fullmatch(ref):
        raise WorkflowPolicyError(
            f"{name} uses floating or malformed first-party Action: {value}"
        )
    return True


def _validate_workflow_security(name: str, text: str) -> None:
    workflow = _load_workflow(name, text)
    writer_workflow = name == APPROVED_WRITER

    root_permissions = _require_mapping(
        workflow.get("permissions"),
        f"{name} top-level permissions",
    )
    expected_contents = "write" if writer_workflow else "read"
    if root_permissions.get("contents") != expected_contents:
        raise WorkflowPolicyError(
            f"{name} top-level contents permission must be {expected_contents}"
        )
    _validate_permission_value(
        name,
        root_permissions,
        context="top-level",
        writer_workflow=writer_workflow,
    )

    jobs = _require_mapping(workflow.get("jobs"), f"{name} jobs")
    if not jobs:
        raise WorkflowPolicyError(f"{name} must define at least one job")

    first_party_seen = 0
    checkout_seen = 0
    expected_persist = writer_workflow

    for job_name, raw_job in jobs.items():
        if not isinstance(job_name, str):
            raise WorkflowPolicyError(f"{name} job identifiers must be strings")
        job = _require_mapping(raw_job, f"{name} job {job_name}")

        if "permissions" in job:
            _validate_permission_value(
                name,
                job["permissions"],
                context=f"job {job_name}",
                writer_workflow=writer_workflow,
            )

        if "uses" in job:
            if _validate_action_use(name, job["uses"], context=f"job {job_name}"):
                first_party_seen += 1

        raw_steps = job.get("steps")
        if raw_steps is None:
            continue
        if not isinstance(raw_steps, list):
            raise WorkflowPolicyError(f"{name} job {job_name} steps must be a sequence")

        for index, raw_step in enumerate(raw_steps):
            step = _require_mapping(raw_step, f"{name} job {job_name} step {index}")
            if "uses" not in step:
                continue

            use_value = step["uses"]
            if _validate_action_use(
                name,
                use_value,
                context=f"job {job_name} step {index}",
            ):
                first_party_seen += 1

            if not isinstance(use_value, str):
                continue
            normalized_use = _normalize_action_use(use_value)
            if not normalized_use.startswith("actions/checkout@"):
                continue

            checkout_seen += 1
            with_mapping = _require_mapping(
                step.get("with"),
                f"{name} job {job_name} checkout with",
            )
            if "persist-credentials" not in with_mapping:
                raise WorkflowPolicyError(
                    f"{name} checkout must explicitly set with.persist-credentials"
                )
            actual_persist = with_mapping["persist-credentials"]
            if type(actual_persist) is not bool:
                raise WorkflowPolicyError(
                    f"{name} checkout with.persist-credentials must be literal true or false"
                )
            if actual_persist is not expected_persist:
                expected_text = "true" if expected_persist else "false"
                raise WorkflowPolicyError(
                    f"{name} checkout must set with.persist-credentials: {expected_text}"
                )

    if first_party_seen == 0:
        raise WorkflowPolicyError(f"{name} has no first-party actions/* use to guard")
    if checkout_seen == 0:
        raise WorkflowPolicyError(
            f"{name} has no checkout step for credential-policy validation"
        )


class ActionsWorkflowSecurityTests(unittest.TestCase):
    def test_all_maintained_workflows_follow_security_policy(self) -> None:
        paths = _workflow_paths()
        self.assertTrue(paths, "No maintained GitHub Actions workflows were found")
        for path in paths:
            with self.subTest(path=path.name):
                _validate_workflow_security(path.name, path.read_text(encoding="utf-8"))

    def test_whole_job_flow_mapping_cannot_hide_write_authority(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  safe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
  hidden: {{runs-on: ubuntu-latest, permissions: {{contents: write}}, steps: [{{uses: actions/checkout@{'1' * 40}, with: {{persist-credentials: true}}}}]}}
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "must not grant contents: write"):
            _validate_workflow_security("ci.yml", workflow)

    def test_whole_job_flow_mapping_cannot_hide_persisted_checkout_token(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  hidden: {{runs-on: ubuntu-latest, steps: [{{uses: actions/checkout@{'1' * 40}, with: {{persist-credentials: true}}}}]}}
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "persist-credentials: false"):
            _validate_workflow_security("ci.yml", workflow)

    def test_checkout_credential_decoy_outside_with_is_rejected(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        env:
          persist-credentials: false
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "checkout with"):
            _validate_workflow_security("ci.yml", workflow)

    def test_flow_style_checkout_with_is_structurally_validated(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe: {{runs-on: ubuntu-latest, steps: [{{uses: actions/checkout@{'1' * 40}, with: {{persist-credentials: false}}}}]}}
"""
        _validate_workflow_security("ci.yml", workflow)

    def test_flow_style_first_party_action_still_requires_full_sha(self) -> None:
        workflow = """\
permissions: {contents: read}
jobs:
  probe: {runs-on: ubuntu-latest, steps: [{uses: actions/checkout@v4, with: {persist-credentials: false}}]}
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "floating or malformed"):
            _validate_workflow_security("ci.yml", workflow)

    def test_mixed_case_first_party_action_still_requires_full_sha(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
      - uses: AcTiOnS/setup-python@v5
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "floating or malformed"):
            _validate_workflow_security("ci.yml", workflow)

    def test_mixed_case_checkout_still_enforces_credential_policy(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
      - uses: aCtIoNs/ChEcKoUt@{'2' * 40}
        with:
          persist-credentials: true
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "persist-credentials: false"):
            _validate_workflow_security("ci.yml", workflow)

    def test_duplicate_yaml_keys_fail_closed(self) -> None:
        workflow = f"""\
permissions:
  contents: read
  contents: write
jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "duplicate key"):
            _validate_workflow_security("ci.yml", workflow)

    def test_read_only_job_level_write_permission_is_rejected(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-latest
    permissions: {{issues: write}}
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "must not grant issues: write"):
            _validate_workflow_security("ci.yml", workflow)


if __name__ == "__main__":
    unittest.main()
