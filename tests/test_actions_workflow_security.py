from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
APPROVED_WRITER = "vendor-videoclaw.yml"
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SIMPLE_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")


class WorkflowPolicyError(ValueError):
    """Raised when workflow security policy cannot be proven from supported YAML."""


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")))


def _strip_yaml_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(line):
        if quote == '"':
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == quote:
                quote = None
                continue
        elif quote == "'":
            if character == quote:
                if index + 1 < len(line) and line[index + 1] == "'":
                    continue
                quote = None
                continue
        else:
            if character in {"'", '"'}:
                quote = character
                continue
            if character == "#":
                return line[:index].rstrip()
    return line.rstrip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _normalize_key(value: str) -> str:
    key = _unquote(value)
    if not SIMPLE_KEY.fullmatch(key):
        raise WorkflowPolicyError(f"unsupported YAML mapping key: {value!r}")
    return key


def _split_top_level(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    depth = 0

    for index, character in enumerate(value):
        if quote == '"':
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == quote:
                quote = None
            continue
        if quote == "'":
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            continue
        if character in "{[":
            depth += 1
            continue
        if character in "]}":
            depth -= 1
            if depth < 0:
                raise WorkflowPolicyError(f"unbalanced flow value: {value!r}")
            continue
        if character == delimiter and depth == 0:
            parts.append(value[start:index])
            start = index + 1

    if quote is not None or depth != 0:
        raise WorkflowPolicyError(f"unterminated flow value: {value!r}")
    parts.append(value[start:])
    return parts


def _split_mapping_entry(value: str) -> tuple[str, str]:
    quote: str | None = None
    escaped = False
    depth = 0
    for index, character in enumerate(value):
        if quote == '"':
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == quote:
                quote = None
            continue
        if quote == "'":
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            continue
        if character in "{[":
            depth += 1
            continue
        if character in "]}":
            depth -= 1
            continue
        if character == ":" and depth == 0:
            return value[:index], value[index + 1 :]
    raise WorkflowPolicyError(f"unsupported flow mapping entry: {value!r}")


def _parse_flow_mapping(value: str) -> dict[str, str]:
    value = value.strip()
    if not (value.startswith("{") and value.endswith("}")):
        raise WorkflowPolicyError(f"expected flow mapping, got: {value!r}")
    inner = value[1:-1].strip()
    if not inner:
        return {}

    result: dict[str, str] = {}
    for raw_entry in _split_top_level(inner, ","):
        raw_key, raw_value = _split_mapping_entry(raw_entry)
        key = _normalize_key(raw_key)
        if key in result:
            raise WorkflowPolicyError(f"duplicate flow mapping key: {key}")
        result[key] = raw_value.strip()
    return result


def _parse_key_value_line(
    line: str, *, allow_list_item: bool = False
) -> tuple[int, str, str] | None:
    code = _strip_yaml_comment(line)
    if not code.strip():
        return None
    indent = len(code) - len(code.lstrip(" "))
    body = code[indent:]
    if allow_list_item and body.startswith("- "):
        body = body[2:].lstrip()
    elif body.startswith("- "):
        return None

    raw_key, separator, raw_value = body.partition(":")
    if not separator:
        return None
    try:
        key = _normalize_key(raw_key)
    except WorkflowPolicyError:
        return None
    return indent, key, raw_value.strip()


def _normalize_permission_value(value: str) -> str:
    normalized = _unquote(value).strip().lower()
    if normalized not in {"read", "write", "none"}:
        raise WorkflowPolicyError(f"unsupported permission value: {value!r}")
    return normalized


def _block_mapping(lines: list[str], start: int, parent_indent: int) -> dict[str, str]:
    result: dict[str, str] = {}
    direct_indent: int | None = None
    for index in range(start, len(lines)):
        code = _strip_yaml_comment(lines[index])
        if not code.strip():
            continue
        indent = len(code) - len(code.lstrip(" "))
        if indent <= parent_indent:
            break
        parsed = _parse_key_value_line(code)
        if parsed is None:
            continue
        parsed_indent, key, raw_value = parsed
        if direct_indent is None:
            direct_indent = parsed_indent
        if parsed_indent != direct_indent:
            continue
        if key in result:
            raise WorkflowPolicyError(f"duplicate block mapping key: {key}")
        result[key] = raw_value
    return result


def _permission_mappings(text: str) -> list[tuple[int, dict[str, str] | str]]:
    lines = text.splitlines()
    mappings: list[tuple[int, dict[str, str] | str]] = []
    for index, line in enumerate(lines):
        parsed = _parse_key_value_line(line)
        if parsed is None:
            stripped = _strip_yaml_comment(line).strip()
            if re.match(r"^\?\s*['\"]?permissions['\"]?\s*$", stripped):
                raise WorkflowPolicyError("complex permissions keys are not supported")
            continue
        indent, key, raw_value = parsed
        if key != "permissions":
            continue
        if raw_value:
            scalar = _unquote(raw_value).strip().lower()
            if scalar in {"read-all", "write-all"}:
                mappings.append((indent, scalar))
            elif raw_value.strip().startswith("{"):
                mappings.append((indent, _parse_flow_mapping(raw_value)))
            else:
                raise WorkflowPolicyError(f"unsupported permissions syntax: {raw_value!r}")
        else:
            mappings.append((indent, _block_mapping(lines, index + 1, indent)))
    return mappings


def _step_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        code = _strip_yaml_comment(line)
        match = re.match(r"^(\s*)-\s+", code)
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


def _step_direct_entries(step: str) -> tuple[dict[str, str], list[str], int]:
    lines = step.splitlines()
    if not lines:
        return {}, lines, 0
    first = _strip_yaml_comment(lines[0])
    match = re.match(r"^(\s*)-\s+(.*)$", first)
    if match is None:
        raise WorkflowPolicyError("malformed workflow step")
    step_indent = len(match.group(1))
    first_body = match.group(2).strip()
    if first_body.startswith("{"):
        if len(lines) != 1:
            raise WorkflowPolicyError("multiline flow-style steps are not supported")
        return _parse_flow_mapping(first_body), lines, step_indent

    result: dict[str, str] = {}
    first_parsed = _parse_key_value_line(lines[0], allow_list_item=True)
    if first_parsed is not None:
        _, key, raw_value = first_parsed
        result[key] = raw_value

    direct_indent: int | None = None
    for line in lines[1:]:
        parsed = _parse_key_value_line(line)
        if parsed is None:
            continue
        indent, key, raw_value = parsed
        if indent <= step_indent:
            continue
        if direct_indent is None:
            direct_indent = indent
        if indent != direct_indent:
            continue
        if key in result:
            raise WorkflowPolicyError(f"duplicate step key: {key}")
        result[key] = raw_value
    return result, lines, step_indent


def _uses_values(text: str) -> list[str]:
    values: list[str] = []
    for step in _step_blocks(text):
        entries, _, _ = _step_direct_entries(step)
        if "uses" in entries:
            values.append(_unquote(entries["uses"]).strip())
    return values


def _checkout_persist_credentials(step: str) -> str:
    entries, lines, step_indent = _step_direct_entries(step)
    raw_with = entries.get("with")
    if raw_with is None:
        raise WorkflowPolicyError("checkout step must declare with.persist-credentials")

    if raw_with:
        if not raw_with.strip().startswith("{"):
            raise WorkflowPolicyError("checkout 'with' must be a block or flow mapping")
        with_mapping = _parse_flow_mapping(raw_with)
    else:
        with_line_index: int | None = None
        with_indent: int | None = None
        for index, line in enumerate(lines):
            parsed = _parse_key_value_line(line, allow_list_item=(index == 0))
            if parsed is None:
                continue
            indent, key, raw_value = parsed
            if key == "with" and indent > step_indent and not raw_value:
                with_line_index = index
                with_indent = indent
                break
        if with_line_index is None or with_indent is None:
            raise WorkflowPolicyError("checkout 'with' block could not be resolved")
        with_mapping = _block_mapping(lines, with_line_index + 1, with_indent)

    raw_value = with_mapping.get("persist-credentials")
    if raw_value is None:
        raise WorkflowPolicyError("checkout step must explicitly set with.persist-credentials")
    normalized = _unquote(raw_value).strip().lower()
    if normalized not in {"true", "false"}:
        raise WorkflowPolicyError("with.persist-credentials must be literal true or false")
    return normalized


def _validate_workflow_security(name: str, text: str) -> None:
    permission_mappings = _permission_mappings(text)
    top_level = [mapping for indent, mapping in permission_mappings if indent == 0]
    if len(top_level) != 1 or not isinstance(top_level[0], dict):
        raise WorkflowPolicyError(f"{name} must declare one top-level permissions mapping")

    expected_contents = "write" if name == APPROVED_WRITER else "read"
    top_contents = top_level[0].get("contents")
    if top_contents is None or _normalize_permission_value(top_contents) != expected_contents:
        raise WorkflowPolicyError(
            f"{name} top-level contents permission must be {expected_contents}"
        )

    for _, mapping in permission_mappings:
        if mapping == "write-all":
            raise WorkflowPolicyError(f"{name} must not use permissions: write-all")
        if mapping == "read-all":
            continue
        assert isinstance(mapping, dict)
        if "contents" not in mapping:
            continue
        contents = _normalize_permission_value(mapping["contents"])
        if contents == "write" and name != APPROVED_WRITER:
            raise WorkflowPolicyError(f"{name} must not grant contents: write")

    first_party_seen = 0
    for value in _uses_values(text):
        if not value.startswith("actions/"):
            continue
        first_party_seen += 1
        action, separator, ref = value.rpartition("@")
        if separator != "@" or not action or not FULL_COMMIT_SHA.fullmatch(ref):
            raise WorkflowPolicyError(
                f"{name} uses floating or malformed first-party Action: {value}"
            )
    if first_party_seen == 0:
        raise WorkflowPolicyError(f"{name} has no first-party actions/* use to guard")

    checkout_steps = []
    for step in _step_blocks(text):
        entries, _, _ = _step_direct_entries(step)
        value = _unquote(entries.get("uses", "")).strip()
        if value.startswith("actions/checkout@"):
            checkout_steps.append(step)
    if not checkout_steps:
        raise WorkflowPolicyError(
            f"{name} has no checkout step for credential-policy validation"
        )

    expected_persist = "true" if name == APPROVED_WRITER else "false"
    for step in checkout_steps:
        actual = _checkout_persist_credentials(step)
        if actual != expected_persist:
            raise WorkflowPolicyError(
                f"{name} checkout must set with.persist-credentials: {expected_persist}"
            )


class ActionsWorkflowSecurityTests(unittest.TestCase):
    def test_all_maintained_workflows_follow_security_policy(self) -> None:
        paths = _workflow_paths()
        self.assertTrue(paths, "No maintained GitHub Actions workflows were found")
        for path in paths:
            with self.subTest(path=path.name):
                _validate_workflow_security(path.name, path.read_text(encoding="utf-8"))

    def test_job_level_flow_permissions_cannot_hide_contents_write(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    permissions: {{contents: write}}
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "must not grant contents: write"):
            _validate_workflow_security("ci.yml", workflow)

    def test_checkout_credential_decoy_outside_with_is_rejected(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    steps:
      - uses: actions/checkout@{'1' * 40}
        env:
          persist-credentials: false
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "with.persist-credentials"):
            _validate_workflow_security("ci.yml", workflow)

    def test_flow_style_checkout_with_is_structurally_validated(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    steps:
      - uses: actions/checkout@{'1' * 40}
        with: {{persist-credentials: false}}
"""
        _validate_workflow_security("ci.yml", workflow)

    def test_permissions_alias_fails_closed(self) -> None:
        workflow = f"""\
permissions:
  contents: read
jobs:
  probe:
    permissions: *elevated
    steps:
      - uses: actions/checkout@{'1' * 40}
        with:
          persist-credentials: false
"""
        with self.assertRaisesRegex(WorkflowPolicyError, "unsupported permissions syntax"):
            _validate_workflow_security("ci.yml", workflow)


if __name__ == "__main__":
    unittest.main()
