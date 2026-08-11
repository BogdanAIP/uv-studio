"""Validate UV Studio's machine-readable development handoff contract.

The validator is intentionally standard-library only so it can run before the
project dependencies are installed. Repository state is always checked. On a
GitHub pull-request event, the live PR identity, draft phase and journal body
are checked as well.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


ACTIVE_SLICE_PATH = "project-context/ACTIVE_SLICE.json"
PROJECT_STATE_PATH = "project-context/PROJECT_STATE.md"
NEXT_TASK_PATH = "project-context/NEXT_TASK.md"

REQUIRED_CHECKS = frozenset(
    {
        "development-context",
        "bootstrap (ubuntu-latest, 3.11)",
        "bootstrap (windows-latest, 3.11)",
        "app-baseline (ubuntu-latest)",
        "app-baseline (windows-latest)",
    }
)
REQUIRED_PR_SECTIONS = (
    "Goal",
    "Changes",
    "Verification",
    "Architecture impact",
    "Known limitations",
    "Next task",
)

_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_H2_PATTERN = re.compile(r"^## ([^\r\n]+?)\s*$", re.MULTILINE)
_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
_REVIEW_PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD)\b|\bstill\s+to\s+do\b|replace-with-[a-z0-9-]+",
    re.IGNORECASE,
)
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class DevelopmentContextError(ValueError):
    """Raised when the development handoff contract is invalid."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DevelopmentContextError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> Any:
    raise DevelopmentContextError(f"non-standard JSON constant: {value}")


