#!/usr/bin/env python3
"""Append a human-readable editor-foundation probe result to GitHub Job Summary."""
from __future__ import annotations

import json
import os
import pathlib
import sys


def mark(value: bool) -> str:
    return "✅" if value else "❌"


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: summarize_probe.py TITLE REPORT")
    title = sys.argv[1]
    report_path = pathlib.Path(sys.argv[2])
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return 0

    lines = [f"## {title}", ""]
    if not report_path.is_file():
        lines += ["🔴 **Probe infrastructure failure:** report file was not produced.", ""]
    else:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        completed = bool(report.get("probe_completed", True))
        lines.append(f"- Probe completed: {mark(completed)} `{completed}`")

        if "all_required_capabilities" in report:
            all_caps = bool(report["all_required_capabilities"])
            lines.append(f"- All required capabilities: {mark(all_caps)} `{all_caps}`")
        if "candidate_eligible" in report:
            eligible = bool(report["candidate_eligible"])
            lines.append(f"- Candidate eligible for its role: {mark(eligible)} `{eligible}`")
        if report.get("binding_version"):
            lines.append(f"- Binding version: `{report['binding_version']}`")
        if report.get("fatal_error"):
            lines.append(f"- Fatal error: `{report['fatal_error']}`")
        lines.append("")

        caps = report.get("capabilities") or {}
        if caps:
            lines += ["| Capability | Result |", "|---|---|"]
            for name, value in sorted(caps.items()):
                lines.append(f"| `{name}` | {mark(bool(value))} |")
            lines.append("")

        checks = {
            "license_mit": report.get("license_mit"),
            "implemented_timeline_source_present": report.get("implemented_timeline_source_present"),
        }
        checks = {k: v for k, v in checks.items() if v is not None}
        if checks:
            lines += ["| Donor check | Result |", "|---|---|"]
            for name, value in checks.items():
                lines.append(f"| `{name}` | {mark(bool(value))} |")
            lines.append("")

        notes = report.get("notes") or ([report["note"]] if report.get("note") else [])
        if notes:
            lines.append("**Notes / rejection reasons**")
            for note in notes:
                lines.append(f"- {note}")
            lines.append("")

        lines.append(f"Raw evidence: `{report_path.as_posix()}` (also uploaded as a workflow artifact).")
        lines.append("")

    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
