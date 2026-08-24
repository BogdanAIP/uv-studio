from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")

# These paths feed the currently routed UV Studio product UI. Legacy donor
# components that are no longer routed are intentionally excluded: they should
# be retired with their compatibility surface rather than cosmetically maintained.
PRODUCT_UI_ROOTS = (
    REPO_ROOT / "frontend" / "app",
    REPO_ROOT / "frontend" / "config",
    REPO_ROOT / "frontend" / "components" / "editor",
)
PRODUCT_UI_FILES = (
    REPO_ROOT / "frontend" / "components" / "AppShell.tsx",
)


def _product_ui_files() -> list[Path]:
    files: list[Path] = []
    for root in PRODUCT_UI_ROOTS:
        files.extend(path for path in root.rglob("*") if path.suffix in {".ts", ".tsx"})
    files.extend(PRODUCT_UI_FILES)
    return sorted(set(files))


def test_current_product_ui_has_no_chinese_text() -> None:
    offenders: list[str] = []
    for path in _product_ui_files():
        text = path.read_text(encoding="utf-8-sig")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if CJK_RE.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: {line.strip()}")

    assert not offenders, "Chinese text remains in current product UI:\n" + "\n".join(offenders)
