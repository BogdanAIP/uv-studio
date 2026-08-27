"""Curated mutation assurance for accepted UV Studio Agent guarantees.

The runner never edits checkout source. Each mutant receives a temporary full copy
of the ``uv_studio`` package, proves its exact detector passes on the unmodified
overlay, applies one exact source replacement, and then reruns the same detector
in a fresh Python process. The detector helper proves that the target module came
from the exact declared overlay path and that its source SHA-256 matches the exact
bytes the runner expects to execute. Optional machine-readable reports are allowed
only outside the repository root.

Classification is deliberately fail-closed:

* KILLED: baseline detector passed and the mutant caused an assertion failure;
* SURVIVED: baseline detector passed and the mutant still passed;
* ERROR: manifest, patch, import, source-binding, timeout, or unittest-error state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

_RESULT_PREFIX = "UV_AGENT_ASSURANCE_RESULT="
_DEFAULT_MANIFEST = Path("project-context/agent-assurance-stage17.json")
_ALLOWED_MUTANT_KEYS = {"id", "guarantee", "target", "module", "detector", "mutation"}
_ALLOWED_MUTATION_KEYS = {"find", "replace"}


class AssuranceError(RuntimeError):
    """Raised when the assurance harness cannot prove a meaningful mutant result."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssuranceError(f"{location} must be a non-empty string")
    return value


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssuranceError(f"cannot read assurance manifest {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AssuranceError("assurance manifest root must be an object")
    if set(raw) != {"schema_version", "suite_id", "description", "mutants"}:
        raise AssuranceError("assurance manifest root keys do not match schema v1")
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise AssuranceError("assurance manifest schema_version must be integer 1")
    _require_string(raw["suite_id"], "suite_id")
    _require_string(raw["description"], "description")
    mutants = raw["mutants"]
    if not isinstance(mutants, list) or not mutants:
        raise AssuranceError("mutants must be a non-empty list")

    seen: set[str] = set()
    for index, mutant in enumerate(mutants):
        location = f"mutants[{index}]"
        if not isinstance(mutant, dict) or set(mutant) != _ALLOWED_MUTANT_KEYS:
            raise AssuranceError(f"{location} keys do not match schema v1")
        mutant_id = _require_string(mutant["id"], f"{location}.id")
        if mutant_id in seen:
            raise AssuranceError(f"duplicate mutant id: {mutant_id}")
        seen.add(mutant_id)
        _require_string(mutant["guarantee"], f"{location}.guarantee")
        target = Path(_require_string(mutant["target"], f"{location}.target"))
        if (
            target.is_absolute()
            or ".." in target.parts
            or not target.parts
            or target.parts[0] != "uv_studio"
        ):
            raise AssuranceError(f"{location}.target must stay inside uv_studio")
        module = _require_string(mutant["module"], f"{location}.module")
        if not module.startswith("uv_studio."):
            raise AssuranceError(f"{location}.module must stay inside uv_studio")
        detector = _require_string(mutant["detector"], f"{location}.detector")
        if not detector.startswith("test_"):
            raise AssuranceError(f"{location}.detector must name one repository unittest")
        mutation = mutant["mutation"]
        if not isinstance(mutation, dict) or set(mutation) != _ALLOWED_MUTATION_KEYS:
            raise AssuranceError(f"{location}.mutation keys do not match schema v1")
        find = _require_string(mutation["find"], f"{location}.mutation.find")
        replace = mutation["replace"]
        if not isinstance(replace, str):
            raise AssuranceError(f"{location}.mutation.replace must be a string")
        if find == replace:
            raise AssuranceError(f"{location}.mutation must change source bytes")
    return raw


def _parse_detector_output(stdout: str) -> dict[str, Any]:
    payload_line = next(
        (line for line in reversed(stdout.splitlines()) if line.startswith(_RESULT_PREFIX)),
        None,
    )
    if payload_line is None:
        raise AssuranceError("detector did not emit a structured assurance result")
    try:
        payload = json.loads(payload_line[len(_RESULT_PREFIX) :])
    except json.JSONDecodeError as exc:
        raise AssuranceError("detector emitted invalid assurance JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("status"), str):
        raise AssuranceError("detector assurance result is missing status")
    return payload


def _run_detector(
    *,
    root: Path,
    overlay: Path,
    mutant: Mapping[str, Any],
    expected_source_sha256: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    env = os.environ.copy()
    pythonpath = [str(overlay), str(root / "tests"), str(root)]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        "-B",
        str(root / "tools" / "agent_assurance_detector.py"),
        "--overlay",
        str(overlay),
        "--module",
        str(mutant["module"]),
        "--test",
        str(mutant["detector"]),
        "--expected-source-relative",
        str(mutant["target"]),
        "--expected-source-sha256",
        expected_source_sha256,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssuranceError(
            f"detector timed out after {timeout_seconds:g}s: {mutant['detector']}"
        ) from exc
    try:
        payload = _parse_detector_output(completed.stdout)
    except AssuranceError as exc:
        detail = (completed.stderr or completed.stdout).strip()
        raise AssuranceError(f"{exc}; detector output: {detail[-2000:]}") from exc
    payload["returncode"] = completed.returncode
    payload["stderr"] = completed.stderr
    return payload


def _copy_package(root: Path, overlay: Path) -> None:
    source = root / "uv_studio"
    destination = overlay / "uv_studio"
    if not source.is_dir():
        raise AssuranceError(f"UV package does not exist: {source}")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def _error_result(mutant: Mapping[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "id": mutant.get("id", "unknown"),
        "guarantee": mutant.get("guarantee", "unknown"),
        "detector": mutant.get("detector", "unknown"),
        "target": mutant.get("target", "unknown"),
        "status": "ERROR",
        "error_type": type(exc).__name__,
        "error": str(exc),
    }


def run_mutant(
    root: Path,
    mutant: Mapping[str, Any],
    *,
    timeout_seconds: float = 45.0,
) -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory(prefix=f"uv-assurance-{mutant['id']}-") as temp_dir:
            overlay = Path(temp_dir).resolve()
            _copy_package(root, overlay)
            relative_target = Path(str(mutant["target"]))
            checkout_target = root / relative_target
            overlay_target = overlay / relative_target
            if (
                not checkout_target.is_file()
                or checkout_target.is_symlink()
                or not overlay_target.is_file()
                or overlay_target.is_symlink()
            ):
                raise AssuranceError(
                    f"mutant target must be a regular non-symlink source file: {relative_target}"
                )
            if not _is_within(checkout_target, root / "uv_studio"):
                raise AssuranceError("mutant target resolved outside the checkout uv_studio package")
            if not _is_within(overlay_target, overlay / "uv_studio"):
                raise AssuranceError("mutant target resolved outside the isolated uv_studio package")

            checkout_sha256 = _sha256(checkout_target)
            baseline_sha256 = _sha256(overlay_target)
            if baseline_sha256 != checkout_sha256:
                raise AssuranceError("isolated baseline copy does not match checkout source bytes")

            baseline = _run_detector(
                root=root,
                overlay=overlay,
                mutant=mutant,
                expected_source_sha256=baseline_sha256,
                timeout_seconds=timeout_seconds,
            )
            if (
                baseline.get("status") != "pass"
                or baseline.get("tests_run") != 1
                or baseline.get("skipped") != 0
            ):
                raise AssuranceError(
                    "baseline detector must run and pass exactly once before mutation "
                    f"(status={baseline.get('status')!r}, tests_run={baseline.get('tests_run')!r}, "
                    f"skipped={baseline.get('skipped')!r})"
                )

            source = overlay_target.read_text(encoding="utf-8")
            mutation = mutant["mutation"]
            find = str(mutation["find"])
            replace = str(mutation["replace"])
            occurrence_count = source.count(find)
            if occurrence_count != 1:
                raise AssuranceError(
                    f"mutation anchor must occur exactly once, found {occurrence_count} occurrences"
                )
            mutated = source.replace(find, replace, 1)
            if mutated == source:
                raise AssuranceError("mutation did not change target source")
            overlay_target.write_text(mutated, encoding="utf-8")
            mutant_sha256 = _sha256(overlay_target)
            if mutant_sha256 == baseline_sha256:
                raise AssuranceError("mutated source SHA-256 did not change")

            detector = _run_detector(
                root=root,
                overlay=overlay,
                mutant=mutant,
                expected_source_sha256=mutant_sha256,
                timeout_seconds=timeout_seconds,
            )
            detector_status = detector.get("status")
            detector_skipped = detector.get("skipped")
            if (
                detector_status == "failure"
                and detector.get("failures", 0) >= 1
                and detector.get("errors", 0) == 0
                and detector_skipped == 0
            ):
                status = "KILLED"
            elif detector_status == "pass" and detector_skipped == 0:
                status = "SURVIVED"
            else:
                raise AssuranceError(
                    "mutant detector did not produce a clean non-skipped assertion failure or pass "
                    f"(status={detector_status!r}, failures={detector.get('failures')!r}, "
                    f"errors={detector.get('errors')!r}, skipped={detector_skipped!r})"
                )

            return {
                "id": mutant["id"],
                "guarantee": mutant["guarantee"],
                "detector": mutant["detector"],
                "target": mutant["target"],
                "module": mutant["module"],
                "status": status,
                "baseline_source_sha256": baseline_sha256,
                "mutant_source_sha256": mutant_sha256,
                "baseline_source": baseline.get("source"),
                "mutant_source": detector.get("source"),
                "detector_failures": detector.get("failures"),
                "detector_errors": detector.get("errors"),
                "detector_skipped": detector_skipped,
                "detector_output": detector.get("output", ""),
            }
    except Exception as exc:
        return _error_result(mutant, exc)


def run_suite(
    root: Path,
    manifest: Mapping[str, Any],
    *,
    selected_ids: Sequence[str] | None = None,
    timeout_seconds: float = 45.0,
) -> dict[str, Any]:
    mutants = list(manifest["mutants"])
    if selected_ids:
        requested = list(dict.fromkeys(selected_ids))
        by_id = {str(item["id"]): item for item in mutants}
        missing = [item for item in requested if item not in by_id]
        if missing:
            raise AssuranceError(f"unknown mutant id(s): {', '.join(missing)}")
        mutants = [by_id[item] for item in requested]

    results = [
        run_mutant(root, mutant, timeout_seconds=timeout_seconds)
        for mutant in mutants
    ]
    counts = {
        status: sum(item["status"] == status for item in results)
        for status in ("KILLED", "SURVIVED", "ERROR")
    }
    return {
        "schema_version": 1,
        "suite_id": manifest["suite_id"],
        "selected_mutants": [item["id"] for item in mutants],
        "summary": counts,
        "results": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--mutant", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--list", action="store_true", dest="list_mutants")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    try:
        manifest = _load_manifest(manifest_path.resolve())
        if args.list_mutants:
            for mutant in manifest["mutants"]:
                print(f"{mutant['id']}: {mutant['guarantee']}")
            return 0
        if args.timeout_seconds <= 0:
            raise AssuranceError("--timeout-seconds must be positive")
        report = run_suite(
            root,
            manifest,
            selected_ids=args.mutant or None,
            timeout_seconds=args.timeout_seconds,
        )
        report_path: Path | None = None
        if args.report is not None:
            report_path = args.report
            if not report_path.is_absolute():
                report_path = (root / report_path).resolve()
            else:
                report_path = report_path.resolve()
            if _is_within(report_path, root):
                raise AssuranceError(
                    "--report must point outside the repository root; assurance never writes checkout files"
                )
    except AssuranceError as exc:
        print(f"agent assurance failed: {exc}", file=sys.stderr)
        return 2

    for result in report["results"]:
        print(f"{result['id']}: {result['status']} - {result['guarantee']}")
        if result["status"] == "ERROR":
            print(f"  {result.get('error_type')}: {result.get('error')}")
    summary = report["summary"]
    print(
        "agent assurance summary: "
        f"KILLED={summary['KILLED']} SURVIVED={summary['SURVIVED']} ERROR={summary['ERROR']}"
    )

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return 0 if summary["SURVIVED"] == 0 and summary["ERROR"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
