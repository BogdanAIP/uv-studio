#!/usr/bin/env python3
"""Stage the immutable Windows payload and attach exact backend-native legal evidence."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Sequence

if __package__:
    from tools import stage_windows_release_core as _core
else:
    import stage_windows_release_core as _core

# Preserve the public and test-visible surface of the proven Stage 9 staging
# implementation while keeping this file as a thin orchestration boundary.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


_EXPECTED_BACKEND_NATIVE_PE = 78
_EXPECTED_BACKEND_NATIVE_GROUPS = 14


def _stage_backend_native_legal_from_release_environment(output: Path) -> list[str]:
    """Stage exact backend PE/PYD legal evidence for a validated release build."""
    if not os.environ.get("UV_PYINSTALLER_VERSION"):
        return []
    legal_root = output / "legal" / "backend-native"
    try:
        if __package__:
            from tools.backend_native_legal import (
                BackendNativeLegalError,
                stage_backend_native_legal,
            )
        else:
            from backend_native_legal import (
                BackendNativeLegalError,
                stage_backend_native_legal,
            )

        result = stage_backend_native_legal(release_root=output)
    except (OSError, UnicodeError, BackendNativeLegalError) as exc:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise _core.WindowsReleaseStageError(
            f"backend native legal/provenance gate failed: {exc}"
        ) from exc

    if result.get("pe_count") != _EXPECTED_BACKEND_NATIVE_PE:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise _core.WindowsReleaseStageError(
            "backend native PE count drifted: "
            f"expected {_EXPECTED_BACKEND_NATIVE_PE}, got {result.get('pe_count')!r}"
        )
    if result.get("group_count") != _EXPECTED_BACKEND_NATIVE_GROUPS:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise _core.WindowsReleaseStageError(
            "backend native legal group count drifted: "
            f"expected {_EXPECTED_BACKEND_NATIVE_GROUPS}, got {result.get('group_count')!r}"
        )
    return sorted(
        (
            path.relative_to(output).as_posix()
            for path in legal_root.rglob("*")
            if path.is_file()
        ),
        key=str.casefold,
    )


def stage_windows_release(**kwargs):
    output = Path(kwargs["output_root"]).expanduser()
    result = _core.stage_windows_release(**kwargs)
    try:
        native_files = _stage_backend_native_legal_from_release_environment(output)
        result["legal_files"].extend(native_files)
        result["file_count"] = sum(1 for path in output.rglob("*") if path.is_file())
        return result
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    args = _core._parser().parse_args(argv)
    try:
        result = stage_windows_release(
            backend_root=args.backend_root,
            frontend_root=args.frontend_root,
            node_executable=args.node_executable,
            node_license_file=args.node_license,
            media_root=args.media_root,
            ffmpeg_executable=args.ffmpeg_executable,
            ffprobe_executable=args.ffprobe_executable,
            mlt_executable=args.mlt_executable,
            uv_license_file=args.uv_license,
            third_party_notices_file=args.third_party_notices,
            release_profile_file=args.release_profile,
            output_root=args.output,
        )
    except (OSError, _core.WindowsReleaseStageError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
