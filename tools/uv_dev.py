#!/usr/bin/env python3
"""UV Studio development launcher.

This module is owned by UV Studio and provides stable repository-root commands.
The backend wraps the pinned VideoClaw runtime, while the user-facing frontend
is tracked UV Studio product source under top-level `frontend/`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_APP = ROOT / "vendor" / "videoclaw-app"
BACKEND = VENDOR_APP / "backend"
VENDOR_FRONTEND = VENDOR_APP / "frontend"
FRONTEND = ROOT / "frontend"
UPSTREAM_BACKEND_ENTRYPOINT = BACKEND / "api_server.py"
UV_SERVER_ENTRYPOINT = ROOT / "uv_studio" / "server.py"
FRONTEND_PACKAGE = FRONTEND / "package.json"
FRONTEND_PROVENANCE = FRONTEND / ".uv-derived.json"
DEFAULT_HEALTH_URL = "http://127.0.0.1:8000/api/health"


class DevError(RuntimeError):
    pass


def validate_layout() -> None:
    required = [
        UPSTREAM_BACKEND_ENTRYPOINT,
        UV_SERVER_ENTRYPOINT,
        FRONTEND_PACKAGE,
        FRONTEND_PROVENANCE,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        formatted = "\n".join(f"- {path.relative_to(ROOT)}" for path in missing)
        raise DevError(
            "UV Studio development layout is incomplete. Missing:\n"
            f"{formatted}\n"
            "If vendor files are missing, run: python tools/vendor_videoclaw.py\n"
            "If tracked frontend files are missing or damaged, restore frontend/ from the current Git checkout or use a fresh checkout. "
            "The pinned donor frontend is provenance/comparison material only."
        )


def npm_executable() -> str:
    executable = "npm.cmd" if os.name == "nt" else "npm"
    found = shutil.which(executable)
    if not found:
        raise DevError(f"{executable} was not found on PATH")
    return found


def backend_command() -> list[str]:
    validate_layout()
    return [sys.executable, "-m", "uv_studio.server"]


def frontend_command(mode: str = "dev") -> list[str]:
    validate_layout()
    if mode not in {"dev", "start", "build"}:
        raise DevError(f"Unsupported frontend mode: {mode}")
    return [npm_executable(), "run", mode]


def run_backend() -> int:
    command = backend_command()
    print(f"UV Studio backend: {' '.join(command)}")
    return subprocess.call(command, cwd=ROOT)


def run_frontend(mode: str) -> int:
    command = frontend_command(mode)
    print(f"UV Studio frontend ({mode}): {' '.join(command)}")
    return subprocess.call(command, cwd=FRONTEND)


def read_health(url: str, timeout: float = 2.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise DevError(f"Health endpoint returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "ok":
        raise DevError(f"Unexpected health payload: {payload!r}")
    return payload


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=8)


def health_smoke(
    *,
    url: str = DEFAULT_HEALTH_URL,
    startup_timeout: float = 30.0,
) -> dict:
    """Start the UV Studio server, probe real HTTP health, then stop it."""
    command = backend_command()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    deadline = time.monotonic() + startup_timeout
    last_error: Exception | None = None
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise DevError(
                    f"Backend exited before becoming healthy (code {process.returncode}).\n{output}"
                )
            try:
                payload = read_health(url)
                print(f"health ok: {payload}")
                return payload
            except (OSError, urllib.error.URLError, json.JSONDecodeError, DevError) as exc:
                last_error = exc
                time.sleep(0.4)
        output = ""
        if process.poll() is not None and process.stdout:
            output = process.stdout.read()
        raise DevError(
            f"Backend did not become healthy at {url} within {startup_timeout:.1f}s. "
            f"Last error: {last_error!r}\n{output}"
        )
    finally:
        terminate_process(process)


def print_paths() -> int:
    validate_layout()
    data = {
        "root": str(ROOT),
        "uv_server": str(UV_SERVER_ENTRYPOINT),
        "vendor_app": str(VENDOR_APP),
        "upstream_backend": str(BACKEND),
        "vendor_frontend_snapshot": str(VENDOR_FRONTEND),
        "frontend": str(FRONTEND),
    }
    print(json.dumps(data, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("paths", help="Print resolved UV Studio source paths.")
    sub.add_parser("backend", help="Run the UV Studio development backend.")

    frontend = sub.add_parser("frontend", help="Run a frontend npm script.")
    frontend.add_argument("--mode", choices=["dev", "start", "build"], default="dev")

    smoke = sub.add_parser("health-smoke", help="Start backend and probe /api/health over HTTP.")
    smoke.add_argument("--url", default=DEFAULT_HEALTH_URL)
    smoke.add_argument("--startup-timeout", type=float, default=30.0)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "paths":
        return print_paths()
    if args.command == "backend":
        return run_backend()
    if args.command == "frontend":
        return run_frontend(args.mode)
    if args.command == "health-smoke":
        health_smoke(url=args.url, startup_timeout=args.startup_timeout)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DevError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
