"""Test-only legacy Project seeding for browser compatibility outcomes.

The public recipe-backed project-creation route is intentionally retired. Browser
E2E scenarios that exercise old/imported compatibility workspaces still need exact
legacy recipe identity, so they seed canonical Project Store state directly in the
same temporary projects root used by the backend process. This helper is fixture
setup only; user-visible interactions continue through the real frontend and APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uv_studio.projects.store import ProjectStore


def seed_legacy_project(projects_root: Path, *, title: str, recipe_id: str) -> str:
    project = ProjectStore(projects_root).create_project(title=title, recipe_id=recipe_id)
    return project.project_id
