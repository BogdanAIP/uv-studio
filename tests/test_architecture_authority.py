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


def test_architecture_index_names_only_real_supporting_documents() -> None:
    index = _text(ARCH / "README.md")
    supporting = [
        "CAPABILITIES.md",
        "CAPABILITY_EXECUTION.md",
        "MCP_ADAPTER.md",
        "DUBBING_TRANSLATION.md",
        "RANGE_REINSERTION.md",
        "EDITOR_FOUNDATION_CONFORMANCE.md",
        "QWEN_MM_PLUGINS_EVALUATION.md",
        "TEST_EVIDENCE_GAPS.md",
    ]
    for name in supporting:
        assert (ARCH / name).is_file(), name
        assert name in index, name

    # Old names accidentally introduced by the first authority-index draft must not return.
    for nonexistent in (
        "CAPABILITY_CONTRACT.md",
        "AUTHORIZED_EXECUTION.md",
        "EDITOR_ENGINE_INTEGRATION.md",
        "MODEL_ADAPTERS.md",
    ):
        assert nonexistent not in index


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


def test_supporting_documents_do_not_publish_obsolete_next_work() -> None:
    capabilities = _text(ARCH / "CAPABILITIES.md")
    capability_execution = _text(ARCH / "CAPABILITY_EXECUTION.md")
    mcp = _text(ARCH / "MCP_ADAPTER.md")
    dubbing = _text(ARCH / "DUBBING_TRANSLATION.md")
    frontend = _text(ROOT / "docs" / "FRONTEND.md")
    development = _text(ROOT / "docs" / "DEVELOPMENT.md")

    assert "CURRENT SUPPORTING TECHNICAL CONTRACT" in capabilities[:300]
    assert "Production Direction / Studio Tool" in capabilities
    assert "next Stage 5" not in capabilities

    assert "CURRENT SUPPORTING TECHNICAL CONTRACT" in capability_execution[:300]
    assert "Current next work is the application transaction/identity boundary" in capability_execution

    assert "CURRENT SUPPORTING TECHNICAL CONTRACT" in mcp[:300]
    assert "MCP execution is implemented" in mcp
    assert "discovery-only" not in mcp

    assert "CURRENT SUPPORTING DOMAIN CONTRACT" in dubbing[:300]
    assert "Post-merge hardening before Stage 6" not in dubbing

    assert "Production Direction" in frontend
    assert "/projects/[projectId]/studio" in frontend
    assert "next Stage 5" not in frontend

    assert "Production Direction" in development
    assert "next Stage 5" not in development


def test_historical_supporting_evidence_is_labeled() -> None:
    editor_audit = _text(ARCH / "EDITOR_FOUNDATION_CONFORMANCE.md")
    qwen = _text(ARCH / "QWEN_MM_PLUGINS_EVALUATION.md")
    assert "HISTORICAL CONFORMANCE SNAPSHOT" in editor_audit[:300]
    assert "HISTORICAL COMPONENT EVALUATION" in qwen[:300]


def test_next_slice_records_modern_studio_boundary_gates() -> None:
    next_task = _text(ROOT / "project-context" / "NEXT_TASK.md")
    project_store = _text(ROOT / "docs" / "PROJECT_STORE.md")

    assert "after PR #64" in next_task
    assert "Protect Production Direction identity" in next_task
    assert "Decouple modern Studio API from recipe/orchestrator imports" in next_task
    assert "Remove legacy creation defaults from the core foundation" in next_task
    assert "ProjectUnitOfWork" in next_task

    assert "Current debt" in project_store
    assert "direction_id" in project_store
    assert "general_video" in project_store
    assert "ProjectUnitOfWork" in project_store


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
