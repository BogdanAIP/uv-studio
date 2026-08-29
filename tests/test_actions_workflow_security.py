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
BOOL_TAG = "tag:yaml.org,2002:bool"


class WorkflowPolicyError(ValueError):
    """Raised when a maintained workflow cannot be proven to satisfy policy."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant with workflow-compatible booleans and unique keys."""


# PyYAML's default YAML-1.1 resolver treats on/off/yes/no as booleans, while
# GitHub workflow syntax relies on words such as `on` as ordinary strings.
# Copy the resolver table, remove the broad bool resolver and re-add only the
# true/false literals used by workflow inputs such as persist-credentials.
_UniqueKeySafeLoader.yaml_implicit_resolvers = {
    first: [
        (tag, resolver)
        for tag, resolver in resolvers
        if tag != BOOL_TAG
    ]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_UniqueKeySafeLoader.add_implicit_resolver(
    BOOL_TAG,
    re.compile(r"^(?:true|false)$", re.IGNORECASE),
    list("tTfF"),
)


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "expected a mapping node", node.start_mark)

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
    return sorted(
        path
        for path in WORKFLOW_DIR.iterdir()
        if path.is_file() and path.suffix.casefold() in {".yml", ".yaml"}
    )


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


def _normalize_checkout_inputs(
    name: str,
    job_name: str,
    value: Any,
) -> dict[str, Any]:
    mapping = _require_mapping(value, f"{name} job {job_name} checkout with")
    normalized: dict[str, Any] = {}
    original_keys: dict[str, str] = {}
    for raw_key, raw_value in mapping.items():
        if not isinstance(raw_key, str):
            raise WorkflowPolicyError(
                f"{name} job {job_name} checkout with input names must be strings"
            )
        key = raw_key.casefold()
        if key in normalized:
            raise WorkflowPolicyError(
                f"{name} job {job_name} checkout with contains case-insensitive duplicate "
                f"input keys {original_keys[key]!r} and {raw_key!r}"
            )
        normalized[key] = raw_value
        original_keys[key] = raw_key
    return normalized


