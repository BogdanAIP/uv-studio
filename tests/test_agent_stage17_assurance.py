from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "project-context" / "agent-assurance-stage17.json"
RESULT_PREFIX = "UV_AGENT_ASSURANCE_RESULT="
EXPECTED_MUTANTS = {
    "UV-ROLE-001",
    "UV-CTX-001",
    "UV-CTX-002",
    "UV-NS-001",
    "UV-PROV-001",
    "UV-AUTH-001",
}


class AgentStage17AssuranceTests(unittest.TestCase):
    def test_manifest_is_exact_bounded_stage17_pilot(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["suite_id"], "stage17-curated-v1")
        mutants = manifest["mutants"]
        self.assertEqual({item["id"] for item in mutants}, EXPECTED_MUTANTS)
        self.assertEqual(len(mutants), len(EXPECTED_MUTANTS))
        self.assertEqual(len({item["detector"] for item in mutants}), len(mutants))
        self.assertTrue(
            all(Path(item["target"]).parts[0] == "uv_studio" for item in mutants)
        )

    def test_curated_stage17_mutants_are_killed_and_exact_source_bound(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        source_before = {
            target: (ROOT / target).read_bytes()
            for target in {item["target"] for item in manifest["mutants"]}
        }
        with tempfile.TemporaryDirectory(prefix="uv-assurance-report-") as temp_dir:
            report_path = Path(temp_dir) / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "tools/agent_assurance.py",
                    "--manifest",
                    str(MANIFEST),
                    "--report",
                    str(report_path),
                    "--timeout-seconds",
                    "60",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=240,
                check=False,
            )
            detail = f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            self.assertEqual(completed.returncode, 0, detail)
            report = json.loads(report_path.read_text(encoding="utf-8"))

        for target, expected_bytes in source_before.items():
            with self.subTest(checkout_target=target):
                self.assertEqual((ROOT / target).read_bytes(), expected_bytes)
        self.assertEqual(report["summary"], {"KILLED": 6, "SURVIVED": 0, "ERROR": 0})
        self.assertEqual(set(report["selected_mutants"]), EXPECTED_MUTANTS)
        for result in report["results"]:
            with self.subTest(mutant=result["id"]):
                self.assertEqual(result["status"], "KILLED")
                self.assertNotEqual(
                    result["baseline_source_sha256"],
                    result["mutant_source_sha256"],
                )
                self.assertIn(f"uv-assurance-{result['id']}-", result["baseline_source"])
                self.assertIn(f"uv-assurance-{result['id']}-", result["mutant_source"])
                self.assertTrue(
                    Path(result["baseline_source"]).as_posix().endswith(result["target"])
                )
                self.assertTrue(
                    Path(result["mutant_source"]).as_posix().endswith(result["target"])
                )
                self.assertEqual(result["detector_failures"], 1)
                self.assertEqual(result["detector_errors"], 0)
                self.assertEqual(result["detector_skipped"], 0)

    def test_detector_fails_closed_on_wrong_executed_source_hash(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        mutant = manifest["mutants"][0]
        with tempfile.TemporaryDirectory(prefix="uv-assurance-binding-") as temp_dir:
            overlay = Path(temp_dir).resolve()
            shutil.copytree(
                ROOT / "uv_studio",
                overlay / "uv_studio",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                [str(overlay), str(ROOT / "tests"), str(ROOT)]
            )
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "tools/agent_assurance_detector.py",
                    "--overlay",
                    str(overlay),
                    "--module",
                    mutant["module"],
                    "--test",
                    mutant["detector"],
                    "--expected-source-relative",
                    mutant["target"],
                    "--expected-source-sha256",
                    "0" * 64,
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        payload_line = next(
            line
            for line in completed.stdout.splitlines()
            if line.startswith(RESULT_PREFIX)
        )
        payload = json.loads(payload_line[len(RESULT_PREFIX) :])
        self.assertEqual(payload["status"], "error")
        self.assertIn("source-binding failure", payload["error"])

    def test_report_path_inside_checkout_fails_closed_without_write(self) -> None:
        report_path = ROOT / ".uv-agent-assurance-forbidden-report.json"
        self.assertFalse(report_path.exists())
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "tools/agent_assurance.py",
                "--manifest",
                str(MANIFEST),
                "--mutant",
                "UV-PROV-001",
                "--report",
                str(report_path),
                "--timeout-seconds",
                "60",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        self.assertIn("--report must point outside the repository root", completed.stderr)
        self.assertFalse(report_path.exists())


if __name__ == "__main__":
    unittest.main()
