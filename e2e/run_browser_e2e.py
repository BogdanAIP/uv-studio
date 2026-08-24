"""Run the browser E2E suite while preserving its full unittest output as CI evidence."""

from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path


artifact_dir = Path(os.environ.get("UV_E2E_ARTIFACT_DIR", "e2e-artifacts")).resolve()
artifact_dir.mkdir(parents=True, exist_ok=True)

# This historical test deliberately depended on the retired generic workspace
# fallback: it created `action_transfer` and expected unrelated Dubbing and
# Sequence Continuity panels to appear. Product Truth reconciliation replaces
# it with two stronger product-owned outcomes in
# test_product_owned_editor_outcomes.py. Filter only this exact stale test ID;
# every other discovered browser regression still runs normally.
REPLACED_TEST_IDS = {
    "test_user_outcomes.BrowserUserOutcomes.test_targeted_edit_isolated_while_dubbing_and_sequence_regressions_remain_operable",
}


def _flatten(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


loader = unittest.TestLoader()
discovered = loader.discover("e2e", pattern="test_*.py")
filtered = unittest.TestSuite(
    test for test in _flatten(discovered) if test.id() not in REPLACED_TEST_IDS
)

buffer = io.StringIO()
result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(filtered)
output = buffer.getvalue()

# GitHub-hosted Windows runners can expose a legacy console encoding (for
# example cp1252). Browser test names and failure diagnostics contain Russian
# product copy, so force the evidence stream to UTF-8 before emitting it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stdout.write(output)
(artifact_dir / "test-output.log").write_text(output, encoding="utf-8", errors="replace")
raise SystemExit(0 if result.wasSuccessful() else 1)
