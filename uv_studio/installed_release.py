"""Deep verification boundary for a copied/installed packaged release."""

from __future__ import annotations

from pathlib import Path

from .desktop_launcher import DesktopLauncherError, build_launch_plan, infer_packaged_release_root
from .release_manifest import ReleaseManifestError, load_release_manifest, verify_release_tree


class InstalledReleaseVerificationError(RuntimeError):
    """A copied packaged release cannot be activated safely."""


def verify_installed_release(
    *,
    release_root: Path | str | None = None,
    current_executable: Path | str | None = None,
) -> dict[str, object]:
    if release_root is None:
        try:
            inferred_root, inferred_executable = infer_packaged_release_root(current_executable)
        except DesktopLauncherError as exc:
            raise InstalledReleaseVerificationError(str(exc)) from exc
        release_root = inferred_root
        current_executable = inferred_executable

    try:
        plan = build_launch_plan(release_root, current_executable=current_executable)
        manifest = load_release_manifest(plan.release_root)
        result = verify_release_tree(manifest, plan.release_root, verify_hashes=True)
    except (DesktopLauncherError, OSError, ReleaseManifestError) as exc:
        raise InstalledReleaseVerificationError("installed release verification could not be completed") from exc

    if not result.get("ok"):
        problems = result.get("problems", [])
        detail = "; ".join(str(item) for item in problems[:3]) if isinstance(problems, list) else ""
        raise InstalledReleaseVerificationError(
            "installed application payload failed deep integrity verification"
            + (f": {detail}" if detail else "")
        )
    return result
