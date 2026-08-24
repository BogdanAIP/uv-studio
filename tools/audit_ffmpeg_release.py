#!/usr/bin/env python3
"""Fail closed when a staged FFmpeg build advertises non-redistributable options."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Sequence

MAX_BUILD_INFO_BYTES = 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 20.0


class FFmpegReleaseAuditError(RuntimeError):
    pass


def inspect_ffmpeg(
    executable: Path | str,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, object]:
    path = Path(executable).expanduser()
    if path.is_symlink():
        raise FFmpegReleaseAuditError("FFmpeg executable must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise FFmpegReleaseAuditError("FFmpeg executable is missing") from exc
    if not resolved.is_file():
        raise FFmpegReleaseAuditError("FFmpeg executable must be a regular file")
    if timeout_seconds <= 0:
        raise FFmpegReleaseAuditError("timeout_seconds must be positive")

    try:
        completed = subprocess.run(
            [str(resolved), "-hide_banner", "-buildconf"],
            capture_output=True,
            text=False,
            shell=False,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegReleaseAuditError("FFmpeg build configuration probe timed out") from exc
    except OSError as exc:
        raise FFmpegReleaseAuditError("FFmpeg build configuration probe could not start") from exc

    combined = (completed.stdout or b"") + b"\n" + (completed.stderr or b"")
    if len(combined) > MAX_BUILD_INFO_BYTES:
        raise FFmpegReleaseAuditError("FFmpeg build configuration output is unexpectedly large")
    output = combined.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise FFmpegReleaseAuditError(
            f"FFmpeg build configuration probe failed with exit {completed.returncode}"
        )

    lowered = output.lower()
    nonfree_enabled = "--enable-nonfree" in lowered
    gpl_enabled = "--enable-gpl" in lowered
    shared_enabled = "--enable-shared" in lowered
    static_disabled = "--disable-static" in lowered
    if nonfree_enabled:
        raise FFmpegReleaseAuditError(
            "FFmpeg build enables --enable-nonfree and is rejected from the redistributable release payload"
        )

    configuration_lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip().startswith("--") or "configuration:" in line.lower()
    ]
    return {
        "ok": True,
        "nonfree_enabled": nonfree_enabled,
        "gpl_enabled": gpl_enabled,
        "shared_enabled": shared_enabled,
        "static_disabled": static_disabled,
        "configuration": configuration_lines,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = inspect_ffmpeg(args.ffmpeg)
    except FFmpegReleaseAuditError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.evidence is not None:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
