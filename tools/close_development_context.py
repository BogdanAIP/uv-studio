"""Close one merged UV Studio development slice to the explicit idle lifecycle."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence

from tools.validate_development_context import (
    ACTIVE_SLICE_PATH,
    PROJECT_STATE_PATH,
    DevelopmentContextError,
    validate_repository,
    validate_slice_document,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _atomic_write_text(path: Path, text: str) -> None:
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def close_context(root: Path, *, pull_request: int, merge_commit: str) -> dict:
    root = root.resolve()
    if isinstance(pull_request, bool) or pull_request <= 0:
        raise DevelopmentContextError("pull_request must be a positive integer")
    if not _SHA_RE.fullmatch(merge_commit):
        raise DevelopmentContextError("merge_commit must be a lowercase 40-character SHA")

    active_path = root / ACTIVE_SLICE_PATH
    document = validate_slice_document(json.loads(active_path.read_text(encoding="utf-8")))
    if document["lifecycle_state"] != "review":
        raise DevelopmentContextError("only review state can be closed after merge")
    active = document["active_slice"]
    if active is None:
        raise DevelopmentContextError("review state requires active_slice")
    if active["pull_request"] != pull_request:
        raise DevelopmentContextError("pull_request does not match active_slice.pull_request")

    completed_id = active["id"]
    document["lifecycle_state"] = "idle"
    document["active_slice"] = None
    document["last_completed"] = {
        "id": completed_id,
        "pull_request": pull_request,
        "merge_commit": merge_commit,
    }
    _atomic_write_text(active_path, json.dumps(document, ensure_ascii=False, indent=2) + "\n")

    state_path = root / PROJECT_STATE_PATH
    state = state_path.read_text(encoding="utf-8")
    expected_state = "<!-- uv-context-state: review -->"
    expected_active = f"<!-- uv-active-slice: {completed_id} -->"
    if state.count(expected_state) != 1 or state.count(expected_active) != 1:
        raise DevelopmentContextError("PROJECT_STATE review markers do not match the slice being closed")
    state = state.replace(expected_state, "<!-- uv-context-state: idle -->")
    state = state.replace(expected_active, f"<!-- uv-last-completed: {completed_id} -->")
    _atomic_write_text(state_path, state)

    return validate_repository(root, event_name="push")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--pull-request", type=int, required=True)
    parser.add_argument("--merge-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        document = close_context(
            args.root,
            pull_request=args.pull_request,
            merge_commit=args.merge_commit,
        )
    except (DevelopmentContextError, OSError, json.JSONDecodeError) as exc:
        print(f"development-context closure failed: {exc}")
        return 1
    print(
        "development-context closed to idle: "
        f"{document['last_completed']['id']} @ {document['last_completed']['merge_commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
