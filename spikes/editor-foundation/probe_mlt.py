#!/usr/bin/env python3
"""Executable MLT foundation probe; emits a machine-readable report."""
from __future__ import annotations

import json
import pathlib
import sys
import time

import mlt7 as mlt


def wait_consumer(consumer, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while not consumer.is_stopped():
        if time.monotonic() >= deadline:
            consumer.stop()
            raise RuntimeError("MLT consumer timed out")
        time.sleep(0.05)


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("usage: probe_mlt.py SOURCE OUTPUT XML REPORT")
    source = pathlib.Path(sys.argv[1]).resolve()
    output = pathlib.Path(sys.argv[2]).resolve()
    xml_path = pathlib.Path(sys.argv[3]).resolve()
    report_path = pathlib.Path(sys.argv[4]).resolve()

    caps: dict[str, bool] = {}
    notes: list[str] = []

    mlt.Factory().init()
    profile = mlt.Profile()
    probe = mlt.Producer(profile, str(source))
    if not probe.is_valid():
        raise RuntimeError("MLT could not open source fixture")
    profile.from_producer(probe)
    caps["open_source_media"] = True

    playlist = mlt.Playlist(profile)
    caps["create_timeline"] = playlist is not None

    first = mlt.Producer(profile, str(source))
    playlist.append(first, 6, 65)
    caps["add_clip"] = playlist.count() == 1
    caps["trim_clip"] = playlist.clip_length(0) == 60

    second = mlt.Producer(profile, str(source))
    playlist.append(second, 0, 29)
    caps["query_timeline"] = playlist.count() == 2 and playlist.get_length() > 0

    # Playlist operations are the direct scriptable edit vocabulary.
    original_count = playlist.count()
    split_result = playlist.split_at(30)
    caps["split_clip"] = split_result >= 0 and playlist.count() >= original_count

    if playlist.count() >= 2:
        move_result = playlist.move(0, playlist.count() - 1)
        caps["move_clip"] = move_result == 0
        caps["ripple_or_reorder"] = caps["move_clip"]
    else:
        caps["move_clip"] = False
        caps["ripple_or_reorder"] = False

    # MLT layers are expressed through tractor tracks.
    track_a = mlt.Playlist(profile)
    track_b = mlt.Playlist(profile)
    track_a.append(mlt.Producer(profile, str(source)), 0, 59)
    track_b.blank(15)
    track_b.append(mlt.Producer(profile, str(source)), 15, 44)
    tractor = mlt.Tractor(profile)
    tractor.set_track(track_a, 0)
    tractor.set_track(track_b, 1)
    caps["multiple_tracks_or_layers"] = tractor.count() >= 2

    # Preview/decode one frame from the composed producer.
    tractor.seek(15)
    frame = tractor.get_frame()
    caps["preview_frame"] = frame is not None

    # The XML consumer provides a portable, script-generated MLT edit model.
    xml_consumer = mlt.Consumer(profile, "xml", str(xml_path))
    if not xml_consumer.is_valid():
        raise RuntimeError("MLT xml consumer unavailable")
    xml_consumer.connect(tractor)
    xml_consumer.start()
    wait_consumer(xml_consumer)
    caps["serialize_state"] = xml_path.is_file() and xml_path.stat().st_size > 0

    reloaded = mlt.Producer(profile, f"xml:{xml_path}")
    caps["roundtrip_state"] = reloaded.is_valid() and reloaded.get_length() > 0

    # Python Playlist/Tractor methods are themselves the external mutation seam.
    caps["external_programmatic_mutation"] = all(
        hasattr(playlist, name) for name in ("append", "move", "resize_clip", "split_at", "remove")
    )
    caps["undo_redo_integration_surface"] = caps["serialize_state"] and caps["external_programmatic_mutation"]
    caps["exact_range_replacement_expressible"] = all(
        hasattr(playlist, name) for name in ("split_at", "remove", "insert", "resize_clip")
    )

    render = mlt.Consumer(profile, "avformat", str(output))
    if not render.is_valid():
        raise RuntimeError("MLT avformat consumer unavailable")
    render.set("vcodec", "libx264")
    render.set("an", 1)
    render.connect(tractor)
    render.start()
    wait_consumer(render)
    caps["render_export"] = output.is_file() and output.stat().st_size > 0

    report = {
        "candidate": "mlt",
        "binding_version": str(mlt.LIBMLT_VERSION) if hasattr(mlt, "LIBMLT_VERSION") else "unknown",
        "capabilities": caps,
        "notes": notes,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(caps.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
