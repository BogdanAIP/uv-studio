#!/usr/bin/env python3
"""Exact audited file closure for the Stage 9 Shotcut acquisition carrier."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MEDIA_COMPONENT_MANIFEST = (
    ROOT / "packaging" / "media-runtime-components.windows-x86_64.json"
)
_DEFAULT_MEDIA_NOTICE = ROOT / "packaging" / "media-runtime-NOTICE.md"

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
_RUNTIME_ENTRYPOINT_NAMES = frozenset({"ffmpeg.exe", "ffprobe.exe", "melt.exe"})


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


def _unique_runtime_entrypoints(root: Path) -> set[tuple[str, ...]]:
    matches: dict[str, list[Path]] = {name: [] for name in _RUNTIME_ENTRYPOINT_NAMES}
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        name = candidate.name.casefold()
        if name in matches:
            matches[name].append(candidate)

    required: set[tuple[str, ...]] = set()
    for name, paths in matches.items():
        if len(paths) > 1:
            locations = ", ".join(
                sorted(path.relative_to(root).as_posix() for path in paths)
            )
            raise RuntimeError(
                f"staged media carrier contains duplicate {name} entrypoints: {locations}"
            )
        if paths:
            required.add(
                tuple(part.casefold() for part in paths[0].relative_to(root).parts)
            )
    return required


def _is_product_release_carrier(root: Path) -> bool:
    """True only for the exact Stage 9 staged layout, never for acquisition source trees."""
    if len(root.parents) < 3:
        return False
    return (
        root.name.casefold() == "shotcut"
        and root.parent.name.casefold() == "media"
        and root.parent.parent.name.casefold() == "runtime"
    )


def _stage_product_legal_bundle(root: Path) -> None:
    if not _is_product_release_carrier(root):
        return
    try:
        if __package__:
            from tools.media_runtime_legal import stage_media_runtime_legal_bundle
        else:
            from media_runtime_legal import stage_media_runtime_legal_bundle

        stage_media_runtime_legal_bundle(
            release_root=root.parents[2],
            media_root=root.parent,
            manifest_file=_DEFAULT_MEDIA_COMPONENT_MANIFEST,
            notice_file=_DEFAULT_MEDIA_NOTICE,
        )
    except Exception as exc:  # stage_windows_release converts RuntimeError to its release error
        raise RuntimeError(f"media runtime legal/provenance gate failed: {exc}") from exc


def prune_media_runtime_carrier(carrier_root: Path | str) -> int:
    """Delete carrier files outside the audited UV MLT/FFmpeg closure.

    The acquisition tree has already passed symlink/non-regular validation in
    stage_windows_release before this runs. This function only narrows a staged
    copy, so a failure can never mutate the downloaded source carrier. Runtime
    entrypoints are retained at their unique carrier-relative location so staging
    does not accidentally couple the release contract to one archive directory
    layout.

    In the exact product release layout this also verifies that every surviving
    media PE belongs to exactly one reviewed component and stages that component
    map plus its notice into ``legal/media-runtime`` before D-044 hashes payload.
    """
    root = Path(carrier_root)
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("staged media carrier root is missing or invalid")

    runtime_entrypoints = _unique_runtime_entrypoints(root)
    removed = 0
    for candidate in sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        relative = candidate.relative_to(root)
        folded = tuple(part.casefold() for part in relative.parts)
        if folded not in runtime_entrypoints and not carrier_path_is_required(relative):
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

    _stage_product_legal_bundle(root)
    return removed


def exact_closure_root_files() -> list[str]:
    return sorted(_REQUIRED_ROOT_FILES)


def exact_closure_carrier_pe_files() -> list[str]:
    """Reviewed PE paths relative to the Shotcut carrier root."""
    files = [
        name
        for name in _REQUIRED_ROOT_FILES
        if Path(name).suffix.casefold() in {".dll", ".exe"}
    ]
    files.extend(f"lib/mlt/{name}" for name in _REQUIRED_MLT_MODULES)
    files.append("lib/qt6/platforms/qwindows.dll")
    return sorted(files, key=str.casefold)
