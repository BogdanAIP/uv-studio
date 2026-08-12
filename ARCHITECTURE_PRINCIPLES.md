# UV Studio Architecture Principles

These rules are product architecture constraints, not implementation suggestions.

## Reuse-first / orchestration-first

UV Studio MUST prefer a mature, professionally usable, maintained and license-compatible open-source component over a custom implementation of a general media/editor primitive.

Before implementing a new timeline, waveform, media player, compositor, render engine, subtitle engine, tracking/masking primitive, audio-processing primitive, interchange format or similar infrastructure, the active slice MUST:

1. identify credible existing open-source candidates;
2. verify license compatibility and redistribution obligations;
3. test the capabilities that matter to the product instead of relying on README claims;
4. record why the selected component is integrated, or why every credible candidate is rejected.

Custom implementation is justified only for UV-specific orchestration, a missing adapter/integration, a small compatibility layer, or a capability for which the repository records a concrete technical rejection of existing solutions.

A convenient custom implementation is not sufficient justification when a suitable reusable component exists.

## One command model: GUI = scripts = AI = MCP

Every meaningful non-trivial editor mutation MUST have one product-owned programmatic command contract.

The GUI, user scripts, AI actions and MCP automation MUST call the same command model. They MUST NOT maintain four independent editing implementations or mutate canonical project/timeline JSON directly.

The command layer owns:

- validation and project/path boundaries;
- deterministic mutation semantics;
- transaction grouping and undo/redo integration;
- provenance needed for automation/review;
- conversion to the selected editor/render-engine adapter;
- canonical UV Studio domain invariants.

An AI assistant may inspect project state and propose commands or higher-level plans, but it does not receive a privileged raw-state mutation bypass.

## Hybrid foundations are allowed

UV Studio does not require one upstream editor to own the entire product. A license-compatible editor UI donor, a separate media/timeline engine, UV Studio Project Store and UV Studio Command API may be composed when this reduces custom code and preserves clean ownership boundaries.

Copyleft components may be used only in a manner consistent with their license obligations. Their presence does not silently relicense UV Studio source. License compatibility is an explicit selection gate for every reused component.

## Evidence before adoption

A foundation dependency is selected only after a reproducible spike proves the required operations on representative real media and records deployment/maintenance/licensing risks. Aspirational roadmap items in an upstream project do not count as implemented capability.
