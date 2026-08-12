#!/usr/bin/env python3
"""Inspect a pinned OpenCut checkout as a UI/component donor, not an engine."""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: probe_opencut.py CHECKOUT REPORT")
    root = pathlib.Path(sys.argv[1]).resolve()
    report_path = pathlib.Path(sys.argv[2]).resolve()

    license_text = (root / "LICENSE").read_text(encoding="utf-8", errors="replace")
    files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    timeline_files = [p for p in files if "timeline" in p.lower()]
    editor_files = [p for p in files if "editor" in p.lower()]

    package_files = [p for p in ("package.json", "bun.lock", "bun.lockb", "pnpm-lock.yaml") if (root / p).exists()]
    report = {
        "candidate": "opencut",
        "role": "editor_ux_donor",
        "license_mit": "MIT License" in license_text,
        "timeline_file_count": len(timeline_files),
        "editor_file_count": len(editor_files),
        "timeline_examples": timeline_files[:25],
        "package_files": package_files,
        "note": "Source-presence evidence only; planned Editor API/MCP/headless features are not credited by this probe.",
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["license_mit"] or not timeline_files:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
