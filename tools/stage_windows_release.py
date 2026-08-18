#!/usr/bin/env python3
"""Stage proven Windows release components into one immutable UV Studio payload."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Sequence


class WindowsReleaseStageError(RuntimeError):
    pass


ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_UV_LICENSE = ROOT / "LICENSE"
_DEFAULT_THIRD_PARTY_NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
_DEFAULT_RELEASE_PROFILE = ROOT / "packaging" / "runtime-profile.windows-x86_64.json"

# The Stage 9 MLT boundary is derived from the XML that MLTTimelineAdapter emits:
# XML loading, core playlist/tractor graph construction, avformat input/output and
# melt's non-XML-consumer qtcrop preflight. Everything else remains excluded until
# UV starts emitting a service that needs it and the release closure is reviewed.
_MLT_REQUIRED_MODULE_NAMES = frozenset(
    {
        "libmltavformat.dll",
        "libmltcore.dll",
        "libmltqt6.dll",
        "libmltxml.dll",
    }
)
_MLT_REQUIRED_CARRIER_FILES = (
    "lib/mlt/libmltavformat.dll",
    "lib/mlt/libmltcore.dll",
    "lib/mlt/libmltqt6.dll",
    "lib/mlt/libmltxml.dll",
    "share/mlt/avformat/consumer_avformat.yml",
    "share/mlt/avformat/producer_avformat-novalidate.yml",
    "share/mlt/core/loader.dict",
    "share/mlt/core/loader.ini",
    "share/mlt/qt6/filter_qtcrop.yml",
)

# Media acquisition archives are carriers, not the canonical UV Studio runtime.
# Exclusions are evidence-backed against the UV-owned MLT projection/render path.
# Qt runtime DLL/plugins and top-level shared media libraries remain untouched in
# this pass because some of them may be discovered dynamically at runtime.
_MEDIA_EXCLUDED_SEGMENT_SEQUENCES: tuple[tuple[str, ...], ...] = (
    ("bin", "qt", "test"),
    ("share", "shotcut"),
    ("lib", "frei0r-1"),
    ("lib", "ladspa"),
    ("lib", "qml"),
)
_MEDIA_EXCLUDED_FILE_NAMES = frozenset(
    {
        "ffplay.exe",
        "glaxnimate.exe",
        "shotcut.exe",
        "whisper-cli.exe",
    }
)
_MEDIA_EXCLUSION_RULES = (
    "**/bin/Qt/test/**",
    "**/share/shotcut/**",
    "**/ffplay.exe",
    "**/glaxnimate.exe",
    "**/shotcut.exe",
    "**/whisper-cli.exe",
    "**/lib/frei0r-1/**",
    "**/lib/ladspa/**",
    "**/lib/qml/**",
    "**/lib/mlt/libmlt*.dll except UV service-closure allowlist",
)
_MANDATORY_LEGAL_TARGETS = {
    "uv_license": "legal/UV-STUDIO-LICENSE.txt",
    "third_party_notices": "legal/THIRD-PARTY-NOTICES.md",
    "release_profile": "legal/release-inputs.windows-x86_64.json",
}
_NODE_LICENSE_TARGET = "legal/node/LICENSE.txt"


def _require_directory(path: Path | str, label: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise WindowsReleaseStageError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WindowsReleaseStageError(f"{label} is missing") from exc
    if not resolved.is_dir():
        raise WindowsReleaseStageError(f"{label} must be a real directory")
    return resolved


def _require_file(path: Path | str, label: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise WindowsReleaseStageError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WindowsReleaseStageError(f"{label} is missing") from exc
    if not resolved.is_file():
        raise WindowsReleaseStageError(f"{label} must be a regular file")
    return resolved


def _reject_symlinks(root: Path, label: str) -> None:
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in directories:
            candidate = current_path / name
            if candidate.is_symlink():
                relative = candidate.relative_to(root).as_posix()
                raise WindowsReleaseStageError(
                    f"{label} contains symlink directory: {relative}"
                )
        for name in names:
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                raise WindowsReleaseStageError(
                    f"{label} contains symlink file: {relative}"
                )
            if not candidate.is_file():
                raise WindowsReleaseStageError(
                    f"{label} contains non-regular file: {relative}"
                )


def _relative_file(path: Path, root: Path, label: str) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise WindowsReleaseStageError(f"{label} must be inside media root") from exc
    if not relative.parts:
        raise WindowsReleaseStageError(f"{label} must be a file inside media root")
    return relative.as_posix()


def _copy_tree(source: Path, target: Path, label: str) -> None:
    _reject_symlinks(source, label)
    shutil.copytree(source, target, symlinks=False)


def _contains_segment_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    folded = tuple(part.casefold() for part in parts)
    width = len(sequence)
    return any(
        folded[index : index + width] == sequence
        for index in range(len(folded) - width + 1)
    )


def _is_mlt_module_file(relative: Path) -> bool:
    parts = relative.parts
    if not relative.name.casefold().startswith("libmlt") or relative.suffix.casefold() != ".dll":
        return False
    folded = tuple(part.casefold() for part in parts)
    return len(parts) >= 3 and folded[-3:-1] == ("lib", "mlt")


def _media_path_is_excluded(relative: Path) -> bool:
    parts = relative.parts
    if relative.name.casefold() in _MEDIA_EXCLUDED_FILE_NAMES:
        return True
    if _is_mlt_module_file(relative):
        return relative.name.casefold() not in _MLT_REQUIRED_MODULE_NAMES
    return any(
        _contains_segment_sequence(parts, sequence)
        for sequence in _MEDIA_EXCLUDED_SEGMENT_SEQUENCES
    )


def _excluded_media_file_count(media_root: Path) -> int:
    return sum(
        1
        for candidate in media_root.rglob("*")
        if candidate.is_file()
        and _media_path_is_excluded(candidate.relative_to(media_root))
    )


def _copy_media_runtime(source: Path, target: Path) -> int:
    # Security validation covers the full acquisition tree, including excluded
    # content, before anything is staged.
    _reject_symlinks(source, "media runtime")
    excluded_file_count = _excluded_media_file_count(source)

    def ignore(current: str, names: list[str]) -> set[str]:
        current_path = Path(current)
        ignored: set[str] = set()
        for name in names:
            candidate = current_path / name
            relative = candidate.relative_to(source)
            if _media_path_is_excluded(relative):
                ignored.add(name)
        return ignored

    shutil.copytree(source, target, symlinks=False, ignore=ignore)
    return excluded_file_count


def _find_mlt_carrier_root(media_root: Path, melt: Path) -> Path:
    candidate = melt.parent
    while True:
        if (candidate / "lib" / "mlt").is_dir():
            return candidate
        if candidate == media_root:
            break
        if media_root not in candidate.parents:
            break
        candidate = candidate.parent
    raise WindowsReleaseStageError(
        "MLT executable is not inside a carrier containing lib/mlt"
    )


def _require_mlt_service_closure(media_root: Path, melt: Path) -> tuple[Path, list[str]]:
    carrier_root = _find_mlt_carrier_root(media_root, melt)
    missing: list[str] = []
    for relative in _MLT_REQUIRED_CARRIER_FILES:
        candidate = carrier_root.joinpath(*relative.split("/"))
        if not candidate.is_file() or candidate.is_symlink():
            missing.append(relative)
    if missing:
        raise WindowsReleaseStageError(
            "MLT UV service closure is incomplete: " + ", ".join(missing)
        )
    return carrier_root, list(_MLT_REQUIRED_CARRIER_FILES)


def _copy_legal_file(source: Path, target: Path, relative: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if not target.is_file() or target.is_symlink() or target.stat().st_size <= 0:
        raise WindowsReleaseStageError(
            f"staged legal/provenance file is missing or empty: {relative}"
        )


def _stage_legal_files(
    output: Path,
    *,
    uv_license: Path,
    third_party_notices: Path,
    release_profile: Path,
    node_license: Path | None,
) -> list[str]:
    sources = {
        "uv_license": uv_license,
        "third_party_notices": third_party_notices,
        "release_profile": release_profile,
    }
    staged: list[str] = []
    for key, relative in _MANDATORY_LEGAL_TARGETS.items():
        target = output.joinpath(*relative.split("/"))
        _copy_legal_file(sources[key], target, relative)
        staged.append(relative)
    if node_license is not None:
        target = output.joinpath(*_NODE_LICENSE_TARGET.split("/"))
        _copy_legal_file(node_license, target, _NODE_LICENSE_TARGET)
        staged.append(_NODE_LICENSE_TARGET)
    return staged


def stage_windows_release(
    *,
    backend_root: Path | str,
    frontend_root: Path | str,
    node_executable: Path | str,
    media_root: Path | str,
    ffmpeg_executable: Path | str,
    ffprobe_executable: Path | str,
    mlt_executable: Path | str,
    output_root: Path | str,
    node_license_file: Path | str | None = None,
    uv_license_file: Path | str = _DEFAULT_UV_LICENSE,
    third_party_notices_file: Path | str = _DEFAULT_THIRD_PARTY_NOTICES,
    release_profile_file: Path | str = _DEFAULT_RELEASE_PROFILE,
) -> dict[str, object]:
    backend = _require_directory(backend_root, "backend component")
    frontend = _require_directory(frontend_root, "frontend component")
    node = _require_file(node_executable, "Node executable")
    node_license = (
        None
        if node_license_file is None
        else _require_file(node_license_file, "Node license")
    )
    media = _require_directory(media_root, "media runtime")
    ffmpeg = _require_file(ffmpeg_executable, "FFmpeg executable")
    ffprobe = _require_file(ffprobe_executable, "FFprobe executable")
    melt = _require_file(mlt_executable, "MLT executable")
    uv_license = _require_file(uv_license_file, "UV Studio license")
    third_party_notices = _require_file(
        third_party_notices_file, "third-party notices"
    )
    release_profile = _require_file(release_profile_file, "release input profile")

    backend_entry = backend / "uv-studio-backend.exe"
    if not backend_entry.is_file() or backend_entry.is_symlink():
        raise WindowsReleaseStageError(
            "backend component is missing regular uv-studio-backend.exe"
        )
    frontend_entry = frontend / "server.js"
    if not frontend_entry.is_file() or frontend_entry.is_symlink():
        raise WindowsReleaseStageError("frontend component is missing regular server.js")

    ffmpeg_relative = _relative_file(ffmpeg, media, "FFmpeg executable")
    ffprobe_relative = _relative_file(ffprobe, media, "FFprobe executable")
    melt_relative = _relative_file(melt, media, "MLT executable")
    for label, relative in (
        ("FFmpeg executable", ffmpeg_relative),
        ("FFprobe executable", ffprobe_relative),
        ("MLT executable", melt_relative),
    ):
        if _media_path_is_excluded(Path(relative)):
            raise WindowsReleaseStageError(
                f"{label} is inside a non-runtime media exclusion: {relative}"
            )

    mlt_carrier_root, mlt_service_files = _require_mlt_service_closure(media, melt)
    mlt_carrier_relative = mlt_carrier_root.relative_to(media)

    output = Path(output_root).expanduser()
    if output.exists() or output.is_symlink():
        raise WindowsReleaseStageError(
            "Windows release staging output must not already exist"
        )

    # Validate all source trees before creating the destination so a rejected source
    # cannot leave a plausible-looking partial release behind.
    _reject_symlinks(backend, "backend component")
    _reject_symlinks(frontend, "frontend component")
    _reject_symlinks(media, "media runtime")

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir()
        _copy_tree(backend, output / "backend", "backend component")
        _copy_tree(frontend, output / "frontend", "frontend component")
        node_target = output / "runtime" / "node" / "node.exe"
        node_target.parent.mkdir(parents=True)
        shutil.copy2(node, node_target)
        media_target = output / "runtime" / "media"
        excluded_media_file_count = _copy_media_runtime(media, media_target)
        legal_files = _stage_legal_files(
            output,
            uv_license=uv_license,
            third_party_notices=third_party_notices,
            release_profile=release_profile,
            node_license=node_license,
        )

        entrypoints = {
            "backend": "backend/uv-studio-backend.exe",
            "frontend": "frontend/server.js",
            "node": "runtime/node/node.exe",
            "ffmpeg": f"runtime/media/{ffmpeg_relative}",
            "ffprobe": f"runtime/media/{ffprobe_relative}",
            "mlt": f"runtime/media/{melt_relative}",
        }
        for component_id, relative in entrypoints.items():
            candidate = output.joinpath(*relative.split("/"))
            if not candidate.is_file() or candidate.is_symlink():
                raise WindowsReleaseStageError(
                    f"staged {component_id} entrypoint is missing or invalid: {relative}"
                )

        staged_carrier = media_target / mlt_carrier_relative
        for relative in mlt_service_files:
            candidate = staged_carrier.joinpath(*relative.split("/"))
            if not candidate.is_file() or candidate.is_symlink():
                raise WindowsReleaseStageError(
                    f"staged MLT UV service closure is missing: {relative}"
                )

        file_count = sum(1 for path in output.rglob("*") if path.is_file())
        media_file_count = sum(
            1
            for path in media_target.rglob("*")
            if path.is_file()
        )
        return {
            "ok": True,
            "entrypoints": entrypoints,
            "file_count": file_count,
            "media_file_count": media_file_count,
            "excluded_media_file_count": excluded_media_file_count,
            "media_exclusion_rules": list(_MEDIA_EXCLUSION_RULES),
            "mlt_required_modules": sorted(_MLT_REQUIRED_MODULE_NAMES),
            "mlt_service_closure_files": mlt_service_files,
            "legal_files": legal_files,
        }
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", type=Path, required=True)
    parser.add_argument("--frontend-root", type=Path, required=True)
    parser.add_argument("--node-executable", type=Path, required=True)
    parser.add_argument("--node-license", type=Path)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--ffmpeg-executable", type=Path, required=True)
    parser.add_argument("--ffprobe-executable", type=Path, required=True)
    parser.add_argument("--mlt-executable", type=Path, required=True)
    parser.add_argument("--uv-license", type=Path, default=_DEFAULT_UV_LICENSE)
    parser.add_argument(
        "--third-party-notices",
        type=Path,
        default=_DEFAULT_THIRD_PARTY_NOTICES,
    )
    parser.add_argument(
        "--release-profile", type=Path, default=_DEFAULT_RELEASE_PROFILE
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
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
    except (OSError, WindowsReleaseStageError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
