"""Run one exact unittest detector against one isolated UV Studio source overlay.

This helper is intentionally stdlib-only. The parent assurance runner supplies a
copied ``uv_studio`` package through ``PYTHONPATH``, the exact expected source
path inside that overlay, and an expected SHA-256 for the target source bytes. A
detector result is accepted only after proving all three refer to the module that
Python actually imported.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import traceback
import unittest
from pathlib import Path
from typing import Sequence

_RESULT_PREFIX = "UV_AGENT_ASSURANCE_RESULT="


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _emit(payload: dict[str, object]) -> None:
    print(_RESULT_PREFIX + json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--module", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--expected-source-relative", required=True, type=Path)
    parser.add_argument("--expected-source-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    overlay = args.overlay.resolve()
    try:
        relative_source = args.expected_source_relative
        if relative_source.is_absolute() or ".." in relative_source.parts:
            raise RuntimeError("expected source path must stay inside the isolated overlay")
        expected_source = (overlay / relative_source).resolve()
        if not _is_within(expected_source, overlay):
            raise RuntimeError("expected source path escaped the isolated overlay")

        importlib.invalidate_caches()
        target_module = importlib.import_module(args.module)
        origin = getattr(target_module, "__file__", None)
        if not origin:
            raise RuntimeError(f"target module {args.module!r} has no source origin")
        source_path = Path(origin).resolve()
        if not _is_within(source_path, overlay):
            raise RuntimeError(
                "source-binding failure: target module was not imported from the isolated overlay "
                f"(module={args.module!r}, source={str(source_path)!r}, overlay={str(overlay)!r})"
            )
        if source_path != expected_source:
            raise RuntimeError(
                "source-binding failure: imported module path does not equal the exact mutated target "
                f"(expected={str(expected_source)!r}, actual={str(source_path)!r})"
            )
        actual_sha256 = _sha256(source_path)
        if actual_sha256 != args.expected_source_sha256:
            raise RuntimeError(
                "source-binding failure: imported target source bytes do not match the expected overlay bytes "
                f"(expected={args.expected_source_sha256}, actual={actual_sha256})"
            )

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(args.test)
        if loader.errors:
            raise RuntimeError("detector loading failed: " + " | ".join(loader.errors))
        if suite.countTestCases() != 1:
            raise RuntimeError(
                f"detector must resolve to exactly one unittest case, got {suite.countTestCases()}"
            )

        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        payload: dict[str, object] = {
            "module": args.module,
            "test": args.test,
            "source": str(source_path),
            "source_sha256": actual_sha256,
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "output": stream.getvalue(),
        }
        if result.errors:
            payload["status"] = "test_error"
        elif result.failures:
            payload["status"] = "failure"
        elif result.wasSuccessful():
            payload["status"] = "pass"
        else:
            payload["status"] = "error"
            payload["error"] = "unittest returned an unclassified result"
        _emit(payload)
        return 0
    except Exception as exc:
        _emit(
            {
                "status": "error",
                "module": args.module,
                "test": args.test,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": "".join(traceback.format_exception(exc)),
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
