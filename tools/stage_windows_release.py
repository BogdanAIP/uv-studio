#!/usr/bin/env python3
"""Stage the immutable Windows payload and attach exact native/legal evidence."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

if __package__:
    from tools import stage_windows_release_core as _core
else:
    import stage_windows_release_core as _core

# Preserve the public and test-visible surface of the proven Stage 9 staging
# implementation while keeping this file as a thin orchestration boundary.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


_ROOT = Path(__file__).resolve().parents[1]
_EXPECTED_BACKEND_NATIVE_PE = 78
_EXPECTED_BACKEND_NATIVE_GROUPS = 14
_DESKTOP_ENTRYPOINT = "desktop/uv-studio-desktop.exe"
_DESKTOP_MANIFEST = _ROOT / "desktop-host" / "Cargo.toml"
_DESKTOP_TOOLCHAIN = _ROOT / "desktop-host" / "rust-toolchain.toml"


def _stage_backend_native_legal_from_release_environment(output: Path) -> list[str]:
    """Stage exact backend PE/PYD legal evidence for a validated release build."""
    if not os.environ.get("UV_PYINSTALLER_VERSION"):
        return []
    legal_root = output / "legal" / "backend-native"
    try:
        if __package__:
            from tools.backend_native_legal import (
                BackendNativeLegalError,
                stage_backend_native_legal,
            )
        else:
            from backend_native_legal import (
                BackendNativeLegalError,
                stage_backend_native_legal,
            )

        result = stage_backend_native_legal(release_root=output)
    except (OSError, UnicodeError, BackendNativeLegalError) as exc:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise _core.WindowsReleaseStageError(
            f"backend native legal/provenance gate failed: {exc}"
        ) from exc

    if result.get("pe_count") != _EXPECTED_BACKEND_NATIVE_PE:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise _core.WindowsReleaseStageError(
            "backend native PE count drifted: "
            f"expected {_EXPECTED_BACKEND_NATIVE_PE}, got {result.get('pe_count')!r}"
        )
    if result.get("group_count") != _EXPECTED_BACKEND_NATIVE_GROUPS:
        shutil.rmtree(legal_root, ignore_errors=True)
        raise _core.WindowsReleaseStageError(
            "backend native legal group count drifted: "
            f"expected {_EXPECTED_BACKEND_NATIVE_GROUPS}, got {result.get('group_count')!r}"
        )
    return sorted(
        (
            path.relative_to(output).as_posix()
            for path in legal_root.rglob("*")
            if path.is_file()
        ),
        key=str.casefold,
    )


def _run_checked(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=_ROOT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=capture,
        )
    except OSError as exc:
        raise _core.WindowsReleaseStageError(
            f"desktop release command could not start: {command[0]}"
        ) from exc
    if result.returncode != 0:
        detail = ""
        if capture:
            combined = "\n".join(item for item in (result.stdout, result.stderr) if item).strip()
            if combined:
                detail = ": " + combined[-1200:]
        raise _core.WindowsReleaseStageError(
            f"desktop release command failed with exit {result.returncode}: {' '.join(command)}{detail}"
        )
    return result


def _desktop_release_markers() -> tuple[str, Path, str] | None:
    rust_version = os.environ.get("UV_RUST_VERSION", "").strip()
    cargo_lock_value = os.environ.get("UV_DESKTOP_CARGO_LOCK", "").strip()
    webview_version = os.environ.get("UV_WEBVIEW2_COM_VERSION", "").strip()
    markers = (rust_version, cargo_lock_value, webview_version)
    if not any(markers):
        return None
    if not all(markers):
        raise _core.WindowsReleaseStageError(
            "Rust desktop release requires rust version, Cargo.lock and webview2-com version together"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", rust_version):
        raise _core.WindowsReleaseStageError("Rust release version is not a safe toolchain token")
    cargo_lock = (_ROOT / cargo_lock_value).resolve()
    try:
        cargo_lock.relative_to(_ROOT)
    except ValueError as exc:
        raise _core.WindowsReleaseStageError("desktop Cargo.lock escaped repository root") from exc
    if not cargo_lock.is_file() or cargo_lock.is_symlink():
        raise _core.WindowsReleaseStageError("committed desktop Cargo.lock is missing")
    return rust_version, cargo_lock, webview_version


def _cargo(rust_version: str, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return _run_checked(
        ["rustup", "run", rust_version, "cargo", *args],
        capture=capture,
    )


def _build_exact_desktop_host() -> tuple[Path, dict[str, object], str, Path]:
    markers = _desktop_release_markers()
    if markers is None:
        raise _core.WindowsReleaseStageError("validated release profile did not export Rust desktop inputs")
    rust_version, cargo_lock, expected_webview_version = markers

    _run_checked(
        [
            "rustup",
            "toolchain",
            "install",
            rust_version,
            "--profile",
            "minimal",
            "--target",
            "x86_64-pc-windows-msvc",
        ]
    )
    rustc = _run_checked(
        ["rustup", "run", rust_version, "rustc", "--version"],
        capture=True,
    ).stdout.strip()
    if not rustc.startswith(f"rustc {rust_version} "):
        raise _core.WindowsReleaseStageError(
            f"unexpected Rust compiler for desktop host: {rustc!r}"
        )

    common = ("--locked", "--manifest-path", str(_DESKTOP_MANIFEST))
    _cargo(rust_version, "test", *common)
    _cargo(rust_version, "build", "--release", *common)
    metadata_result = _cargo(
        rust_version,
        "metadata",
        *common,
        "--format-version",
        "1",
        capture=True,
    )
    try:
        metadata = json.loads(metadata_result.stdout)
    except json.JSONDecodeError as exc:
        raise _core.WindowsReleaseStageError("Cargo metadata was not valid JSON") from exc
    if not isinstance(metadata, dict) or not isinstance(metadata.get("packages"), list):
        raise _core.WindowsReleaseStageError("Cargo metadata had an invalid package graph")

    webview_packages = [
        package
        for package in metadata["packages"]
        if isinstance(package, dict) and package.get("name") == "webview2-com"
    ]
    if len(webview_packages) != 1 or webview_packages[0].get("version") != expected_webview_version:
        raise _core.WindowsReleaseStageError(
            "Cargo graph did not resolve the release-profile webview2-com version"
        )

    desktop = _ROOT / "desktop-host" / "target" / "release" / "uv-studio-desktop.exe"
    if not desktop.is_file() or desktop.is_symlink() or desktop.stat().st_size <= 0:
        raise _core.WindowsReleaseStageError("Rust desktop host build did not produce a regular executable")
    runtime_check = subprocess.run(
        [str(desktop), "--runtime-check"],
        cwd=desktop.parent,
        check=False,
    )
    if runtime_check.returncode != 0:
        raise _core.WindowsReleaseStageError(
            "Windows release runner does not provide the required WebView2 Runtime"
        )
    return desktop.resolve(), metadata, rustc, cargo_lock


def _stage_desktop_legal(
    output: Path,
    *,
    metadata: dict[str, object],
    rustc_version: str,
    cargo_lock: Path,
) -> list[str]:
    legal_root = output / "legal" / "desktop-rust"
    legal_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_DESKTOP_MANIFEST, legal_root / "Cargo.toml")
    shutil.copy2(cargo_lock, legal_root / "Cargo.lock")
    shutil.copy2(_DESKTOP_TOOLCHAIN, legal_root / "rust-toolchain.toml")
    (legal_root / "rustc-version.txt").write_text(rustc_version + "\n", encoding="utf-8")
    (legal_root / "cargo-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    packages = metadata.get("packages")
    assert isinstance(packages, list)
    third_party = [
        package
        for package in packages
        if isinstance(package, dict) and package.get("source") is not None
    ]
    if not third_party:
        raise _core.WindowsReleaseStageError("Cargo metadata contained no third-party desktop packages")

    crate_root = legal_root / "crates"
    for package in sorted(third_party, key=lambda item: (str(item.get("name")), str(item.get("version")))):
        name = str(package.get("name", "")).strip()
        version = str(package.get("version", "")).strip()
        license_expression = str(package.get("license") or "").strip()
        manifest_path = Path(str(package.get("manifest_path", "")))
        if not name or not version or not license_expression or not manifest_path.is_file():
            raise _core.WindowsReleaseStageError(
                f"Cargo package provenance is incomplete for {name or '<unknown>'} {version or '<unknown>'}"
            )
        source_root = manifest_path.parent
        license_files: list[Path] = []
        explicit = package.get("license_file")
        if explicit:
            candidate = Path(str(explicit))
            if candidate.is_file():
                license_files.append(candidate)
        if not license_files:
            for pattern in ("LICENSE*", "COPYING*", "NOTICE*"):
                license_files.extend(
                    path for path in source_root.glob(pattern) if path.is_file() and not path.is_symlink()
                )
        unique = sorted({path.resolve() for path in license_files}, key=lambda path: path.name.casefold())
        if not unique:
            raise _core.WindowsReleaseStageError(
                f"Cargo package has no staged license text: {name} {version} ({license_expression})"
            )
        target = crate_root / f"{name}-{version}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "LICENSE-EXPRESSION.txt").write_text(
            license_expression + "\n", encoding="utf-8"
        )
        for source in unique:
            shutil.copy2(source, target / source.name)

    return sorted(
        (path.relative_to(output).as_posix() for path in legal_root.rglob("*") if path.is_file()),
        key=str.casefold,
    )


def _stage_desktop_host(
    output: Path,
    source: Path | str | None,
) -> tuple[str | None, list[str]]:
    metadata: dict[str, object] | None = None
    rustc_version = ""
    cargo_lock: Path | None = None
    if _desktop_release_markers() is not None:
        desktop, metadata, rustc_version, cargo_lock = _build_exact_desktop_host()
    elif source is not None:
        desktop = _core._require_file(source, "Rust desktop host executable")
    else:
        return None, []

    target = output.joinpath(*_DESKTOP_ENTRYPOINT.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(desktop, target)
    if not target.is_file() or target.is_symlink() or target.stat().st_size <= 0:
        raise _core.WindowsReleaseStageError("staged Rust desktop host is missing or invalid")

    legal_files: list[str] = []
    if metadata is not None and cargo_lock is not None:
        legal_files = _stage_desktop_legal(
            output,
            metadata=metadata,
            rustc_version=rustc_version,
            cargo_lock=cargo_lock,
        )
    return _DESKTOP_ENTRYPOINT, legal_files


def stage_windows_release(**kwargs):
    output = Path(kwargs["output_root"]).expanduser()
    desktop_executable = kwargs.pop("desktop_executable", None)
    # Build/validate the desktop binary before touching the release output so a
    # rejected Rust graph cannot leave a plausible-looking partial payload.
    prepared_desktop: Path | str | None = desktop_executable
    prepared_metadata: tuple[dict[str, object], str, Path] | None = None
    if _desktop_release_markers() is not None:
        desktop, metadata, rustc_version, cargo_lock = _build_exact_desktop_host()
        prepared_desktop = desktop
        prepared_metadata = (metadata, rustc_version, cargo_lock)

    result = _core.stage_windows_release(**kwargs)
    try:
        desktop_entrypoint: str | None = None
        desktop_legal: list[str] = []
        if prepared_desktop is not None:
            target = output.joinpath(*_DESKTOP_ENTRYPOINT.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_core._require_file(prepared_desktop, "Rust desktop host executable"), target)
            if not target.is_file() or target.is_symlink() or target.stat().st_size <= 0:
                raise _core.WindowsReleaseStageError("staged Rust desktop host is missing or invalid")
            desktop_entrypoint = _DESKTOP_ENTRYPOINT
            if prepared_metadata is not None:
                metadata, rustc_version, cargo_lock = prepared_metadata
                desktop_legal = _stage_desktop_legal(
                    output,
                    metadata=metadata,
                    rustc_version=rustc_version,
                    cargo_lock=cargo_lock,
                )
        if desktop_entrypoint is not None:
            result["entrypoints"]["desktop"] = desktop_entrypoint
        result["legal_files"].extend(desktop_legal)
        native_files = _stage_backend_native_legal_from_release_environment(output)
        result["legal_files"].extend(native_files)
        result["file_count"] = sum(1 for path in output.rglob("*") if path.is_file())
        return result
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = _core._parser()
    parser.add_argument("--desktop-executable", type=Path)
    args = parser.parse_args(argv)
    try:
        result = stage_windows_release(
            backend_root=args.backend_root,
            frontend_root=args.frontend_root,
            node_executable=args.node_executable,
            node_license_file=args.node_license,
            desktop_executable=args.desktop_executable,
            media_root=args.media_root,
            ffmpeg_executable=args.ffmpeg_executable,
            ffprobe_executable=args.ffprobe_executable,
            mlt_executable=args.mlt_executable,
            uv_license_file=args.uv_license,
            third_party_notices_file=args.third_party_notices,
            release_profile_file=args.release_profile,
            output_root=args.output,
        )
    except (OSError, _core.WindowsReleaseStageError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
