from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")

# These paths feed the currently routed UV Studio product UI. Legacy donor
# components that are no longer routed are intentionally excluded: they should
# be retired with their compatibility surface rather than cosmetically maintained.
# The pinned vendor snapshot is also intentionally excluded because its exact
# bytes are provenance evidence and must not be translated in place.
PRODUCT_UI_ROOTS = (
    REPO_ROOT / "frontend" / "app",
    REPO_ROOT / "frontend" / "config",
    REPO_ROOT / "frontend" / "components" / "editor",
)
PRODUCT_SURFACE_FILES = (
    REPO_ROOT / "frontend" / "components" / "AppShell.tsx",
    REPO_ROOT / "uv_studio" / "server.py",
)


def _product_surface_files() -> list[Path]:
    files: list[Path] = []
    for root in PRODUCT_UI_ROOTS:
        files.extend(path for path in root.rglob("*") if path.suffix in {".ts", ".tsx"})
    files.extend(PRODUCT_SURFACE_FILES)
    return sorted(set(files))


def test_current_product_surface_has_no_chinese_text() -> None:
    offenders: list[str] = []
    for path in _product_surface_files():
        text = path.read_text(encoding="utf-8-sig")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if CJK_RE.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: {line.strip()}")

    assert not offenders, "Chinese text remains in current product surface:\n" + "\n".join(offenders)


def test_blank_project_surface_explains_supported_and_preparation_only_journeys() -> None:
    projects_page = (REPO_ROOT / "frontend" / "app" / "projects" / "page.tsx").read_text(encoding="utf-8")
    project_page = (
        REPO_ROOT / "frontend" / "app" / "projects" / "[projectId]" / "page.tsx"
    ).read_text(encoding="utf-8")
    composition = (
        REPO_ROOT / "frontend" / "components" / "editor" / "Stage8CompositionPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "Для первого знакомства рекомендуем «Обычный видеоролик»" in projects_page
    assert "Подготовительный режим" in projects_page
    assert "Создать и открыть" in projects_page
    assert "Сейчас это подготовка истории, а не генератор готового фильма" in project_page
    assert "SequenceContinuityPanel" not in project_page
    assert "Начать можно без файлов" in composition
    assert "Добавить своё изображение" in composition
    assert "Stage 8 ·" not in composition


def test_settings_are_capability_first_not_legacy_model_picker() -> None:
    settings = (REPO_ROOT / "frontend" / "app" / "settings" / "page.tsx").read_text(encoding="utf-8")

    assert "fetch('/api/uv/capabilities')" in settings
    assert "Как UV Studio выбирает инструменты" in settings
    assert "Локально и бесплатно" in settings
    assert "Облако — только явно" in settings
    assert "Экспериментальные подключения провайдеров · не активируют генерацию" in settings
    assert "Ключ сохранён · не активен" in settings
    assert "fetchModelGroupsByType" not in settings
    assert "fetchVideoModelGroupsByAbility" not in settings
    assert "Модели по умолчанию" not in settings
    assert "Подключить внешний ИИ-сервис · необязательно" not in settings
