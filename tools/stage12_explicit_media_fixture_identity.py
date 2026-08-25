"""One-shot Stage 12 migration for real/browser media fixtures only."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOTS = (ROOT / "tests_real_media", ROOT / "tests_browser")


def _char_offset(text: str, lineno: int, byte_col: int) -> int:
    lines = text.splitlines(keepends=True)
    before = sum(len(line) for line in lines[: lineno - 1])
    line = lines[lineno - 1]
    prefix = line.encode("utf-8")[:byte_col].decode("utf-8")
    return before + len(prefix)


def _call_open_paren(text: str, node: ast.Call) -> int:
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


def _insert_value(text: str, offset: int, compact: str) -> str:
    return compact if text[offset:offset + 1] in {"\n", "\r"} else compact + " "


def migrate(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    tree = ast.parse(original, filename=str(path))
    edits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "create_project":
            if not any(keyword.arg == "recipe_id" for keyword in node.keywords):
                offset = _call_open_paren(original, node) + 1
                edits.append((offset, _insert_value(original, offset, 'recipe_id="general_video",')))
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
        offset = _dict_open_brace(original, json_keyword.value) + 1
        edits.append((offset, _insert_value(original, offset, '"recipe_id": "general_video",')))

    text = original
    for offset, value in sorted(set(edits), reverse=True):
        text = text[:offset] + value + text[offset:]
    if text == original:
        return False
    ast.parse(text, filename=str(path))
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    changed: list[str] = []
    for root in TEST_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("test_*.py")):
            if migrate(path):
                changed.append(path.relative_to(ROOT).as_posix())
    print(f"updated {len(changed)} media fixture files")
    for item in changed:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
