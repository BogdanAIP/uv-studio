"""Run the browser E2E suite while preserving its full unittest output as CI evidence."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


artifact_dir = Path(os.environ.get("UV_E2E_ARTIFACT_DIR", "e2e-artifacts")).resolve()
artifact_dir.mkdir(parents=True, exist_ok=True)

completed = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "e2e", "-p", "test_*.py", "-v"],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)

sys.stdout.write(completed.stdout)
(artifact_dir / "test-output.log").write_text(completed.stdout, encoding="utf-8", errors="replace")
raise SystemExit(completed.returncode)
