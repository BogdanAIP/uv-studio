#!/usr/bin/env python3
"""Exact audited file closure for the Stage 9 Shotcut acquisition carrier."""

from __future__ import annotations

from pathlib import Path

# Exact root PE dependency closure measured from Stage 9 artifact #120 using the
# retained UV entrypoints (ffmpeg/ffprobe/melt), MLT framework/modules and the
# Windows Qt platform plugin. Keep the carrier license/config files alongside it.
_REQUIRED_ROOT_FILES = frozenset(
    name.casefold()
    for name in (
        "avcodec-62.dll",
        "avdevice-62.dll",
        "avfilter-11.dll",
        "avformat-62.dll",
        "avutil-60.dll",
        "ffmpeg.exe",
        "ffprobe.exe",
        "libaom.dll",
        "libbz2-1.dll",
        "libdav1d.dll",
        "libdl.dll",
        "libgcc_s_seh-1.dll",
        "libiconv-2.dll",
        "liblzma-5.dll",
        "libmlt++-7.dll",
        "libmlt-7.dll",
        "libmp3lame-0.dll",
        "libogg-0.dll",
        "libopus-0.dll",
        "libsharpyuv-0.dll",
        "libstdc++-6.dll",
        "libSvtAv1Enc-4.dll",
        "libtheoradec-2.dll",
        "libtheoraenc-2.dll",
        "libvmaf.dll",
        "libvorbis-0.dll",
        "libvorbisenc-2.dll",
        "libvpl-2.dll",
        "libvpx-1.dll",
        "libwebp-7.dll",
        "libwebpmux-3.dll",
        "libwinpthread-1.dll",
        "libx264-165.dll",
        "libx265-216.dll",
        "libxml2-16.dll",
        "libzimg-2.dll",
        "melt.exe",
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Svg.dll",
        "Qt6SvgWidgets.dll",
        "Qt6Widgets.dll",
        "Qt6Xml.dll",
        "SDL2.dll",
        "swresample-6.dll",
        "swscale-9.dll",
        "zlib1.dll",
        "COPYING.txt",
        "LICENSE",
        "qt.conf",
    )
)
_REQUIRED_MLT_MODULES = frozenset(
    name.casefold()
    for name in (
        "libmltavformat.dll",
        "libmltcore.dll",
        "libmltqt6.dll",
        "libmltxml.dll",
    )
)


def carrier_path_is_required(relative: Path | str) -> bool:
    relative = Path(relative)
    parts = tuple(part.casefold() for part in relative.parts)
    if len(parts) == 1:
        return relative.name.casefold() in _REQUIRED_ROOT_FILES
    if len(parts) == 3 and parts[:2] == ("lib", "mlt"):
        return relative.name.casefold() in _REQUIRED_MLT_MODULES
    if parts == ("lib", "qt6", "platforms", "qwindows.dll"):
        return True
    return len(parts) >= 2 and parts[:2] == ("share", "mlt")


def prune_media_runtime_carrier(carrier_root: Path | str) -> int:
    """Delete carrier files outside the audited UV MLT/FFmpeg closure.

    The acquisition tree has already passed symlink/non-regular validation in
    stage_windows_release before this runs. This function only narrows a staged
    copy, so a failure can never mutate the downloaded source carrier.
    """

    root = Path(carrier_root)
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("staged media carrier root is missing or invalid")

    removed = 0
    for candidate in sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if not carrier_path_is_required(candidate.relative_to(root)):
            candidate.unlink()
            removed += 1

    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass
    return removed


def exact_closure_root_files() -> list[str]:
    return sorted(_REQUIRED_ROOT_FILES)
