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

    fatal_error: str | None = None
    report: dict[str, object]
    try:
        license_text = (root / "LICENSE").read_text(encoding="utf-8", errors="replace")
        files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
        timeline_files = [p for p in files if "timeline" in p.lower()]
        editor_files = [p for p in files if "editor" in p.lower()]
        package_files = [p for p in ("package.json", "bun.lock", "bun.lockb", "pnpm-lock.yaml") if (root / p).exists()]

        license_mit = (
            "Permission is hereby granted, free of charge" in license_text
            and "to deal in the Software without restriction" in license_text
            and (
                'THE SOFTWARE IS PROVIDED “AS IS”' in license_text
                or 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text
            )
        )
        timeline_markers = {
            "store": any(p.endswith("timeline-store.ts") for p in timeline_files),
            "drag": any(p.endswith("drag.ts") or p.endswith("drag-utils.ts") for p in timeline_files),
            "tracks": any(p.endswith("tracks.ts") or p.endswith("track-capabilities.ts") for p in timeline_files),
            "update_pipeline": any(p.endswith("update-pipeline.ts") for p in timeline_files),
            "types": any(p.endswith("types.ts") for p in timeline_files),
        }
        implemented = len(timeline_files) >= 20 and all(timeline_markers.values())
        report = {
            "candidate": "opencut-classic",
            "role": "editor_ux_donor",
            "probe_completed": True,
            "candidate_eligible": bool(license_mit and implemented),
            "license_mit": bool(license_mit),
            "timeline_file_count": len(timeline_files),
            "editor_file_count": len(editor_files),
            "timeline_markers": timeline_markers,
            "timeline_examples": timeline_files[:25],
            "package_files": package_files,
            "implemented_timeline_source_present": implemented,
            "fatal_error": None,
            "notes": [
                "Pinned source evidence only; planned Editor API/MCP/headless features are not credited."
            ],
        }
        if not license_mit:
            report["notes"].append("Rejected as UI donor: pinned source did not satisfy the MIT-license check.")
        if not implemented:
            report["notes"].append("Rejected as UI donor: required implemented timeline source markers were incomplete.")
    except Exception as exc:
        fatal_error = f"{type(exc).__name__}: {exc}"
        report = {
            "candidate": "opencut-classic",
            "role": "editor_ux_donor",
            "probe_completed": False,
            "candidate_eligible": False,
            "fatal_error": fatal_error,
            "notes": [f"Probe aborted by unexpected error: {fatal_error}"],
        }

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if fatal_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
