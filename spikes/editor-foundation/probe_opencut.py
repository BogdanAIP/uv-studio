#!/usr/bin/env python3
"""Inspect a pinned OpenCut Classic checkout as a UI/component donor, not an engine."""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: probe_opencut.py CHECKOUT REPORT")
    root = pathlib.Path(sys.argv[1]).resolve()
    report_path = pathlib.Path(sys.argv[2]).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    license_text = (root / "LICENSE").read_text(encoding="utf-8", errors="replace")
    files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    timeline_files = [p for p in files if "timeline" in p.lower()]
    editor_files = [p for p in files if "editor" in p.lower()]
    package_files = [p for p in ("package.json", "bun.lock", "bun.lockb", "pnpm-lock.yaml") if (root / p).exists()]

    # Some canonical MIT license texts omit the heading "MIT License". Detect
    # the actual grant and warranty clauses instead of relying on a title.
    license_mit = (
        "Permission is hereby granted, free of charge" in license_text
        and "to deal in the Software without restriction" in license_text
        and 'THE SOFTWARE IS PROVIDED “AS IS”' in license_text
        or (
            "Permission is hereby granted, free of charge" in license_text
            and "to deal in the Software without restriction" in license_text
            and 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text
        )
    )

    timeline_markers = {
        "store": any(p.endswith("timeline-store.ts") for p in timeline_files),
        "drag": any(p.endswith("drag.ts") or p.endswith("drag-utils.ts") for p in timeline_files),
        "tracks": any(p.endswith("tracks.ts") or p.endswith("track-capabilities.ts") for p in timeline_files),
        "update_pipeline": any(p.endswith("update-pipeline.ts") for p in timeline_files),
        "types": any(p.endswith("types.ts") for p in timeline_files),
    }

    report = {
        "candidate": "opencut-classic",
        "role": "editor_ux_donor",
        "license_mit": bool(license_mit),
        "timeline_file_count": len(timeline_files),
        "editor_file_count": len(editor_files),
        "timeline_markers": timeline_markers,
        "timeline_examples": timeline_files[:25],
        "package_files": package_files,
        "implemented_timeline_source_present": len(timeline_files) >= 20 and all(timeline_markers.values()),
        "note": "Pinned source evidence only; planned Editor API/MCP/headless features are not credited.",
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["license_mit"] or not report["implemented_timeline_source_present"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
