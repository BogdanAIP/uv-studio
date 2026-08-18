"""Run browser E2E while preserving output and optionally target a packaged release.

Normal CI uses the source checkout services started by the test suite. Stage 9
release validation can set UV_E2E_PACKAGED_* variables; the runner then reuses the
same permanent browser scenarios while substituting the frozen backend and bundled
standalone frontend for the source service commands.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "e2e"
artifact_dir = Path(os.environ.get("UV_E2E_ARTIFACT_DIR", "e2e-artifacts")).resolve()
artifact_dir.mkdir(parents=True, exist_ok=True)


def _enable_packaged_service_substitution() -> None:
    backend = os.environ.get("UV_E2E_PACKAGED_BACKEND", "").strip()
    node = os.environ.get("UV_E2E_PACKAGED_NODE", "").strip()
    frontend_root = os.environ.get("UV_E2E_PACKAGED_FRONTEND_ROOT", "").strip()
    if not any((backend, node, frontend_root)):
        return
    if not all((backend, node, frontend_root)):
        raise RuntimeError(
            "packaged browser E2E requires UV_E2E_PACKAGED_BACKEND, "
            "UV_E2E_PACKAGED_NODE and UV_E2E_PACKAGED_FRONTEND_ROOT together"
        )

    backend_path = Path(backend).expanduser().resolve(strict=True)
    node_path = Path(node).expanduser().resolve(strict=True)
    frontend_path = Path(frontend_root).expanduser().resolve(strict=True)
    if not backend_path.is_file() or not node_path.is_file() or not frontend_path.is_dir():
        raise RuntimeError("packaged browser E2E service paths are invalid")

    if str(E2E) not in sys.path:
        sys.path.insert(0, str(E2E))
    import test_user_outcomes as harness

    source_start_process = harness._start_process

    def packaged_start_process(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        log_path: Path,
    ) -> Any:
        command_text = [str(part) for part in command]
        child_env = dict(env)
        if len(command_text) >= 3 and command_text[1:3] == ["-m", "uv_studio.server"]:
            return source_start_process(
                [str(backend_path), "--backend-child"],
                cwd=backend_path.parent,
                env=child_env,
                log_path=log_path,
            )
        if "run" in command_text and "start" in command_text:
            child_env["HOSTNAME"] = "127.0.0.1"
            child_env["PORT"] = "3000"
            return source_start_process(
                [str(node_path), "server.js"],
                cwd=frontend_path,
                env=child_env,
                log_path=log_path,
            )
        return source_start_process(command, cwd=cwd, env=child_env, log_path=log_path)

    harness._start_process = packaged_start_process


_enable_packaged_service_substitution()

completed = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "e2e", "-p", "test_*.py", "-v"],
    cwd=ROOT,
    env=os.environ.copy(),
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)

sys.stdout.write(completed.stdout)
(artifact_dir / "test-output.log").write_text(completed.stdout, encoding="utf-8", errors="replace")
raise SystemExit(completed.returncode)
