#!/usr/bin/env python3
"""Verify the exact Windows Python runtime graph selected for UV Studio releases."""

from __future__ import annotations

import argparse
import importlib.metadata
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uv_studio.release_profile import ReleaseProfileError, load_release_profile

DEFAULT_PROFILE = ROOT / "packaging" / "runtime-profile.windows-x86_64.json"
_ALLOWED_BOOTSTRAP_PACKAGES = frozenset({"pip", "setuptools", "wheel"})
_NAME_NORMALIZER = re.compile(r"[-_.]+")


class ReleasePythonLockError(ValueError):
    pass


def canonical_name(value: str) -> str:
    return _NAME_NORMALIZER.sub("-", value).lower()


def load_profile(path: Path) -> dict[str, object]:
    try:
        return load_release_profile(path)
    except ReleaseProfileError as exc:
        raise ReleasePythonLockError(str(exc)) from exc


def parse_constraints(path: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ReleasePythonLockError("release constraints file is unreadable") from exc
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ";" in line or " @ " in line or line.count("==") != 1:
            raise ReleasePythonLockError(
                f"release constraints line {line_number} must be an exact name==version pin"
            )
        name, version = (part.strip() for part in line.split("==", 1))
        normalized = canonical_name(name)
        if not normalized or not version or any(character.isspace() for character in version):
            raise ReleasePythonLockError(f"release constraints line {line_number} is malformed")
        if normalized in expected:
            raise ReleasePythonLockError(f"duplicate release constraint for {normalized}")
        expected[normalized] = version
    if not expected:
        raise ReleasePythonLockError("release constraints file contains no packages")
    return expected


def installed_distributions() -> dict[str, str]:
    result: dict[str, str] = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if isinstance(name, str) and name.strip():
            result[canonical_name(name)] = distribution.version
    return result


def validate_runtime(
    *,
    expected_python: str,
    expected_packages: Mapping[str, str],
    installed_packages: Mapping[str, str],
    actual_python: str,
) -> list[str]:
    problems: list[str] = []
    if actual_python != expected_python:
        problems.append(f"Python version mismatch: expected {expected_python}, got {actual_python}")
    for name, expected_version in sorted(expected_packages.items()):
        actual = installed_packages.get(name)
        if actual is None:
            problems.append(f"missing locked package: {name}=={expected_version}")
        elif actual != expected_version:
            problems.append(
                f"package version mismatch for {name}: expected {expected_version}, got {actual}"
            )
    extra = sorted(
        set(installed_packages).difference(expected_packages).difference(_ALLOWED_BOOTSTRAP_PACKAGES)
    )
    if extra:
        problems.append("unmanaged runtime packages: " + ", ".join(extra))
    return problems


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        profile = load_profile(args.profile)
        python_profile = profile["python"]
        assert isinstance(python_profile, dict)
        constraints = ROOT / str(python_profile["constraints"])
        expected_packages = parse_constraints(constraints)
        problems = validate_runtime(
            expected_python=str(python_profile["version"]),
            expected_packages=expected_packages,
            installed_packages=installed_distributions(),
            actual_python=".".join(str(part) for part in sys.version_info[:3]),
        )
    except ReleasePythonLockError as exc:
        print(f"release Python lock validation failed: {exc}", file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2
    print(
        f"release Python lock validation passed: Python {python_profile['version']}, "
        f"{len(expected_packages)} packages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
