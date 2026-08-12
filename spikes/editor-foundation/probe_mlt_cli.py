#!/usr/bin/env python3
"""Probe a relocatable MLT/melt runtime through its CLI and serialized XML state."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

REQUIRED = (
    "melt_runtime",
    "open_source_media",
    "serialize_state",
    "roundtrip_state",
    "external_programmatic_mutation",
    "render_export",
    "exact_range_replacement_expressible",
)


def run(command: list[str], *, cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def add_property(parent: ET.Element, name: str, value: str) -> None:
    node = ET.SubElement(parent, "property", {"name": name})
    node.text = value


def build_project(source: pathlib.Path) -> ET.ElementTree:
    root = ET.Element("mlt", {"LC_NUMERIC": "C", "version": "7.40.0"})
    ET.SubElement(
        root,
        "profile",
        {
            "description": "UV Studio MLT Windows probe",
            "width": "320",
            "height": "240",
            "progressive": "1",
            "sample_aspect_num": "1",
            "sample_aspect_den": "1",
            "display_aspect_num": "4",
            "display_aspect_den": "3",
            "frame_rate_num": "30",
            "frame_rate_den": "1",
            "colorspace": "709",
        },
    )

    producer = ET.SubElement(root, "producer", {"id": "source", "in": "0", "out": "119"})
    add_property(producer, "mlt_service", "avformat-novalidate")
    add_property(producer, "resource", source.as_posix())

    playlist = ET.SubElement(root, "playlist", {"id": "playlist0"})
    ET.SubElement(playlist, "entry", {"producer": "source", "in": "0", "out": "29"})
    ET.SubElement(
        playlist,
        "entry",
        {"producer": "source", "in": "30", "out": "59", "uv_role": "replacement"},
    )
    ET.SubElement(playlist, "entry", {"producer": "source", "in": "60", "out": "119"})

    tractor = ET.SubElement(root, "tractor", {"id": "tractor0", "in": "0", "out": "119"})
    ET.SubElement(tractor, "track", {"producer": "playlist0"})
    return ET.ElementTree(root)


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: probe_mlt_cli.py MELT SOURCE OUTPUT XML REPORT")

    melt = pathlib.Path(sys.argv[1]).resolve()
    source = pathlib.Path(sys.argv[2]).resolve()
    output = pathlib.Path(sys.argv[3]).resolve()
    xml_path = pathlib.Path(sys.argv[4]).resolve()
    report_path = pathlib.Path(sys.argv[5]).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.parent.mkdir(parents=True, exist_ok=True)

    caps = {name: False for name in REQUIRED}
    notes: list[str] = []
    fatal_error: str | None = None
    version = "unknown"

    try:
        if not melt.is_file():
            raise RuntimeError(f"melt executable not found: {melt}")
        workdir = melt.parent

        version_probe = run([str(melt), "-version"], cwd=workdir)
        caps["melt_runtime"] = version_probe.returncode == 0
        version = version_probe.stdout.splitlines()[0].strip() if version_probe.stdout else "unknown"
        if not caps["melt_runtime"]:
            raise RuntimeError(f"melt -version failed: {version_probe.stdout[-1000:]}")

        query = run([str(melt), "-query", "producers"], cwd=workdir)
        caps["open_source_media"] = query.returncode == 0 and "avformat" in query.stdout.lower()
        if not caps["open_source_media"]:
            raise RuntimeError("MLT runtime does not expose an avformat producer")

        tree = build_project(source)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        caps["serialize_state"] = xml_path.is_file() and xml_path.stat().st_size > 0

        parsed = ET.parse(xml_path)
        replacement = parsed.getroot().find(".//entry[@uv_role='replacement']")
        if replacement is None:
            raise RuntimeError("serialized MLT project lost replacement marker")
        caps["roundtrip_state"] = replacement.get("in") == "30" and replacement.get("out") == "59"

        replacement.set("in", "60")
        replacement.set("out", "89")
        replacement.attrib.pop("uv_role", None)
        parsed.write(xml_path, encoding="utf-8", xml_declaration=True)

        reparsed = ET.parse(xml_path)
        middle = reparsed.getroot().find(".//playlist[@id='playlist0']/entry[2]")
        caps["external_programmatic_mutation"] = (
            middle is not None and middle.get("in") == "60" and middle.get("out") == "89"
        )
        caps["exact_range_replacement_expressible"] = caps["external_programmatic_mutation"]

        render = run(
            [
                str(melt),
                str(xml_path),
                "-consumer",
                f"avformat:{output}",
                "vcodec=mpeg4",
                "an=1",
                "real_time=-1",
                "terminate_on_pause=1",
            ],
            cwd=workdir,
        )
        if render.returncode != 0:
            notes.append(f"melt render output: {render.stdout[-2000:]}")
        caps["render_export"] = render.returncode == 0 and output.is_file() and output.stat().st_size > 0
        if not caps["render_export"]:
            raise RuntimeError("melt failed to render the mutated serialized project")
    except Exception as exc:
        fatal_error = f"{type(exc).__name__}: {exc}"
        notes.append(f"Probe aborted by unexpected error: {fatal_error}")

    report = {
        "candidate": "mlt-cli-windows",
        "runtime_version": version,
        "probe_completed": fatal_error is None,
        "all_required_capabilities": all(caps.values()),
        "capabilities": caps,
        "fatal_error": fatal_error,
        "notes": notes,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if fatal_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
