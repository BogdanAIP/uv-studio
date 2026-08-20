# D-062 — Product Truth Recovery Gate

**Status:** Accepted  
**Date:** 2026-08-20

## Context

Stage 9 demonstrated that package integrity, native Windows hosting and release automation can pass while a human installed-app review still finds UV Studio confusing and apparently non-functional. A repository/history audit found deeper pre-Stage-9 drift:

- Stage 3.5 intentionally stopped mounting the complete legacy VideoClaw backend;
- Stage 8 recipe execution metadata still advertised some removed `/api/pipelines/*` targets as available;
- the live Stage 8 frontend itself still contains `workflowApi.ts`, old `HomePage`/`WorkflowPanel`, real `/pipelines/*` pages and a root `AppShell` that exposes legacy pipeline/session/task/sandbox concepts in normal navigation;
- those live legacy pages call backend route families Stage 3.5 intentionally no longer mounts;
- the newer `/projects` architecture separately loads many unrelated specialist panels for every recipe, so selecting a task does not isolate its workflow;
- some visible recipes lack a complete current UV-owned journey;
- newer frontend components directly coordinate multiple domain state machines and hidden prerequisites;
- D-033 reuse-first editor intent has drifted toward increasing UV-owned editor behavior while MLT is mostly projection/render;
- informed E2E tests can pass with state/test knowledge unavailable to a first-time user.

The problem is therefore not just a stale adapter or styling bug. Two frontend eras and two project/task mental models coexist in the shipped source while only one backend runtime boundary remains supported.

## Decision

Introduce a mandatory Product Truth Recovery Gate before Stage 9 can become the maintained product baseline.

Invariants:

1. User-visible readiness is backed by current reachable UV-owned execution.
2. No execution plan may advertise an unmounted target.
3. Main navigation may not advertise legacy runtime surfaces whose backend contracts are absent.
4. Setup-dependent/incomplete workflows are explicitly gated before use.
5. Product Orchestrator owns user-facing readiness, prerequisites, relevant workspaces and next actions.
6. Project Store remains the single canonical project authority; old VideoClaw session/project state must not return as a competing product model.
7. GUI, AI, MCP and scripts converge on shared semantic product actions incrementally.
8. The complete legacy VideoClaw backend is not remounted merely to make old frontend code work.
9. D-033 editor ownership/reuse is re-evaluated before generic NLE growth.
10. Permanent scenarios require cold-start UI-only evidence and installed-app human acceptance.
11. Existing Project Store, capability/security boundaries, deterministic media adapters and archived Stage 9 packaging work are preserved unless separate evidence justifies replacement.

## Consequences

- PR #38 is archived closed without merge; its branch remains engineering reference for Stage 9 packaging/native-shell work.
- Recovery begins from Stage 8 `main`, because product-truth drift predates Stage 9.
- Signing/publication is lower priority than restoring product truth.
- `narrated_video` and `action_transfer` fail closed until current executable UV-owned workflows exist.
- `general_video`, `digital_human` and all other recipes are audited against current domain/capability paths, not historical donor promises.
- live `workflowApi`/pipeline/session/task/sandbox surfaces must be isolated, migrated or retired from normal product navigation; they are not treated as harmless vendor provenance.
- pinned `vendor/` code remains provenance/compatibility material unless a separate dependency decision removes it.
- Product Orchestrator is added over existing canonical/domain/capability state rather than replacing the proven backend with one giant controller.
- Photo-to-video and Visualizer remain reference examples of the intended intent-to-result UX.

## Rejected alternatives

### Continue Stage 9 visual polish
Rejected because the audit found execution-contract, dual-frontend and orchestration defects that styling cannot solve.

### Remount the complete VideoClaw backend
Rejected because it would reopen the security/authorization bypasses Stage 3.5 intentionally closed and reintroduce a competing project/session authority.

### Keep legacy pages indefinitely because they compile
Rejected because the root AppShell exposes them as normal product navigation while their required backend contracts are absent.

### Rewrite UV Studio from scratch
Rejected because substantial Project Store, capability, media, domain-state and packaging work is proven and reusable.

### Treat current E2E as sufficient product proof
Rejected because informed tests can seed or know state a first-time user cannot and can pass while unrelated/broken navigation remains visible.
