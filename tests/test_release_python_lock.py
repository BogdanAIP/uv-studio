from __future__ import annotations

import unittest
from pathlib import Path

from tools.verify_release_python_lock import (
    ROOT,
    load_profile,
    parse_constraints,
    validate_runtime,
)


class ReleasePythonLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile_path = ROOT / "packaging" / "runtime-profile.windows-x86_64.json"
        self.profile = load_profile(self.profile_path)
        python_profile = self.profile["python"]
        assert isinstance(python_profile, dict)
        self.lock_path = ROOT / str(python_profile["constraints"])
        self.expected = parse_constraints(self.lock_path)

    def test_profile_pins_proven_release_runtime_candidates(self) -> None:
        self.assertEqual(self.profile["target"], {"os": "windows", "arch": "x86_64"})
        self.assertEqual(self.profile["python"]["version"], "3.13.14")
        self.assertEqual(self.profile["node"]["version"], "24.19.0")
        self.assertEqual(self.profile["node"]["lock"], "frontend/package-lock.json")
        self.assertEqual(len(self.expected), 32)

    def test_every_direct_core_requirement_is_covered_by_exact_release_lock(self) -> None:
        direct: set[str] = set()
        for raw in (ROOT / "requirements-uv.txt").read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name = line.split("<", 1)[0].split(">", 1)[0].split("=", 1)[0].strip().lower()
            direct.add(name.replace("_", "-"))
        self.assertTrue(direct)
        self.assertTrue(direct.issubset(self.expected), direct.difference(self.expected))

    def test_exact_runtime_passes_with_only_bootstrap_tools_extra(self) -> None:
        installed = dict(self.expected)
        installed["pip"] = "99.0"
        problems = validate_runtime(
            expected_python="3.13.14",
            expected_packages=self.expected,
            installed_packages=installed,
            actual_python="3.13.14",
        )
        self.assertEqual(problems, [])

    def test_wrong_python_package_version_and_unmanaged_package_fail_closed(self) -> None:
        installed = dict(self.expected)
        installed["fastapi"] = "0.0.1"
        installed["surprise-runtime"] = "1.0"
        problems = validate_runtime(
            expected_python="3.13.14",
            expected_packages=self.expected,
            installed_packages=installed,
            actual_python="3.13.13",
        )
        self.assertTrue(any("Python version mismatch" in item for item in problems))
        self.assertTrue(any("package version mismatch for fastapi" in item for item in problems))
        self.assertTrue(any("unmanaged runtime packages" in item for item in problems))

    def test_release_lock_contains_no_markers_urls_or_ranges(self) -> None:
        for line in self.lock_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self.assertEqual(line.count("=="), 1, line)
            self.assertNotIn(";", line)
            self.assertNotIn(" @ ", line)
            self.assertNotIn(">", line)
            self.assertNotIn("<", line)


if __name__ == "__main__":
    unittest.main()
