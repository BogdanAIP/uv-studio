# Architecture Document Authority

Use this index before treating any architecture document as current guidance.

## Current authority

1. [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md) — primary architecture entry point.
2. [`UV_STUDIO_V2_ARCHITECTURE_MAP.md`](UV_STUDIO_V2_ARCHITECTURE_MAP.md) — repository/component migration map under D-064.
3. `project-context/decisions/D-064-production-directions-over-shared-studio-core.md` — current product-composition ADR.
4. `project-context/decisions/D-033-reuse-first-scriptable-editor-foundation.md` — editor/MLT ownership foundation.
5. `ARCHITECTURE_PRINCIPLES.md` — repository-wide engineering principles.

## Foundational/supporting documents

These remain usable when they do not conflict with current authority:

- `CAPABILITY_CONTRACT.md`;
- `AUTHORIZED_EXECUTION.md`;
- `EDITOR_ENGINE_INTEGRATION.md`;
- `MODEL_ADAPTERS.md`;
- `RUNTIME_DEPENDENCIES.md`;
- `TARGETED_EDIT_STATE.md`;
- packaging/dependency inventories and evidence documents.

## Compatibility / historical documents

The following files describe earlier product eras or recovery strategies. They are retained for migration evidence and implementation archaeology, **not as instructions for new product composition**:

- `PRODUCT_ORCHESTRATOR.md`;
- `PRODUCT_RECOVERY_PLAN.md`;
- `PRODUCT_SURFACE_AUDIT.md`;
- `PRODUCT_TRUTH_MATRIX.md`;
- `FRONTEND_BACKEND_INTERACTION_MAP.md`;
- `RECIPES.md`;
- `RECIPE_EXECUTION.md`;
- `LEGACY_SURFACE_INVENTORY.md`.

If one of these disagrees with `CURRENT_ARCHITECTURE.md` or D-064, the current authority wins.

## Decision status

Decision records are historical by nature. Their status matters:

- D-064 — current product-composition authority;
- D-063 — partially superseded by D-064; shared Studio Core and command/model/job direction remain useful;
- D-062 — partially superseded; Product Truth invariants remain, Product Orchestrator as long-term center does not;
- D-042 — superseded at product-composition level; technical capability/media evidence remains historical reference.

Git history retains the original text of compacted historical documents when deeper archaeology is required.
