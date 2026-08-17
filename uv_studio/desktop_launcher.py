"""Native-Windows desktop launcher and process supervisor for packaged UV Studio."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .config import paths_overlap
from .release_manifest import (
    ReleaseManifestError,
    load_release_manifest,
    verify_release_tree,
)

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 3000
STARTUP_TIMEOUT_SECONDS = 90.0


class DesktopLauncherError(RuntimeError):
    """The packaged desktop application cannot be started safely."""


@dataclass(frozen=True)
class DesktopLaunchPlan:
    release_root: Path
    backend_executable: Path
    frontend_entrypoint: Path
    node_executable: Path

    @property
    def backend_url(self) -> str:
        return f"http://{BACKEND_HOST}:{BACKEND_PORT}"

    @property
    def frontend_url(self) -> str:
        return f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"


def infer_packaged_release_root(executable: Path | str | None = None) -> tuple[Path, Path]:
    if executable is None:
        if not getattr(sys, "frozen", False):
            raise DesktopLauncherError("desktop launcher requires the packaged UV Studio executable")
        executable_path = Path(sys.executable)
    else:
        executable_path = Path(executable)
    try:
        resolved_executable = executable_path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise DesktopLauncherError("packaged UV Studio executable could not be resolved") from exc
    if not resolved_executable.is_file() or resolved_executable.is_symlink():
        raise DesktopLauncherError("packaged UV Studio executable must be a regular file")
    if resolved_executable.parent.name != "backend":
        raise DesktopLauncherError("packaged UV Studio executable is outside the expected backend directory")
    return resolved_executable.parent.parent, resolved_executable


def _component_entrypoints(release_root: Path) -> dict[str, Path]:
    try:
        manifest = load_release_manifest(release_root)
        verification = verify_release_tree(manifest, release_root, verify_hashes=False)
    except (OSError, ReleaseManifestError) as exc:
        raise DesktopLauncherError("release manifest preflight failed") from exc
    if not verification["ok"]:
        problems = verification.get("problems", [])
        detail = "; ".join(str(item) for item in problems[:3])
        raise DesktopLauncherError(
            "installed application payload failed the release preflight"
            + (f": {detail}" if detail else "")
        )

    entrypoints: dict[str, Path] = {}
    for component in manifest.components:
        candidate = release_root.joinpath(*component.entrypoint.split("/"))
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise DesktopLauncherError(
                f"release component is unavailable: {component.component_id}"
            ) from exc
        if not resolved.is_file() or resolved.is_symlink():
            raise DesktopLauncherError(
                f"release component entrypoint is invalid: {component.component_id}"
            )
        entrypoints[component.component_id] = resolved
    return entrypoints


def build_launch_plan(
    release_root: Path | str,
    *,
    current_executable: Path | str | None = None,
) -> DesktopLaunchPlan:
    try:
        root = Path(release_root).expanduser().resolve(strict=True)
    except OSError as exc:
        raise DesktopLauncherError("release root could not be resolved") from exc
    if not root.is_dir() or root.is_symlink():
        raise DesktopLauncherError("release root must be a real directory")

    entrypoints = _component_entrypoints(root)
    backend = entrypoints["backend"]
    frontend = entrypoints["frontend"]
    node = entrypoints["node"]

    if current_executable is not None:
        try:
            current = Path(current_executable).expanduser().resolve(strict=True)
        except OSError as exc:
            raise DesktopLauncherError("current launcher executable could not be resolved") from exc
        if current != backend:
            raise DesktopLauncherError(
                "desktop launcher must execute from the manifest-owned backend entrypoint"
            )

    return DesktopLaunchPlan(
        release_root=root,
        backend_executable=backend,
        frontend_entrypoint=frontend,
        node_executable=node,
    )


def build_child_environment(
    plan: DesktopLaunchPlan,
    *,
    base_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if base_environment is None else base_environment)
    configured_user_data = environment.get("UV_STUDIO_USER_DATA_DIR", "").strip()
    if configured_user_data:
        user_data = Path(configured_user_data).expanduser().resolve()
    else:
        local_app_data = environment.get("LOCALAPPDATA", "").strip()
        if not local_app_data:
            raise DesktopLauncherError(
                "LOCALAPPDATA is unavailable; UV Studio cannot select its packaged user-data directory"
            )
        user_data = (Path(local_app_data).expanduser() / "UV Studio").resolve()
    if paths_overlap(user_data, plan.release_root):
        raise DesktopLauncherError(
            "UV Studio user data must not overlap the immutable application payload"
        )

    for variable, label in (
        ("UV_STUDIO_PROJECTS_DIR", "Project Store"),
        ("UV_STUDIO_CONFIG_DIR", "machine configuration"),
    ):
        configured = environment.get(variable, "").strip()
        if configured and paths_overlap(Path(configured).expanduser(), plan.release_root):
            raise DesktopLauncherError(
                f"UV Studio {label} override must not overlap the immutable application payload"
            )

    environment["UV_STUDIO_RELEASE_ROOT"] = str(plan.release_root)
    environment["UV_STUDIO_USER_DATA_DIR"] = str(user_data)
    environment["HOSTNAME"] = FRONTEND_HOST
    environment["PORT"] = str(FRONTEND_PORT)
    environment["NODE_ENV"] = "production"
    return environment


def port_is_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind((host, port))
        return True
    except OSError:
        return False


def require_desktop_ports_available() -> None:
    occupied: list[str] = []
    if not port_is_available(BACKEND_HOST, BACKEND_PORT):
        occupied.append(str(BACKEND_PORT))
    if not port_is_available(FRONTEND_HOST, FRONTEND_PORT):
        occupied.append(str(FRONTEND_PORT))
    if occupied:
        raise DesktopLauncherError(
            "UV Studio cannot start because required local port(s) are already in use: "
            + ", ".join(occupied)
        )


def _creation_flags() -> int:
    if os.name == "nt":
        return int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    return 0


def _start_children(
    plan: DesktopLaunchPlan,
    environment: Mapping[str, str],
) -> tuple[subprocess.Popen, subprocess.Popen]:
    try:
        backend = subprocess.Popen(
            [str(plan.backend_executable), "--backend-child"],
            cwd=str(plan.backend_executable.parent),
            env=dict(environment),
            shell=False,
            creationflags=_creation_flags(),
        )
    except OSError as exc:
        raise DesktopLauncherError("bundled backend process could not be started") from exc

    try:
        frontend = subprocess.Popen(
            [str(plan.node_executable), str(plan.frontend_entrypoint)],
            cwd=str(plan.frontend_entrypoint.parent),
            env=dict(environment),
            shell=False,
            creationflags=_creation_flags(),
        )
    except OSError as exc:
        _stop_process(backend)
        raise DesktopLauncherError("bundled frontend process could not be started") from exc
    return backend, frontend


def _request_json(url: str, *, timeout: float = 2.0) -> object:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise DesktopLauncherError("local UV Studio service returned an unexpected status")
        return json.loads(response.read().decode("utf-8"))


def _request_ok(url: str, *, timeout: float = 2.0) -> bool:
    request = urllib.request.Request(url, headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status == 200


def _raise_if_child_exited(
    backend: subprocess.Popen,
    frontend: subprocess.Popen,
) -> None:
    backend_code = backend.poll()
    if backend_code is not None:
        raise DesktopLauncherError(
            f"bundled backend stopped unexpectedly (exit code {backend_code})"
        )
    frontend_code = frontend.poll()
    if frontend_code is not None:
        raise DesktopLauncherError(
            f"bundled frontend stopped unexpectedly (exit code {frontend_code})"
        )


def _wait_until_ready(
    plan: DesktopLaunchPlan,
    backend: subprocess.Popen,
    frontend: subprocess.Popen,
    *,
    timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    backend_ready = False
    while time.monotonic() < deadline:
        _raise_if_child_exited(backend, frontend)
        try:
            health = _request_json(f"{plan.backend_url}/api/health")
            if (
                isinstance(health, dict)
                and health.get("status") == "ok"
                and health.get("service") == "uv-studio"
            ):
                backend_ready = True
                break
        except (DesktopLauncherError, OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    if not backend_ready:
        raise DesktopLauncherError("bundled backend did not become ready")

    while time.monotonic() < deadline:
        _raise_if_child_exited(backend, frontend)
        try:
            if _request_ok(plan.frontend_url):
                return
        except (OSError, TimeoutError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise DesktopLauncherError("bundled frontend did not become ready")


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    graceful_sent = False
    if os.name == "nt" and hasattr(signal, "CTRL_BREAK_EVENT"):
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            graceful_sent = True
        except (OSError, ValueError):
            graceful_sent = False
    if not graceful_sent:
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except OSError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _smoke_diagnostics(plan: DesktopLaunchPlan) -> None:
    try:
        diagnostics = _request_json(
            f"{plan.frontend_url}/api/uv/diagnostics?verify_release=true",
            timeout=120.0,
        )
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise DesktopLauncherError("desktop smoke diagnostics could not be read") from exc
    if not isinstance(diagnostics, dict):
        raise DesktopLauncherError("desktop smoke diagnostics returned an invalid payload")
    if diagnostics.get("mode") != "packaged" or diagnostics.get("overall_status") != "ok":
        raise DesktopLauncherError("desktop smoke diagnostics rejected the packaged application")
    runtime = diagnostics.get("runtime")
    release = diagnostics.get("release")
    if not isinstance(runtime, dict) or runtime.get("frozen") is not True:
        raise DesktopLauncherError("desktop smoke did not observe a frozen backend")
    if not isinstance(release, dict):
        raise DesktopLauncherError("desktop smoke did not observe release diagnostics")
    integrity = release.get("integrity")
    if (
        not isinstance(integrity, dict)
        or integrity.get("ok") is not True
        or integrity.get("verify_hashes") is not True
    ):
        raise DesktopLauncherError("desktop smoke deep release verification failed")


def run_desktop(
    *,
    release_root: Path | str | None = None,
    current_executable: Path | str | None = None,
    open_browser: bool = True,
    smoke: bool = False,
    base_environment: Mapping[str, str] | None = None,
) -> int:
    if release_root is None:
        inferred_root, inferred_executable = infer_packaged_release_root(current_executable)
        release_root = inferred_root
        current_executable = inferred_executable
    plan = build_launch_plan(release_root, current_executable=current_executable)
    environment = build_child_environment(plan, base_environment=base_environment)
    require_desktop_ports_available()

    backend: subprocess.Popen | None = None
    frontend: subprocess.Popen | None = None
    try:
        backend, frontend = _start_children(plan, environment)
        _wait_until_ready(plan, backend, frontend)
        if smoke:
            _smoke_diagnostics(plan)
            return 0
        if open_browser:
            try:
                webbrowser.open(plan.frontend_url, new=1)
            except Exception:
                pass
        while True:
            _raise_if_child_exited(backend, frontend)
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        if frontend is not None:
            _stop_process(frontend)
        if backend is not None:
            _stop_process(backend)


def _show_windows_error(message: str) -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "UV Studio", 0x10)
    except Exception:
        pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the packaged UV Studio desktop application.")
    parser.add_argument(
        "--desktop-smoke",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the desktop services without opening the default browser.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return run_desktop(
            open_browser=not args.no_browser and not args.desktop_smoke,
            smoke=args.desktop_smoke,
        )
    except DesktopLauncherError as exc:
        message = f"UV Studio could not start.\n\n{exc}"
        print(message, file=sys.stderr)
        if not args.desktop_smoke:
            _show_windows_error(message)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
