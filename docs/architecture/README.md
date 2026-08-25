# Architecture Document Authority

Use this index before treating any architecture document as current guidance.

## Current authority

1. [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md) — primary architecture entry point.
2. [`UV_STUDIO_V2_ARCHITECTURE_MAP.md`](UV_STUDIO_V2_ARCHITECTURE_MAP.md) — practical component/migration map under D-064.
3. `project-context/decisions/D-064-production-directions-over-shared-studio-core.md` — current product-composition ADR.
4. `project-context/decisions/D-033-reuse-first-scriptable-editor-foundation.md` — editor/MLT ownership foundation.
5. `ARCHITECTURE_PRINCIPLES.md` — repository-wide engineering constraints.

## Current supporting technical documents

These describe lower-layer contracts that remain valid when they do not conflict with current authority:

- [`CAPABILITIES.md`](CAPABILITIES.md) — Capability Registry below Studio tools/Model Registry;
- [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) — selection, authorization and bounded execution;
- [`MCP_ADAPTER.md`](MCP_ADAPTER.md) — current optional MCP capability/execution boundary;
- [`DUBBING_TRANSLATION.md`](DUBBING_TRANSLATION.md) — reusable dubbing-domain implementation;
- [`RANGE_REINSERTION.md`](RANGE_REINSERTION.md) — deterministic range-replacement primitive;
- `docs/PROJECT_STORE.md` — canonical project storage and current transaction/identity debt;
- `docs/PROJECT_ARCHIVES.md` — archive portability/integrity;
- `docs/FRONTEND.md` — current and compatibility frontend surfaces.

## Historical evidence / evaluations

These may contain useful engineering evidence but do not define current product composition or current next work:

- [`EDITOR_FOUNDATION_CONFORMANCE.md`](EDITOR_FOUNDATION_CONFORMANCE.md) — historical PR #44 D-033 conformance snapshot;
- [`QWEN_MM_PLUGINS_EVALUATION.md`](QWEN_MM_PLUGINS_EVALUATION.md) — pinned 2026-08-11 external-component evaluation;
- [`TEST_EVIDENCE_GAPS.md`](TEST_EVIDENCE_GAPS.md) — evidence-class policy plus historical recovery context; current targets are expressed in Production Direction terms.

## Compatibility / historical product documents

The following describe earlier recipe/Product-Orchestrator recovery eras. They are retained for migration evidence and implementation archaeology, **not as instructions for new product composition**:

- `PRODUCT_ORCHESTRATOR.md`;
- `PRODUCT_RECOVERY_PLAN.md`;
- `PRODUCT_SURFACE_AUDIT.md`;
- `PRODUCT_TRUTH_MATRIX.md`;
- `FRONTEND_BACKEND_INTERACTION_MAP.md`;
- `RECIPES.md`;
- `RECIPE_EXECUTION.md`;
- `LEGACY_SURFACE_INVENTORY.md`.

If any supporting or historical document disagrees with `CURRENT_ARCHITECTURE.md` or D-064, current authority wins.

## Decision status

- D-064 — current product-composition authority;
- D-063 — partially superseded by D-064; shared Studio Core and command/model/job direction remain useful;
- D-062 — partially superseded; Product Truth invariants remain, Product Orchestrator as long-term center does not;
- D-042 — superseded at product-composition level; technical capability/media evidence remains historical reference.

Git history retains the original detail of compacted historical documents when deeper archaeology is required.
