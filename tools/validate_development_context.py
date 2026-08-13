"""Validate UV Studio's machine-readable development handoff contract.

Schema v2 represents the complete lifecycle explicitly:

    idle -> draft -> review -> idle

The validator is standard-library only so it can run before product dependencies
are installed. Repository state is always checked. Pull-request events also bind
the declared active slice to the live PR identity, draft state and journal body.
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
_SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_H2_PATTERN = re.compile(r"^## ([^\r\n]+?)\s*$", re.MULTILINE)
_FENCE_OPEN_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})[^\r\n]*$")
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


def _require_exact_keys(value: Mapping[str, Any], *, location: str, expected: set[str]) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing!r}")
        if unknown:
            details.append(f"unknown={unknown!r}")
        raise DevelopmentContextError(f"{location} has invalid keys ({', '.join(details)})")


def _require_nonblank_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DevelopmentContextError(f"{location} must be a nonblank string")
    if value != value.strip():
        raise DevelopmentContextError(f"{location} must not contain leading/trailing whitespace")
    return value


def _require_id(value: Any, location: str) -> str:
    identifier = _require_nonblank_string(value, location)
    if not _ID_PATTERN.fullmatch(identifier):
        raise DevelopmentContextError(f"{location} must match {_ID_PATTERN.pattern!r}")
    return identifier


def _require_positive_int(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DevelopmentContextError(f"{location} must be a positive integer")
    return value


def _require_positive_int_or_null(value: Any, location: str) -> int | None:
    if value is None:
        return None
    return _require_positive_int(value, location)


def _require_sha(value: Any, location: str) -> str:
    sha = _require_nonblank_string(value, location)
    if not _SHA_PATTERN.fullmatch(sha):
        raise DevelopmentContextError(f"{location} must be a lowercase 40-character SHA")
    return sha


def _require_enum(value: Any, *, location: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise DevelopmentContextError(
            f"{location} must be one of: {', '.join(sorted(allowed))}"
        )
    return value


def _require_portable_scope_path(value: Any, location: str) -> str:
    path = _require_nonblank_string(value, location)
    if "\x00" in path or "\\" in path or _WINDOWS_DRIVE_PATTERN.match(path):
        raise DevelopmentContextError(f"{location} must be a portable relative path/glob")
    if any(character in path for character in ':<>"|'):
        raise DevelopmentContextError(f"{location} contains a non-portable path character")
    if path.startswith("/") or path.endswith("/") or "//" in path:
        raise DevelopmentContextError(f"{location} must be a canonical relative path/glob")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts) or PurePosixPath(path).is_absolute():
        raise DevelopmentContextError(f"{location} contains an invalid path segment")
    return path


def _require_string_list(
    value: Any, *, location: str, path_values: bool = False
) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise DevelopmentContextError(f"{location} must be a nonempty JSON array")
    parsed = tuple(
        _require_portable_scope_path(item, f"{location}[{index}]")
        if path_values
        else _require_nonblank_string(item, f"{location}[{index}]")
        for index, item in enumerate(value)
    )
    if len(parsed) != len(set(parsed)):
        raise DevelopmentContextError(f"{location} must not contain duplicates")
    return parsed


def _validate_branch(kind: str, branch: Any) -> str:
    value = _require_nonblank_string(branch, "active_slice.branch")
    if "\\" in value or value.startswith("/") or value.endswith("/"):
        raise DevelopmentContextError("active_slice.branch must be canonical")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise DevelopmentContextError("active_slice.branch contains an invalid path segment")
    if kind == "stage":
        valid = re.fullmatch(r"stage-[1-9][0-9]*/.+", value) is not None
        expected = "stage-N/"
    else:
        valid = value.startswith(f"{kind}/") and len(value) > len(kind) + 1
        expected = f"{kind}/"
    if not valid:
        raise DevelopmentContextError(
            f"active_slice.branch must use the {expected!r} prefix for kind {kind!r}"
        )
    return value


def _validate_active_slice(value: Any, lifecycle_state: str) -> Mapping[str, Any] | None:
    if lifecycle_state == "idle":
        if value is not None:
            raise DevelopmentContextError("active_slice must be null while lifecycle_state is idle")
        return None
    active = _require_object(value, "active_slice")
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
            "write_scope",
        },
    )
    _require_id(active["id"], "active_slice.id")
    kind = _require_enum(
        active["kind"], location="active_slice.kind", allowed={"stage", "fix", "chore", "research"}
    )
    _require_id(active["roadmap_stage"], "active_slice.roadmap_stage")
    _require_nonblank_string(active["goal"], "active_slice.goal")
    _require_nonblank_string(active["base_branch"], "active_slice.base_branch")
    _validate_branch(kind, active["branch"])
    pull_request = _require_positive_int_or_null(active["pull_request"], "active_slice.pull_request")
    if lifecycle_state == "review" and pull_request is None:
        raise DevelopmentContextError("review state requires active_slice.pull_request")
    _require_string_list(active["write_scope"], location="active_slice.write_scope", path_values=True)
    return active


def _validate_last_completed(value: Any) -> Mapping[str, Any]:
    completed = _require_object(value, "last_completed")
    _require_exact_keys(
        completed,
        location="last_completed",
        expected={"id", "pull_request", "merge_commit"},
    )
    _require_id(completed["id"], "last_completed.id")
    _require_positive_int(completed["pull_request"], "last_completed.pull_request")
    _require_sha(completed["merge_commit"], "last_completed.merge_commit")
    return completed


def validate_slice_document(raw: Any) -> dict[str, Any]:
    document = _require_object(raw, "root")
    _require_exact_keys(
        document,
        location="root",
        expected={
            "schema_version",
            "lifecycle_state",
            "active_slice",
            "last_completed",
            "handoff",
            "coordination",
            "required_checks",
        },
    )
    if isinstance(document["schema_version"], bool) or document["schema_version"] != 2:
        raise DevelopmentContextError("schema_version must be integer 2")
    lifecycle_state = _require_enum(
        document["lifecycle_state"],
        location="lifecycle_state",
        allowed={"idle", "draft", "review"},
    )
    _validate_active_slice(document["active_slice"], lifecycle_state)
    _validate_last_completed(document["last_completed"])

    handoff = _require_object(document["handoff"], "handoff")
    _require_exact_keys(handoff, location="handoff", expected={"next_slice_id", "next_task_file"})
    _require_id(handoff["next_slice_id"], "handoff.next_slice_id")
    if handoff["next_task_file"] != NEXT_TASK_PATH:
        raise DevelopmentContextError(f"handoff.next_task_file must be exactly {NEXT_TASK_PATH!r}")

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
            raise DevelopmentContextError(f"coordination.{field} must be exactly {expected!r}")

    checks = _require_string_list(document["required_checks"], location="required_checks")
    if set(checks) != REQUIRED_CHECKS:
        raise DevelopmentContextError("required_checks must match the permanent CI set exactly")
    return dict(document)


def _validate_single_marker(text: str, *, name: str, value: str, location: str) -> None:
    expected = f"<!-- uv-{name}: {value} -->"
    if text.count(f"uv-{name}:") != 1 or text.count(expected) != 1:
        raise DevelopmentContextError(f"{location} must contain exactly one marker {expected!r}")


def _validate_absent_marker(text: str, *, name: str, location: str) -> None:
    if f"uv-{name}:" in text:
        raise DevelopmentContextError(f"{location} must not contain uv-{name} in this lifecycle state")


def _mask_fenced_code(body: str) -> str:
    masked: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in body.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        newline = line[len(content):]
        if fence_character is None:
            opening = _FENCE_OPEN_PATTERN.fullmatch(content)
            if opening is None:
                masked.append(line)
                continue
            marker = opening.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
        else:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*", content
            )
            if closing is not None:
                fence_character = None
                fence_length = 0
        masked.append(" " * len(content) + newline)
    return "".join(masked)


def _section_content(body: str, heading_body: str, match: re.Match[str]) -> str:
    next_match = _H2_PATTERN.search(heading_body, match.end())
    end = next_match.start() if next_match else len(body)
    return body[match.end():end]


def _validate_pr_body(body: Any, *, active_id: str, next_id: str, state: str) -> None:
    if not isinstance(body, str):
        raise DevelopmentContextError("pull_request.body must be a string")
    _validate_single_marker(body, name="active-slice", value=active_id, location="pull_request.body")
    _validate_single_marker(body, name="next-slice", value=next_id, location="pull_request.body")
    heading_body = _mask_fenced_code(body)
    matches = list(_H2_PATTERN.finditer(heading_body))
    positions: list[int] = []
    for section in REQUIRED_PR_SECTIONS:
        section_matches = [match for match in matches if match.group(1) == section]
        if len(section_matches) != 1:
            raise DevelopmentContextError(
                f"pull_request.body must contain exactly one '## {section}' section"
            )
        match = section_matches[0]
        positions.append(match.start())
        content = _HTML_COMMENT_PATTERN.sub("", _section_content(body, heading_body, match)).strip()
        if not content:
            raise DevelopmentContextError(
                f"pull_request.body section '## {section}' must contain meaningful content"
            )
    if positions != sorted(positions):
        raise DevelopmentContextError("pull_request.body required sections are out of order")
    if state == "review" and _REVIEW_PLACEHOLDER_PATTERN.search(body):
        raise DevelopmentContextError("pull_request.body contains a draft placeholder in review")


def _event_field(mapping: Mapping[str, Any], field: str, location: str) -> Any:
    if field not in mapping:
        raise DevelopmentContextError(f"{location}.{field} is required")
    return mapping[field]


def _validate_pull_request_event(event: Any, document: Mapping[str, Any]) -> None:
    state = document["lifecycle_state"]
    if state == "idle":
        raise DevelopmentContextError("idle repository state cannot validate a pull_request event")
    active = _require_object(document["active_slice"], "active_slice")
    handoff = _require_object(document["handoff"], "handoff")
    payload = _require_object(event, "event")
    pull_request = _require_object(
        _event_field(payload, "pull_request", "event"), "event.pull_request"
    )
    event_number = _require_positive_int(_event_field(payload, "number", "event"), "event.number")
    configured_number = active["pull_request"]
    if configured_number is None or configured_number != event_number:
        raise DevelopmentContextError("active_slice.pull_request does not match event.number")

    head = _require_object(_event_field(pull_request, "head", "event.pull_request"), "event.pull_request.head")
    base = _require_object(_event_field(pull_request, "base", "event.pull_request"), "event.pull_request.base")
    if _event_field(head, "ref", "event.pull_request.head") != active["branch"]:
        raise DevelopmentContextError("event.pull_request.head.ref does not match active_slice.branch")
    if _event_field(base, "ref", "event.pull_request.base") != active["base_branch"]:
        raise DevelopmentContextError("event.pull_request.base.ref does not match active_slice.base_branch")
    is_draft = _event_field(pull_request, "draft", "event.pull_request")
    if not isinstance(is_draft, bool):
        raise DevelopmentContextError("event.pull_request.draft must be a boolean")
    if is_draft != (state == "draft"):
        raise DevelopmentContextError("event.pull_request.draft does not match lifecycle_state")
    _validate_pr_body(
        _event_field(pull_request, "body", "event.pull_request"),
        active_id=active["id"],
        next_id=handoff["next_slice_id"],
        state=state,
    )


def validate_repository(
    root: Path,
    *,
    event_name: str | None = None,
    event_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    document = validate_slice_document(_read_json(root / ACTIVE_SLICE_PATH))
    state = document["lifecycle_state"]
    active = document["active_slice"]
    completed = _require_object(document["last_completed"], "last_completed")
    handoff = _require_object(document["handoff"], "handoff")

    project_state = _read_text(root / PROJECT_STATE_PATH)
    _validate_single_marker(
        project_state,
        name="context-state",
        value=state,
        location=PROJECT_STATE_PATH,
    )
    if state == "idle":
        _validate_single_marker(
            project_state,
            name="last-completed",
            value=completed["id"],
            location=PROJECT_STATE_PATH,
        )
        _validate_absent_marker(project_state, name="active-slice", location=PROJECT_STATE_PATH)
    else:
        active_object = _require_object(active, "active_slice")
        _validate_single_marker(
            project_state,
            name="active-slice",
            value=active_object["id"],
            location=PROJECT_STATE_PATH,
        )
        _validate_absent_marker(project_state, name="last-completed", location=PROJECT_STATE_PATH)

    next_task = _read_text(root / handoff["next_task_file"])
    _validate_single_marker(
        next_task,
        name="next-slice",
        value=handoff["next_slice_id"],
        location=handoff["next_task_file"],
    )

    normalized_event = (event_name or "").strip()
    if normalized_event not in {"", "push", "pull_request"}:
        raise DevelopmentContextError(f"unsupported GITHUB_EVENT_NAME: {normalized_event!r}")
    if normalized_event == "pull_request":
        if event_path is None:
            raise DevelopmentContextError("GITHUB_EVENT_PATH is required for pull_request validation")
        _validate_pull_request_event(_read_json(event_path), document)
    return document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate UV Studio development context and pull-request handoff state."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--event", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = args.event
    if event_path is None and os.environ.get("GITHUB_EVENT_PATH"):
        event_path = Path(os.environ["GITHUB_EVENT_PATH"])
    try:
        document = validate_repository(args.root, event_name=event_name, event_path=event_path)
    except DevelopmentContextError as exc:
        print(f"development-context validation failed: {exc}", file=sys.stderr)
        return 1
    identity = (
        document["last_completed"]["id"]
        if document["lifecycle_state"] == "idle"
        else document["active_slice"]["id"]
    )
    print(f"development-context validation passed: {identity} ({document['lifecycle_state']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
