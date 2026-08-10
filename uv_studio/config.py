"""UV Studio-owned runtime settings.

Keep product settings separate from the vendored VideoClaw configuration so
project state and future recipes do not become coupled to upstream config files.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECTS_ROOT = ROOT / "data" / "projects"


def projects_root() -> Path:
    configured = os.environ.get("UV_STUDIO_PROJECTS_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_PROJECTS_ROOT.resolve()
