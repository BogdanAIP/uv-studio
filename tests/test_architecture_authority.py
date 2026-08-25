from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture"
DECISIONS = ROOT / "project-context" / "decisions"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_current_architecture_is_explicit_authority() -> None:
    current = _text(ARCH / "CURRENT_ARCHITECTURE.md")
    index = _text(ARCH / "README.md")
    agents = _text(ROOT / "AGENTS.md")

    assert "CURRENT AUTHORITY" in current
    assert "Production Direction" in current
    assert "D-064" in current
    assert "CURRENT_ARCHITECTURE.md" in index
    assert "CURRENT_ARCHITECTURE.md" in agents


def test_recipe_orchestrator_documents_are_not_current_authority() -> None:
    historical = [
        "PRODUCT_ORCHESTRATOR.md",
        "PRODUCT_RECOVERY_PLAN.md",
        "PRODUCT_SURFACE_AUDIT.md",
        "PRODUCT_TRUTH_MATRIX.md",
        "FRONTEND_BACKEND_INTERACTION_MAP.md",
        "RECIPES.md",
        "RECIPE_EXECUTION.md",
        "LEGACY_SURFACE_INVENTORY.md",
    ]

    for name in historical:
        prefix = _text(ARCH / name)[:500]
        assert "HISTORICAL" in prefix or "COMPATIBILITY" in prefix, name
        assert "CURRENT_ARCHITECTURE.md" in prefix, name


def test_superseded_product_decisions_are_labeled() -> None:
    d042 = _text(DECISIONS / "D-042-stage-8-composition-first-additional-recipes.md")
    d062 = _text(DECISIONS / "D-062-product-truth-recovery-gate.md")
    d063 = _text(DECISIONS / "D-063-studio-first-product-architecture.md")

    assert "Superseded at product-composition level" in d042[:500]
    assert "Product Orchestrator center superseded" in d062[:500]
    assert "Partially superseded by D-064" in d063[:500]


def test_decision_index_points_to_current_authority() -> None:
    decisions = _text(ROOT / "project-context" / "DECISIONS.md")
    assert "Current product / application authority" in decisions
    assert "D-064" in decisions
    assert "Partially superseded / historical product-composition decisions" in decisions
