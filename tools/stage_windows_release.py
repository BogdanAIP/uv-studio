#!/usr/bin/env python3
"""Stage proven Windows release components into one immutable UV Studio payload."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Sequence


class WindowsReleaseStageError(RuntimeError):
    pass


def _require_directory(path: Path | str, label: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise WindowsReleaseStageError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WindowsReleaseStageError(f"{label} is missing") from exc
    if not resolved.is_dir():
        raise WindowsReleaseStageError(f"{label} must be a real directory")
    return resolved


def _require_file(path: Path | str, label: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise WindowsReleaseStageError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WindowsReleaseStageError(f"{label} is missing") from exc
    if not resolved.is_file():
        raise WindowsReleaseStageError(f"{label} must be a regular file")
    return resolved


def _reject_symlinks(root: Path, label: str) -> None:
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in directories:
            candidate = current_path / name
            if candidate.is_symlink():
                relative = candidate.relative_to(root).as_posix()
                raise WindowsReleaseStageError(
                    f"{label} contains symlink directory: {relative}"
                )
        for name in names:
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                raise WindowsReleaseStageError(
                    f"{label} contains symlink file: {relative}"
                )
            if not candidate.is_file():
                raise WindowsReleaseStageError(
                    f"{label} contains non-regular file: {relative}"
                )


def _relative_file(path: Path, root: Path, label: str) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise WindowsReleaseStageError(f"{label} must be inside media root") from exc
    if not relative.parts:
        raise WindowsReleaseStageError(f"{label} must be a file inside media root")
    return relative.as_posix()


def _copy_tree(source: Path, target: Path, label: str) -> None:
    _reject_symlinks(source, label)
    shutil.copytree(source, target, symlinks=False)


def stage_windows_release(
    *,
    backend_root: Path | str,
    frontend_root: Path | str,
    node_executable: Path | str,
    media_root: Path | str,
    ffmpeg_executable: Path | str,
    ffprobe_executable: Path | str,
    mlt_executable: Path | str,
    output_root: Path | str,
) -> dict[str, object]:
    backend = _require_directory(backend_root, "backend component")
    frontend = _require_directory(frontend_root, "frontend component")
    node = _require_file(node_executable, "Node executable")
    media = _require_directory(media_root, "media runtime")
    ffmpeg = _require_file(ffmpeg_executable, "FFmpeg executable")
    ffprobe = _require_file(ffprobe_executable, "FFprobe executable")
    melt = _require_file(mlt_executable, "MLT executable")

    backend_entry = backend / "uv-studio-backend.exe"
    if not backend_entry.is_file() or backend_entry.is_symlink():
        raise WindowsReleaseStageError(
            "backend component is missing regular uv-studio-backend.exe"
        )
    frontend_entry = frontend / "server.js"
    if not frontend_entry.is_file() or frontend_entry.is_symlink():
        raise WindowsReleaseStageError("frontend component is missing regular server.js")

    ffmpeg_relative = _relative_file(ffmpeg, media, "FFmpeg executable")
    ffprobe_relative = _relative_file(ffprobe, media, "FFprobe executable")
    melt_relative = _relative_file(melt, media, "MLT executable")

    output = Path(output_root).expanduser()
    if output.exists() or output.is_symlink():
        raise WindowsReleaseStageError("Windows release staging output must not already exist")

    # Validate all source trees before creating the destination so a rejected source
    # cannot leave a plausible-looking partial release behind.
    _reject_symlinks(backend, "backend component")
    _reject_symlinks(frontend, "frontend component")
    _reject_symlinks(media, "media runtime")

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir()
        _copy_tree(backend, output / "backend", "backend component")
        _copy_tree(frontend, output / "frontend", "frontend component")
        node_target = output / "runtime" / "node" / "node.exe"
        node_target.parent.mkdir(parents=True)
        shutil.copy2(node, node_target)
        _copy_tree(media, output / "runtime" / "media", "media runtime")

        entrypoints = {
            "backend": "backend/uv-studio-backend.exe",
            "frontend": "frontend/server.js",
            "node": "runtime/node/node.exe",
            "ffmpeg": f"runtime/media/{ffmpeg_relative}",
            "ffprobe": f"runtime/media/{ffprobe_relative}",
            "mlt": f"runtime/media/{melt_relative}",
        }
        for component_id, relative in entrypoints.items():
            candidate = output.joinpath(*relative.split("/"))
            if not candidate.is_file() or candidate.is_symlink():
                raise WindowsReleaseStageError(
                    f"staged {component_id} entrypoint is missing or invalid: {relative}"
                )

        file_count = sum(1 for path in output.rglob("*") if path.is_file())
        media_file_count = sum(
            1 for path in (output / "runtime" / "media").rglob("*") if path.is_file()
        )
        return {
            "ok": True,
            "entrypoints": entrypoints,
            "file_count": file_count,
            "media_file_count": media_file_count,
        }
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", type=Path, required=True)
    parser.add_argument("--frontend-root", type=Path, required=True)
    parser.add_argument("--node-executable", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--ffmpeg-executable", type=Path, required=True)
    parser.add_argument("--ffprobe-executable", type=Path, required=True)
    parser.add_argument("--mlt-executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = stage_windows_release(
            backend_root=args.backend_root,
            frontend_root=args.frontend_root,
            node_executable=args.node_executable,
            media_root=args.media_root,
            ffmpeg_executable=args.ffmpeg_executable,
            ffprobe_executable=args.ffprobe_executable,
            mlt_executable=args.mlt_executable,
            output_root=args.output,
        )
    except (OSError, WindowsReleaseStageError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
