# Architecture Document Authority

Use this index before treating any architecture document as current guidance.

## Current authority

1. [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md) — primary architecture entry point.
2. [`UV_STUDIO_V2_ARCHITECTURE_MAP.md`](UV_STUDIO_V2_ARCHITECTURE_MAP.md) — practical component/migration map.
3. `project-context/decisions/D-064-production-directions-over-shared-studio-core.md` — Production Direction/product-composition authority.
4. `project-context/decisions/D-065-shared-production-semantic-core.md` — shared Scene/Shot/Take/production-semantics factoring beneath directions.
5. `project-context/decisions/D-066-jarvishub-agent-harness-donor.md` — Agent Harness donor/factoring authority; JarvisHub informs the agent/runtime patterns without replacing UV-owned project/production/timeline state.
6. `project-context/decisions/D-067-product-truth-contract-and-current-doc-consistency.md` — Product Truth, current-doc consistency, backend/frontend parity and user-outcome verification authority.
7. `project-context/decisions/D-068-desktop-in-place-updates.md` — desktop update/version migration authority.
8. `project-context/decisions/D-069-stateful-generative-continuation-lineage.md` — stateful/sequential generation continuation authority: durable parent media lineage with provider-private runtime state kept behind adapters.
9. `project-context/decisions/D-033-reuse-first-scriptable-editor-foundation.md` — editor/MLT ownership foundation.
10. `ARCHITECTURE_PRINCIPLES.md` — repository-wide engineering constraints.

## Current supporting technical documents

These remain valid when they do not conflict with current authority:

- [`CAPABILITIES.md`](CAPABILITIES.md) — Capability Registry below Studio tools/Model Registry;
- [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) — selection, authorization and bounded execution;
- [`PRODUCT_TRUTH_CONTRACT.md`](PRODUCT_TRUTH_CONTRACT.md) — machine-verifiable D-067 contract shape connecting current docs, backend/frontend surfaces and user-outcome evidence;
- [`product-truth/generate-shot-take.json`](product-truth/generate-shot-take.json) — first ready machine-readable Product Truth record, for Stage-14 named generation;
- [`STAGE14_PRODUCT_TRUTH_PLAN.md`](STAGE14_PRODUCT_TRUTH_PLAN.md) — Stage-14 as-built Product Truth evidence and bounded continuation non-claim;
- [`DESKTOP_UPDATES.md`](DESKTOP_UPDATES.md) — target Update Service/UI, in-place upgrade and N-1 -> N release proof;
- [`MCP_ADAPTER.md`](MCP_ADAPTER.md) — current optional MCP capability/execution boundary;
- [`DUBBING_TRANSLATION.md`](DUBBING_TRANSLATION.md) — reusable contextual dubbing-domain implementation;
- [`RANGE_REINSERTION.md`](RANGE_REINSERTION.md) — deterministic range-replacement primitive;
- `docs/PROJECT_STORE.md` — canonical storage, typed Studio identity and transaction/undo contract;
- `docs/PROJECT_ARCHIVES.md` — archive portability/integrity;
- `docs/FRONTEND.md` — current and compatibility frontend surfaces.

## Historical evidence / evaluations

- [`EDITOR_FOUNDATION_CONFORMANCE.md`](EDITOR_FOUNDATION_CONFORMANCE.md) — historical PR #44 D-033 conformance snapshot;
- [`QWEN_MM_PLUGINS_EVALUATION.md`](QWEN_MM_PLUGINS_EVALUATION.md) — pinned 2026-08-11 external-component evaluation;
- [`TEST_EVIDENCE_GAPS.md`](TEST_EVIDENCE_GAPS.md) — current evidence-class policy with historical recovery context.

## Compatibility / historical product documents

The following describe earlier recipe/Product-Orchestrator recovery eras. They are retained for migration evidence and archaeology, **not as instructions for new product composition**:

- `PRODUCT_ORCHESTRATOR.md`;
- `PRODUCT_RECOVERY_PLAN.md`;
- `PRODUCT_SURFACE_AUDIT.md`;
- `PRODUCT_TRUTH_MATRIX.md`;
- `FRONTEND_BACKEND_INTERACTION_MAP.md`;
- `RECIPES.md`;
- `RECIPE_EXECUTION.md`;
- `LEGACY_SURFACE_INVENTORY.md`.

If any supporting/historical document disagrees with `CURRENT_ARCHITECTURE.md`, D-064, D-065, D-066, D-067, D-068 or D-069, current authority wins.

## Decision status

- D-064 — current Production Direction/product-composition authority;
- D-065 — current shared production-semantics authority beneath directions;
- D-066 — current JarvisHub Agent Harness donor/factoring authority;
- D-067 — current Product Truth/current-documentation consistency authority;
- D-068 — current desktop in-place update/version migration authority;
- D-069 — current stateful generative continuation lineage/provider-state boundary authority;
- D-063 — partially superseded by D-064; shared application core remains useful;
- D-062 — historical Product Truth recovery rationale; forward verification is now D-067;
- D-042 — superseded at product-composition level; technical capability/media evidence remains historical reference.

Git history retains original detail of compacted historical documents.
