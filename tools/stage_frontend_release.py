#!/usr/bin/env python3
"""Stage a Next standalone build into the immutable UV Studio frontend payload."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Sequence


class FrontendStageError(RuntimeError):
    pass


def _require_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise FrontendStageError(f"{label} is missing") from exc
    if not resolved.is_dir() or resolved.is_symlink():
        raise FrontendStageError(f"{label} must be a real directory")
    return resolved


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir() or source.is_symlink():
        raise FrontendStageError(f"standalone source is not a real directory: {source.name}")
    shutil.copytree(source, target, symlinks=False)


def stage_frontend(frontend_root: Path | str, output_root: Path | str) -> dict[str, object]:
    frontend = _require_directory(Path(frontend_root), "frontend root")
    standalone = _require_directory(frontend / ".next" / "standalone", "Next standalone output")
    server = standalone / "server.js"
    if not server.is_file() or server.is_symlink():
        raise FrontendStageError("Next standalone output is missing regular server.js")

    output = Path(output_root).expanduser()
    if output.exists() or output.is_symlink():
        raise FrontendStageError("frontend staging output must not already exist")
    output.parent.mkdir(parents=True, exist_ok=True)
    _copy_tree(standalone, output)

    static_source = frontend / ".next" / "static"
    if not static_source.is_dir() or static_source.is_symlink():
        shutil.rmtree(output, ignore_errors=True)
        raise FrontendStageError("Next build is missing .next/static")
    static_target = output / ".next" / "static"
    static_target.parent.mkdir(parents=True, exist_ok=True)
    _copy_tree(static_source, static_target)

    public_source = frontend / "public"
    if public_source.exists():
        if not public_source.is_dir() or public_source.is_symlink():
            shutil.rmtree(output, ignore_errors=True)
            raise FrontendStageError("frontend public/ must be a real directory")
        _copy_tree(public_source, output / "public")

    staged_server = output / "server.js"
    if not staged_server.is_file():
        shutil.rmtree(output, ignore_errors=True)
        raise FrontendStageError("staged frontend lost server.js")

    file_count = sum(1 for path in output.rglob("*") if path.is_file())
    return {
        "ok": True,
        "entrypoint": "server.js",
        "file_count": file_count,
        "has_public": (output / "public").is_dir(),
        "has_static": (output / ".next" / "static").is_dir(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-root", type=Path, default=Path("frontend"))
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_frontend(args.frontend_root, args.output)
    except FrontendStageError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
