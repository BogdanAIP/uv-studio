from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uv_studio.release_manifest import RELEASE_MANIFEST_FILENAME, load_release_manifest

CLASSIC_WINDOWS_FILE_PATH_LIMIT = 259
CLASSIC_WINDOWS_DIRECTORY_PATH_LIMIT = 247


def analyze_install_path_budget(
    release_root: Path | str,
    install_root: str,
    *,
    file_limit: int = CLASSIC_WINDOWS_FILE_PATH_LIMIT,
    directory_limit: int = CLASSIC_WINDOWS_DIRECTORY_PATH_LIMIT,
) -> dict[str, object]:
    root = Path(release_root).expanduser().resolve(strict=True)
    manifest = load_release_manifest(root)
    target_root = PureWindowsPath(install_root)
    if not target_root.is_absolute():
        raise ValueError("install_root must be an absolute Windows path")
    if file_limit < 1 or directory_limit < 1:
        raise ValueError("path limits must be positive")

    relative_paths = [item.path for item in manifest.files]
    relative_paths.append(RELEASE_MANIFEST_FILENAME)
    records: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []

    for relative in relative_paths:
        parts = PurePosixPath(relative).parts
        target = target_root.joinpath(*parts)
        target_text = str(target)
        directory_text = str(target.parent)
        record = {
            "path": relative,
            "target_length": len(target_text),
            "directory_length": len(directory_text),
        }
        records.append(record)
        if len(target_text) > file_limit or len(directory_text) > directory_limit:
            violations.append(record)

    records.sort(key=lambda item: (int(item["target_length"]), str(item["path"])), reverse=True)
    violations.sort(
        key=lambda item: (
            max(
                int(item["target_length"]) - file_limit,
                int(item["directory_length"]) - directory_limit,
            ),
            str(item["path"]),
        ),
        reverse=True,
    )
    longest = records[:5]
    return {
        "ok": not violations,
        "install_root": str(target_root),
        "file_limit": file_limit,
        "directory_limit": directory_limit,
        "checked_paths": len(relative_paths),
        "max_target_length": max((int(item["target_length"]) for item in records), default=0),
        "max_directory_length": max(
            (int(item["directory_length"]) for item in records), default=0
        ),
        "longest": longest,
        "violations": violations[:10],
        "violation_count": len(violations),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check a packaged UV Studio release against classic Windows install path budgets."
    )
    parser.add_argument("--release-root", required=True)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--report-only", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = analyze_install_path_budget(args.release_root, args.install_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] or args.report_only else 2


if __name__ == "__main__":
    raise SystemExit(main())
