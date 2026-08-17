#!/usr/bin/env python3
"""Export the validated Windows release profile for build automation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uv_studio import __version__
from uv_studio.release_profile import load_release_profile

DEFAULT_PROFILE = ROOT / "packaging" / "runtime-profile.windows-x86_64.json"


def profile_environment(profile: Mapping[str, object]) -> dict[str, str]:
    python = profile["python"]
    node = profile["node"]
    media = profile["media"]
    build_tools = profile["build_tools"]
    assert isinstance(python, dict)
    assert isinstance(node, dict)
    assert isinstance(media, dict)
    assert isinstance(build_tools, dict)
    node_download = node["download"]
    media_download = media["download"]
    nsis = build_tools["nsis"]
    assert isinstance(node_download, dict)
    assert isinstance(media_download, dict)
    assert isinstance(nsis, dict)
    nsis_acquisition = nsis["acquisition"]
    assert isinstance(nsis_acquisition, dict)
    return {
        "UV_PRODUCT_VERSION": __version__,
        "UV_PYTHON_VERSION": str(python["version"]),
        "UV_PYTHON_CONSTRAINTS": str(python["constraints"]),
        "UV_NODE_VERSION": str(node["version"]),
        "UV_NODE_LOCK": str(node["lock"]),
        "UV_NODE_URL": str(node_download["url"]),
        "UV_NODE_SHA256": str(node_download["sha256"]),
        "UV_MEDIA_DISTRIBUTION": str(media["distribution"]),
        "UV_MEDIA_PACKAGE_VERSION": str(media["version"]),
        "UV_MEDIA_URL": str(media_download["url"]),
        "UV_MEDIA_SHA256": str(media_download["sha256"]),
        "UV_PYINSTALLER_VERSION": str(build_tools["pyinstaller"]),
        "UV_NSIS_VERSION": str(nsis["version"]),
        "UV_NSIS_PROVIDER": str(nsis_acquisition["provider"]),
        "UV_NSIS_PACKAGE": str(nsis_acquisition["package"]),
        "UV_NSIS_PACKAGE_VERSION": str(nsis_acquisition["package_version"]),
        "UV_NSIS_SOURCE": str(nsis_acquisition["source"]),
    }


def _write_environment(path: Path, values: Mapping[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key in sorted(values):
            handle.write(f"{key}={values[key]}\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--github-env", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    profile = load_release_profile(args.profile)
    values = profile_environment(profile)
    if args.github_env is not None:
        _write_environment(args.github_env, values)
    print(json.dumps(values, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