def _validate_permission_value(
    name: str,
    value: Any,
    *,
    context: str,
    allow_contents_write: bool,
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
        if level == "write" and not (allow_contents_write and scope == "contents"):
            raise WorkflowPolicyError(f"{name} {context} must not grant {scope}: write")


def _job_writes_contents(job: Mapping[str, Any]) -> bool:
    permissions = job.get("permissions")
    return isinstance(permissions, Mapping) and permissions.get("contents") == "write"


def _normalize_action_use(value: str) -> str:
    return value.casefold()


def _validate_action_use(name: str, value: Any, *, context: str) -> bool:
    if not isinstance(value, str):
        raise WorkflowPolicyError(f"{name} {context} uses value must be a string")

    normalized = _normalize_action_use(value)
    if normalized.startswith("./"):
        return False
    if normalized.startswith("docker://"):
        raise WorkflowPolicyError(
            f"{name} {context} uses Docker action without an approved immutable policy: {value}"
        )

    action, separator, ref = normalized.rpartition("@")
    if separator != "@" or "/" not in action or not FULL_COMMIT_SHA.fullmatch(ref):
        raise WorkflowPolicyError(
            f"{name} uses floating or malformed remote Action/workflow: {value}"
        )
    return True


def _validate_workflow_security(name: str, text: str) -> None:
    workflow = _load_workflow(name, text)
    writer_workflow = name == APPROVED_WRITER

    root_permissions = _require_mapping(
        workflow.get("permissions"),
        f"{name} top-level permissions",
    )
    if root_permissions.get("contents") != "read":
        raise WorkflowPolicyError(f"{name} top-level contents permission must be read")
    _validate_permission_value(
        name,
        root_permissions,
        context="top-level",
        allow_contents_write=False,
    )

    jobs = _require_mapping(workflow.get("jobs"), f"{name} jobs")
    if not jobs:
        raise WorkflowPolicyError(f"{name} must define at least one job")

    remote_use_seen = 0
    checkout_seen = 0
    write_jobs = 0
    writer_checkout_seen = 0

    for job_name, raw_job in jobs.items():
        if not isinstance(job_name, str):
            raise WorkflowPolicyError(f"{name} job identifiers must be strings")
        job = _require_mapping(raw_job, f"{name} job {job_name}")

        if "permissions" in job:
            _validate_permission_value(
                name,
                job["permissions"],
                context=f"job {job_name}",
                allow_contents_write=writer_workflow,
            )

        job_writes_contents = _job_writes_contents(job)
        if job_writes_contents:
            write_jobs += 1

        if "uses" in job:
            if _validate_action_use(name, job["uses"], context=f"job {job_name}"):
                remote_use_seen += 1

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
                remote_use_seen += 1

            if not isinstance(use_value, str):
                continue
            normalized_use = _normalize_action_use(use_value)
            if not normalized_use.startswith("actions/checkout@"):
                continue

            checkout_seen += 1
            if job_writes_contents:
                writer_checkout_seen += 1
            with_mapping = _normalize_checkout_inputs(
                name,
                job_name,
                step.get("with"),
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
            expected_persist = job_writes_contents
            if actual_persist is not expected_persist:
                expected_text = "true" if expected_persist else "false"
                raise WorkflowPolicyError(
                    f"{name} checkout must set with.persist-credentials: {expected_text}"
                )

    if writer_workflow:
        if write_jobs != 1:
            raise WorkflowPolicyError(
                f"{name} must grant contents: write to exactly one job"
            )
        if writer_checkout_seen == 0:
            raise WorkflowPolicyError(
                f"{name} writer job must contain an authenticated checkout"
            )
    elif write_jobs:
        raise WorkflowPolicyError(f"{name} must not define a write-authorized job")

    if remote_use_seen == 0:
        raise WorkflowPolicyError(f"{name} has no remote Action/workflow use to guard")
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

    def test_github_workflow_words_remain_strings_while_true_false_are_boolean(self) -> None:
        workflow = f"""\
on: push
permissions:
  contents: read
jobs:
  on:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
"""
        parsed = _load_workflow("ci.yml", workflow)
        self.assertIn("on", parsed)
        self.assertIn("on", _require_mapping(parsed["jobs"], "jobs"))
        _validate_workflow_security("ci.yml", workflow)

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

    def test_checkout_input_keys_cannot_collide_case_insensitively(self) -> None:
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
          PERSIST-CREDENTIALS: true
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "case-insensitive duplicate input keys"):
            _validate_workflow_security("ci.yml", workflow)

    def test_flow_style_checkout_with_is_structurally_validated(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe: {{runs-on: ubuntu-latest, steps: [{{uses: actions/checkout@{'1' * 40}, with: {{persist-credentials: false}}}}]}}
"""
        _validate_workflow_security("ci.yml", workflow)

    def test_flow_style_remote_action_still_requires_full_sha(self) -> None:
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

    def test_third_party_remote_action_also_requires_full_sha(self) -> None:
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
      - uses: example/action@v1
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "floating or malformed"):
            _validate_workflow_security("ci.yml", workflow)

    def test_docker_action_is_rejected_without_explicit_immutable_policy(self) -> None:
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
      - uses: docker://alpine:latest
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "Docker action"):
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

    def test_writer_requires_top_level_read_and_one_write_job(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  vendor:
    permissions:
      contents: write
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: true
"""
        _validate_workflow_security(APPROVED_WRITER, workflow)

        top_level_write = workflow.replace("contents: read", "contents: write", 1)
        with self.assertRaisesRegex(WorkflowPolicyError, "top-level contents permission must be read"):
            _validate_workflow_security(APPROVED_WRITER, top_level_write)

    def test_writer_rejects_second_write_job(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  vendor:
    permissions: {{contents: write}}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with: {{persist-credentials: true}}
  extra:
    permissions: {{contents: write}}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'2' * 40}
        with: {{persist-credentials: true}}
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "exactly one job"):
            _validate_workflow_security(APPROVED_WRITER, workflow)

    def test_writer_read_only_job_cannot_persist_credentials(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  vendor:
    permissions: {{contents: write}}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'1' * 40}
        with: {{persist-credentials: true}}
  inspect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'2' * 40}
        with: {{persist-credentials: true}}
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "persist-credentials: false"):
            _validate_workflow_security(APPROVED_WRITER, workflow)

    def test_writer_job_must_contain_authenticated_checkout(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  vendor:
    permissions: {{contents: write}}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@{'1' * 40}
  inspect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{'2' * 40}
        with: {{persist-credentials: false}}
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "writer job must contain"):
            _validate_workflow_security(APPROVED_WRITER, workflow)


if __name__ == "__main__":
    unittest.main()