def _read_json(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DevelopmentContextError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except DevelopmentContextError:
        raise
    except json.JSONDecodeError as exc:
        raise DevelopmentContextError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DevelopmentContextError(f"cannot read {path}: {exc}") from exc


def _require_object(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DevelopmentContextError(f"{location} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], *, location: str, expected: set[str]
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing!r}")
        if unknown:
            details.append(f"unknown={unknown!r}")
        raise DevelopmentContextError(
            f"{location} has invalid keys ({', '.join(details)})"
        )


def _require_nonblank_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DevelopmentContextError(f"{location} must be a nonblank string")
    if value != value.strip():
        raise DevelopmentContextError(
            f"{location} must not contain leading or trailing whitespace"
        )
    return value


def _require_id(value: Any, location: str) -> str:
    identifier = _require_nonblank_string(value, location)
    if not _ID_PATTERN.fullmatch(identifier):
        raise DevelopmentContextError(
            f"{location} must match {_ID_PATTERN.pattern!r}"
        )
    return identifier


def _require_positive_int_or_null(value: Any, location: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DevelopmentContextError(f"{location} must be null or a positive integer")
    return value


def _require_portable_scope_path(value: Any, location: str) -> str:
    path = _require_nonblank_string(value, location)
    if "\x00" in path:
        raise DevelopmentContextError(f"{location} must not contain NUL")
    if "\\" in path:
        raise DevelopmentContextError(f"{location} must use POSIX '/' separators")
    if _WINDOWS_DRIVE_PATTERN.match(path):
        raise DevelopmentContextError(f"{location} must be project-relative")
    if any(character in path for character in ':<>"|'):
        raise DevelopmentContextError(
            f"{location} contains a non-portable path character"
        )
    if path.startswith("/") or path.endswith("/") or "//" in path:
        raise DevelopmentContextError(f"{location} must be a canonical relative path/glob")

    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise DevelopmentContextError(
            f"{location} must not contain empty, '.' or '..' path segments"
        )
    if PurePosixPath(path).is_absolute():
        raise DevelopmentContextError(f"{location} must be project-relative")
    return path


def _require_string_list(
    value: Any,
    *,
    location: str,
    path_values: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise DevelopmentContextError(f"{location} must be a nonempty JSON array")
    parsed: list[str] = []
    for index, item in enumerate(value):
        item_location = f"{location}[{index}]"
        parsed.append(
            _require_portable_scope_path(item, item_location)
            if path_values
            else _require_nonblank_string(item, item_location)
        )
    if len(parsed) != len(set(parsed)):
        raise DevelopmentContextError(f"{location} must not contain duplicates")
    return tuple(parsed)


def _validate_branch(kind: str, branch: Any) -> str:
    value = _require_nonblank_string(branch, "active_slice.branch")
    if "\\" in value or value.startswith("/") or value.endswith("/"):
        raise DevelopmentContextError("active_slice.branch must be a canonical branch name")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise DevelopmentContextError("active_slice.branch contains an invalid path segment")

    if kind == "stage":
        matches = re.fullmatch(r"stage-[1-9][0-9]*/.+", value)
    else:
        matches = value.startswith(f"{kind}/") and len(value) > len(kind) + 1
    if not matches:
        expected = "stage-N/" if kind == "stage" else f"{kind}/"
        raise DevelopmentContextError(
            f"active_slice.branch must use the {expected!r} prefix for kind {kind!r}"
        )
    return value


def _require_enum(value: Any, *, location: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise DevelopmentContextError(f"{location} must be one of: {choices}")
    return value


def validate_slice_document(raw: Any) -> dict[str, Any]:
    document = _require_object(raw, "root")
    _require_exact_keys(
        document,
        location="root",
        expected={
            "schema_version",
            "active_slice",
            "handoff",
            "coordination",
            "required_checks",
        },
    )
    schema_version = document["schema_version"]
    if isinstance(schema_version, bool) or schema_version != 1:
        raise DevelopmentContextError("schema_version must be integer 1")

    active = _require_object(document["active_slice"], "active_slice")
    _require_exact_keys(
        active,
        location="active_slice",
        expected={
            "id",
            "kind",
            "roadmap_stage",
            "goal",
            "base_branch",
            "branch",
            "pull_request",
            "phase",
            "write_scope",
        },
    )
    _require_id(active["id"], "active_slice.id")
    kind = _require_enum(
        active["kind"],
        location="active_slice.kind",
        allowed={"stage", "fix", "chore", "research"},
    )
    _require_id(active["roadmap_stage"], "active_slice.roadmap_stage")
    _require_nonblank_string(active["goal"], "active_slice.goal")
    _require_nonblank_string(active["base_branch"], "active_slice.base_branch")
    _validate_branch(kind, active["branch"])
    _require_positive_int_or_null(active["pull_request"], "active_slice.pull_request")
    _require_enum(
        active["phase"],
        location="active_slice.phase",
        allowed={"draft", "review"},
    )
    _require_string_list(
        active["write_scope"],
        location="active_slice.write_scope",
        path_values=True,
    )

    handoff = _require_object(document["handoff"], "handoff")
    _require_exact_keys(
        handoff,
        location="handoff",
        expected={"next_slice_id", "next_task_file"},
    )
    _require_id(handoff["next_slice_id"], "handoff.next_slice_id")
    if handoff["next_task_file"] != NEXT_TASK_PATH:
        raise DevelopmentContextError(
            f"handoff.next_task_file must be exactly {NEXT_TASK_PATH!r}"
        )

    coordination = _require_object(document["coordination"], "coordination")
    _require_exact_keys(
        coordination,
        location="coordination",
        expected={"integration_owner", "context_owner", "parallel_write_policy"},
    )
    expected_coordination = {
        "integration_owner": "coordinator",
        "context_owner": "coordinator",
        "parallel_write_policy": "disjoint_paths",
    }
    for field, expected in expected_coordination.items():
        if coordination[field] != expected:
            raise DevelopmentContextError(
                f"coordination.{field} must be exactly {expected!r}"
            )

    checks = _require_string_list(
        document["required_checks"], location="required_checks"
    )
    check_set = set(checks)
    if check_set != REQUIRED_CHECKS:
        missing = sorted(REQUIRED_CHECKS - check_set)
        unexpected = sorted(check_set - REQUIRED_CHECKS)
        raise DevelopmentContextError(
            "required_checks must match the required CI set exactly "
            f"(missing={missing!r}, unexpected={unexpected!r})"
        )

    # Return a normal dict with the original JSON-compatible values. Callers use
    # the already-validated identity fields for repository and PR checks.
    return dict(document)


def _validate_single_marker(text: str, *, name: str, value: str, location: str) -> None:
    expected = f"<!-- uv-{name}: {value} -->"
    if text.count(f"uv-{name}:") != 1 or text.count(expected) != 1:
        raise DevelopmentContextError(
            f"{location} must contain exactly one marker {expected!r}"
        )


def _section_content(body: str, match: re.Match[str]) -> str:
    next_match = _H2_PATTERN.search(body, match.end())
    end = next_match.start() if next_match else len(body)
    return body[match.end() : end]


def _validate_pr_body(body: Any, *, active_id: str, next_id: str, phase: str) -> None:
    if not isinstance(body, str):
        raise DevelopmentContextError("pull_request.body must be a string")
    _validate_single_marker(
        body,
        name="active-slice",
        value=active_id,
        location="pull_request.body",
    )
    _validate_single_marker(
        body,
        name="next-slice",
        value=next_id,
        location="pull_request.body",
    )

    matches = list(_H2_PATTERN.finditer(body))
    positions: list[int] = []
    for section in REQUIRED_PR_SECTIONS:
        section_matches = [match for match in matches if match.group(1) == section]
        if len(section_matches) != 1:
            raise DevelopmentContextError(
                f"pull_request.body must contain exactly one '## {section}' section"
            )
        match = section_matches[0]
        positions.append(match.start())
        content = _HTML_COMMENT_PATTERN.sub("", _section_content(body, match)).strip()
        if not content:
            raise DevelopmentContextError(
                f"pull_request.body section '## {section}' must contain meaningful content"
            )
    if positions != sorted(positions):
        raise DevelopmentContextError(
            "pull_request.body required sections must use the documented order"
        )
    if phase == "review" and _REVIEW_PLACEHOLDER_PATTERN.search(body):
        raise DevelopmentContextError(
            "pull_request.body contains a draft placeholder while phase is 'review'"
        )


def _event_field(mapping: Mapping[str, Any], field: str, location: str) -> Any:
    if field not in mapping:
        raise DevelopmentContextError(f"{location}.{field} is required")
    return mapping[field]


def _validate_pull_request_event(event: Any, document: Mapping[str, Any]) -> None:
    payload = _require_object(event, "event")
    pull_request = _require_object(
        _event_field(payload, "pull_request", "event"), "event.pull_request"
    )
    active = _require_object(document["active_slice"], "active_slice")
    handoff = _require_object(document["handoff"], "handoff")

    event_number = _event_field(payload, "number", "event")
    if isinstance(event_number, bool) or not isinstance(event_number, int) or event_number <= 0:
        raise DevelopmentContextError("event.number must be a positive integer")
    configured_number = active["pull_request"]
    if configured_number is None:
        raise DevelopmentContextError(
            "active_slice.pull_request must be set for pull_request events"
        )
    if configured_number != event_number:
        raise DevelopmentContextError(
            "active_slice.pull_request does not match event.number"
        )

    head = _require_object(
        _event_field(pull_request, "head", "event.pull_request"),
        "event.pull_request.head",
    )
    base = _require_object(
        _event_field(pull_request, "base", "event.pull_request"),
        "event.pull_request.base",
    )
    if _event_field(head, "ref", "event.pull_request.head") != active["branch"]:
        raise DevelopmentContextError(
            "event.pull_request.head.ref does not match active_slice.branch"
        )
    if _event_field(base, "ref", "event.pull_request.base") != active["base_branch"]:
        raise DevelopmentContextError(
            "event.pull_request.base.ref does not match active_slice.base_branch"
        )

    is_draft = _event_field(pull_request, "draft", "event.pull_request")
    if not isinstance(is_draft, bool):
        raise DevelopmentContextError("event.pull_request.draft must be a boolean")
    expected_draft = active["phase"] == "draft"
    if is_draft != expected_draft:
        raise DevelopmentContextError(
            "event.pull_request.draft does not match active_slice.phase"
        )

    _validate_pr_body(
        _event_field(pull_request, "body", "event.pull_request"),
        active_id=active["id"],
        next_id=handoff["next_slice_id"],
        phase=active["phase"],
    )


def validate_repository(
    root: Path,
    *,
    event_name: str | None = None,
    event_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    document = validate_slice_document(_read_json(root / ACTIVE_SLICE_PATH))
    active = _require_object(document["active_slice"], "active_slice")
    handoff = _require_object(document["handoff"], "handoff")

    project_state = _read_text(root / PROJECT_STATE_PATH)
    next_task_file = root / handoff["next_task_file"]
    next_task = _read_text(next_task_file)
    _validate_single_marker(
        project_state,
        name="active-slice",
        value=active["id"],
        location=PROJECT_STATE_PATH,
    )
    _validate_single_marker(
        next_task,
        name="next-slice",
        value=handoff["next_slice_id"],
        location=handoff["next_task_file"],
    )

    normalized_event = (event_name or "").strip()
    if normalized_event not in {"", "push", "pull_request"}:
        raise DevelopmentContextError(
            f"unsupported GITHUB_EVENT_NAME: {normalized_event!r}"
        )
    if normalized_event == "pull_request":
        if event_path is None:
            raise DevelopmentContextError(
                "GITHUB_EVENT_PATH is required for pull_request validation"
            )
        _validate_pull_request_event(_read_json(event_path), document)
    return document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate UV Studio development context and pull-request handoff state."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    parser.add_argument(
        "--event",
        type=Path,
        default=None,
        help="GitHub event JSON path (default: GITHUB_EVENT_PATH).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = args.event
    if event_path is None:
        raw_event_path = os.environ.get("GITHUB_EVENT_PATH")
        if raw_event_path:
            event_path = Path(raw_event_path)
    try:
        document = validate_repository(
            args.root,
            event_name=event_name,
            event_path=event_path,
        )
    except DevelopmentContextError as exc:
        print(f"development-context validation failed: {exc}", file=sys.stderr)
        return 1

    active = _require_object(document["active_slice"], "active_slice")
    print(
        "development-context validation passed: "
        f"{active['id']} ({active['phase']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
