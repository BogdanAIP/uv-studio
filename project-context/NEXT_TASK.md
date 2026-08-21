# Next Task

<!-- uv-next-slice: product-recovery-targeted-edit-orchestration -->

## Goal

Make the existing targeted existing-video edit journey understandable and product-driven by projecting its durable domain state through Product Orchestrator prerequisites and semantic next actions without weakening the accepted review/acceptance chain.

## Required direction

- preserve D-028/D-032/D-033 canonical edit, replacement and review state;
- keep `EditorCommandService`, Project Store, Capability Registry and D-017 as existing authorities;
- project user-facing steps such as source import, range selection, requested change, replacement preparation, preview/review, acceptance and export instead of exposing raw internal state-machine names as the primary UX;
- keep Brief → Plan → Candidate → Review → Accept durable underneath where it protects correctness and provenance;
- do not create a second workflow persistence engine;
- keep raw MLT/XML and direct canonical-state mutation unavailable to GUI/scripts/AI/MCP;
- reuse the current targeted-edit implementation and D-033 foundation rather than rebuilding a generic editor.

## Completion proof

The slice is complete when a targeted-edit project has truthful Orchestrator readiness/prerequisites/next actions derived from canonical edit state, the frontend follows those actions without bypassing domain review gates, and focused API/browser tests prove blocked, ready, review and accepted/exportable states.

## Entry gate

Do not begin until `product-recovery-workspace-routing` is reviewed and merged, its lifecycle is closed to `idle`, and Photo → Video plus Visualizer both use authoritative Product Orchestrator workspace routing with required tests green.
