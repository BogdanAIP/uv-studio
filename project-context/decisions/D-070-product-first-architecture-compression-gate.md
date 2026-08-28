# D-070 — Product-first architecture compression gate before further Agent autonomy

**Status:** Accepted sequencing authority  
**Date:** 2026-08-28

## Context

UV Studio now has a strong modern spine: Project Store, Production Directions, shared Scene/Shot/Take semantics, canonical Timeline, Studio/Application Commands, ProjectUnitOfWork, Model Registry, Generation Job Manager, Capability/D-017 and Agent Harness layers 1-3. Stage 18 / PR #75 adds bounded background Agent execution and also strengthens cross-runtime Production/Timeline/Generation mutation safety.

At the same time, the repository still physically carries overlapping earlier product composition:

- schema-v1 `recipe_id`;
- Recipe Registry and recipe execution;
- Product Orchestrator under `uv_studio/orchestration/**`;
- `/execution-plan`;
- Stage 6/8 workspace/API/frontend surfaces;
- donor-era clients/runtime paths;
- dubbing, targeted-edit, continuity and music logic whose useful state/workflow responsibilities are not yet cleanly separated into modern directions/tools.

Continuing directly from Stage 18 into D-066 layers 5-7 would deepen Agent infrastructure before the product has one clearly proven project-to-export user journey and before duplicate product-composition paths have a bounded retirement plan.

This is a sequencing problem, not a rejection of D-066 or of the Stage-18 implementation.

## Decision

### 1. Keep Stage 18 if its existing review gate passes

PR #75 remains a valid D-066 layer-4 slice. Its worker leases, recovery semantics and shared cross-runtime project mutation fence are useful infrastructure and must not be discarded merely to simplify the architecture.

Stage 18 still requires its existing exact-head CI and Codex review gates before merge.

### 2. Stop Agent-autonomy expansion after Layer 4

After Stage 18 is accepted, merged and lifecycle-closed, the next slice is:

`architecture-compression-inventory`

D-066 layers 5-7 remain accepted target architecture but are deferred until the gates below are satisfied.

### 3. Architecture compression gate

Before further Agent autonomy, the repository must have an accepted exact inventory for the legacy/modern overlap.

For every targeted legacy path the inventory must identify:

- exact backend/API/frontend/test/documentation callers;
- whether the path is modern-runtime, compatibility-only, persisted-project migration-only or dead;
- canonical replacement authority;
- state/data that must survive extraction;
- proof required before removal;
- safe migration/deletion PR order.

The first inventory must cover at least Recipe Registry, `uv_studio/orchestration/**`, `api/recipes.py`, `api/execution.py` and `/execution-plan`, Stage 6/8 surfaces, server compatibility routes and schema-v1 `recipe_id`.

No new caller may be added to a superseded product-composition path while the gate is active unless a later accepted decision explicitly reverses its legacy status.

### 4. Golden vertical gate

Before D-066 layer 5, UV Studio must name and prove one real user-visible Studio path as the product baseline:

```text
New Project
 -> micro_drama
 -> Scene
 -> Shot
 -> named generation Job
 -> Take candidate
 -> Accept
 -> canonical Timeline
 -> Export
```

The proof must exercise the GUI for the user journey. When Agent execution is involved, it must use the same Studio/Application Commands, Generation service/model/job authority and Capability/D-017 boundaries used by GUI/scripts/MCP. No Agent-private project mutation path is allowed.

The golden vertical may be delivered through more than one bounded PR; the gate is about the accepted end-to-end result, not forcing a big-bang implementation.

### 5. Preserve functionality while removing duplicate composition

Architecture compression is not permission to delete useful domain state.

Dubbing, targeted edit, continuity and music logic must be split by responsibility:

- portable/canonical project state stays in modern project/direction authorities where appropriate;
- reusable operations move toward contextual tools/capabilities;
- obsolete recipe/orchestrator/workspace composition can be retired only after caller and migration proof.

### 6. Inventory first, deletion later

`architecture-compression-inventory` is behavior-preserving. It must not delete production paths. It creates the exact caller map and executable retirement sequence.

Actual removal/extraction follows in separate bounded slices with tests and migration evidence.

### 7. Do not replace overengineering with another framework

Use the existing classification vocabulary in `UV_STUDIO_V2_ARCHITECTURE_MAP.md`: **KEEP**, **ADAPT**, **MOVE**, **LEGACY**, **DELETE LATER**.

Prefer simplifying existing documents/processes over introducing another parallel architecture registry. Product Truth remains verification metadata; later simplification may reduce validator/process machinery, but D-067 user-outcome truthfulness remains required.

## Consequences

### Positive

- preserves the useful Stage-18 concurrency/recovery work already under review;
- prevents Layer 5-7 from increasing complexity while old and new product architectures coexist;
- converts vague cleanup into caller-proven migration work rather than deletion by intuition;
- forces the architecture to prove a real product journey before more autonomy infrastructure;
- keeps GUI, Agent, scripts and MCP converged on one command/model/job authority;
- creates a safe path to retire Recipe/Product-Orchestrator/Stage-workspace debt without losing useful dubbing/music/continuity/targeted-edit behavior.

### Cost

- D-066 layer 5 evaluation/repair is intentionally delayed;
- some compatibility code remains temporarily while caller/migration proof is built;
- Stage 18 will exist before a visible autonomous-Agent product surface, but no such product readiness claim is allowed.

## Supersession / precedence

D-070 does **not** supersede D-064, D-065, D-066 or D-067 architectural ownership.

It supersedes only the immediate sequencing assumption that D-066 layer 5 must follow directly after layer 4. The D-066 layer order remains the target order **when Agent autonomy work resumes**.

Until the D-070 gates are satisfied, any document that labels D-066 layer 5 as the unconditional next slice must be read as historical/pre-D-070 sequencing and updated when touched.
