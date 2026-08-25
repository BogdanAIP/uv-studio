"""One-shot Stage 12 migration for legacy test fixtures.

ProjectStore and the compatibility project API no longer infer ``general_video``.
This script makes historical test setup explicit without weakening the production
boundary. It is intentionally deterministic and should be removed after use.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOTS = (ROOT / "tests", ROOT / "tests_api")


def _char_offset(text: str, lineno: int, byte_col: int) -> int:
    lines = text.splitlines(keepends=True)
    before = sum(len(line) for line in lines[: lineno - 1])
    line = lines[lineno - 1]
    prefix = line.encode("utf-8")[:byte_col].decode("utf-8")
    return before + len(prefix)


def _call_open_paren(text: str, node: ast.Call) -> int:
    assert hasattr(node.func, "end_lineno") and hasattr(node.func, "end_col_offset")
    start = _char_offset(text, node.func.end_lineno, node.func.end_col_offset)
    end = _char_offset(text, node.end_lineno, node.end_col_offset)
    pos = text.find("(", start, end)
    if pos < 0:
        raise RuntimeError(f"could not locate call parenthesis at line {node.lineno}")
    return pos


def _dict_open_brace(text: str, node: ast.Dict) -> int:
    start = _char_offset(text, node.lineno, node.col_offset)
    end = _char_offset(text, node.end_lineno, node.end_col_offset)
    pos = text.find("{", start, end)
    if pos < 0:
        raise RuntimeError(f"could not locate dict brace at line {node.lineno}")
    return pos


def _constant_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _migrate_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return False

    insertions: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Direct ProjectStore-style fixture creation. Existing explicit identities
        # are preserved byte-for-byte.
        if isinstance(node.func, ast.Attribute) and node.func.attr == "create_project":
            if not any(keyword.arg == "recipe_id" for keyword in node.keywords):
                insertions.append(
                    (_call_open_paren(text, node) + 1, 'recipe_id="general_video", ')
                )

        # Compatibility HTTP project creation used by old API tests.
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "post"):
            continue
        url_node = node.args[0] if node.args else None
        if _constant_string(url_node) != "/api/uv/projects":
            continue
        json_keyword = next((kw for kw in node.keywords if kw.arg == "json"), None)
        if json_keyword is None or not isinstance(json_keyword.value, ast.Dict):
            continue
        keys = {_constant_string(key) for key in json_keyword.value.keys if key is not None}
        if "recipe_id" in keys:
            continue
        insertions.append(
            (_dict_open_brace(text, json_keyword.value) + 1, '"recipe_id": "general_video", ')
        )

    # Apply all AST-coordinate edits before any content-specific replacements so
    # source offsets remain valid.
    for offset, value in sorted(set(insertions), reverse=True):
        text = text[:offset] + value + text[offset:]

    # The strict-JSON regression deliberately sends NaN as raw content rather than
    # through httpx JSON encoding, so it is not represented by an ast.Dict.
    if path.name == "test_projects_api.py":
        old = "content='{\"title\":\"Bad JSON\",\"settings\""
        new = "content='{\"title\":\"Bad JSON\",\"recipe_id\":\"general_video\",\"settings\""
        if old in text:
            text = text.replace(old, new, 1)

    if path.name == "test_studio_timeline_api.py":
        text = text.replace(
            '"schema_version": 2,\n                "product_model": "production_directions",',
            '"schema_version": 1,\n                "product_model": "production_directions",',
        )

    if text == original:
        return False
    ast.parse(text, filename=str(path))
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    changed: list[str] = []
    for root in TEST_ROOTS:
        for path in sorted(root.glob("test_*.py")):
            if _migrate_file(path):
                changed.append(path.relative_to(ROOT).as_posix())
    print(f"updated {len(changed)} legacy test fixture files")
    for path in changed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
