#!/usr/bin/env python3
"""Stage the immutable Windows payload and attach exact native/legal evidence."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
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
_WEBVIEW2_RS_REPOSITORY = "https://github.com/wravery/webview2-rs"
_WEBVIEW2_RS_LICENSE = _ROOT / "packaging" / "licenses" / "webview2-rs.LICENSE"
_WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
_WEBVIEW2_BOOTSTRAPPER_ENTRYPOINT = "prerequisites/MicrosoftEdgeWebview2Setup.exe"
_WEBVIEW2_RUNTIME_CHECK_ATTEMPTS = 12
_WEBVIEW2_RUNTIME_CHECK_DELAY_SECONDS = 5.0


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


def _run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a release command without polluting the staging JSON stdout channel."""
    try:
        result = subprocess.run(
            command,
            cwd=_ROOT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except OSError as exc:
        raise _core.WindowsReleaseStageError(
            f"desktop release command could not start: {command[0]}"
        ) from exc
    if result.returncode != 0:
        combined = "\n".join(item for item in (result.stdout, result.stderr) if item).strip()
        detail = ": " + combined[-1600:] if combined else ""
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


def _cargo(rust_version: str, *args: str) -> subprocess.CompletedProcess[str]:
    return _run_checked(["rustup", "run", rust_version, "cargo", *args])


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
        ["rustup", "run", rust_version, "rustc", "--version"]
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

        repository = str(package.get("repository") or "").rstrip("/")
        if (
            not license_files
            and repository == _WEBVIEW2_RS_REPOSITORY
            and license_expression == "MIT"
        ):
            if not _WEBVIEW2_RS_LICENSE.is_file() or _WEBVIEW2_RS_LICENSE.is_symlink():
                raise _core.WindowsReleaseStageError(
                    "vendored upstream webview2-rs MIT license snapshot is missing"
                )
            license_files.append(_WEBVIEW2_RS_LICENSE)

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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stage_and_provision_webview2_bootstrapper(output: Path, desktop: Path) -> list[str]:
    target = output.joinpath(*_WEBVIEW2_BOOTSTRAPPER_ENTRYPOINT.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        _WEBVIEW2_BOOTSTRAPPER_URL,
        headers={"User-Agent": "UV-Studio-Release/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except (OSError, urllib.error.URLError) as exc:
        raise _core.WindowsReleaseStageError("could not download Microsoft WebView2 bootstrapper") from exc
    if target.is_symlink() or not target.is_file() or target.stat().st_size <= 0:
        raise _core.WindowsReleaseStageError("downloaded WebView2 bootstrapper is missing or empty")

    powershell = shutil.which("pwsh.exe") or shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        raise _core.WindowsReleaseStageError("PowerShell is required to validate WebView2 Authenticode")
    signature_script = target.parent / ".verify-webview2-authenticode.ps1"
    signature_script.write_text(
        "param([Parameter(Mandatory=$true)][string]$Path)\n"
        "$ErrorActionPreference='Stop'\n"
        "$s=Get-AuthenticodeSignature -LiteralPath $Path\n"
        "[ordered]@{\n"
        "  status=[string]$s.Status\n"
        "  subject=if($s.SignerCertificate){[string]$s.SignerCertificate.Subject}else{$null}\n"
        "  thumbprint=if($s.SignerCertificate){[string]$s.SignerCertificate.Thumbprint}else{$null}\n"
        "} | ConvertTo-Json -Compress\n",
        encoding="utf-8",
    )
    try:
        signature_result = _run_checked(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(signature_script),
                "-Path",
                str(target),
            ]
        )
    finally:
        signature_script.unlink(missing_ok=True)
    try:
        signature = json.loads(signature_result.stdout)
    except json.JSONDecodeError as exc:
        raise _core.WindowsReleaseStageError("WebView2 Authenticode evidence was not JSON") from exc
    subject = str(signature.get("subject") or "") if isinstance(signature, dict) else ""
    if not isinstance(signature, dict) or str(signature.get("status")) != "Valid":
        raise _core.WindowsReleaseStageError("WebView2 bootstrapper Authenticode status is not Valid")
    if re.match(r"^CN=Microsoft Corporation(?:,|$)", subject) is None:
        raise _core.WindowsReleaseStageError(
            f"unexpected WebView2 bootstrapper signer: {subject or '<missing>'}"
        )

    legal_root = output / "legal" / "prerequisites"
    legal_root.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema_version": 1,
        "name": "Microsoft Edge WebView2 Evergreen Bootstrapper",
        "source_url": _WEBVIEW2_BOOTSTRAPPER_URL,
        "sha256": _sha256_file(target),
        "authenticode_status": "Valid",
        "signer_subject": subject,
        "signer_thumbprint": str(signature.get("thumbprint") or ""),
        "release_path": _WEBVIEW2_BOOTSTRAPPER_ENTRYPOINT,
    }
    evidence_path = legal_root / "webview2-bootstrapper.json"

    # Provision the hosted runner from the exact authenticated bytes that are now
    # staged for the installer. This is machine setup, not a release component.
    install = subprocess.run(
        [str(target), "/silent", "/install"],
        cwd=target.parent,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    if install.returncode != 0:
        raise _core.WindowsReleaseStageError(
            f"WebView2 bootstrapper failed on release runner with exit {install.returncode}"
        )

    runtime_probe_attempts: list[int] = []
    runtime_ready = False
    for attempt in range(1, _WEBVIEW2_RUNTIME_CHECK_ATTEMPTS + 1):
        runtime = subprocess.run(
            [str(desktop), "--runtime-check"],
            cwd=desktop.parent,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        runtime_probe_attempts.append(runtime.returncode)
        if runtime.returncode == 0:
            runtime_ready = True
            break
        if attempt < _WEBVIEW2_RUNTIME_CHECK_ATTEMPTS:
            time.sleep(_WEBVIEW2_RUNTIME_CHECK_DELAY_SECONDS)
    if not runtime_ready:
        raise _core.WindowsReleaseStageError(
            "WebView2 Runtime is unavailable after authenticated prerequisite provisioning; "
            f"runtime-check exits={runtime_probe_attempts}"
        )

    evidence["runtime_probe_attempts"] = runtime_probe_attempts
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return [evidence_path.relative_to(output).as_posix()]


def stage_windows_release(**kwargs):
    output = Path(kwargs["output_root"]).expanduser()
    desktop_executable = kwargs.pop("desktop_executable", None)
    prepared_desktop: Path | str | None = desktop_executable
    prepared_metadata: tuple[dict[str, object], str, Path] | None = None

    # Build and validate the exact Rust graph before creating the release output.
    if _desktop_release_markers() is not None:
        desktop, metadata, rustc_version, cargo_lock = _build_exact_desktop_host()
        prepared_desktop = desktop
        prepared_metadata = (metadata, rustc_version, cargo_lock)

    result = _core.stage_windows_release(**kwargs)
    try:
        staged_desktop: Path | None = None
        if prepared_desktop is not None:
            target = output.joinpath(*_DESKTOP_ENTRYPOINT.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_core._require_file(prepared_desktop, "Rust desktop host executable"), target)
            if not target.is_file() or target.is_symlink() or target.stat().st_size <= 0:
                raise _core.WindowsReleaseStageError("staged Rust desktop host is missing or invalid")
            staged_desktop = target
            result["entrypoints"]["desktop"] = _DESKTOP_ENTRYPOINT
            if prepared_metadata is not None:
                metadata, rustc_version, cargo_lock = prepared_metadata
                result["legal_files"].extend(
                    _stage_desktop_legal(
                        output,
                        metadata=metadata,
                        rustc_version=rustc_version,
                        cargo_lock=cargo_lock,
                    )
                )
        elif _desktop_release_markers() is not None:
            raise _core.WindowsReleaseStageError("validated release omitted the Rust desktop host")

        if staged_desktop is not None and _desktop_release_markers() is not None:
            result["legal_files"].extend(
                _stage_and_provision_webview2_bootstrapper(output, staged_desktop)
            )

        result["legal_files"].extend(_stage_backend_native_legal_from_release_environment(output))
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
