# D-062 — Product Truth Recovery Gate

**Status:** Accepted  
**Date:** 2026-08-20

## Context

Stage 9 demonstrated that package integrity, native Windows hosting and release automation can pass while a human installed-app review still finds UV Studio confusing and apparently non-functional. A repository/history audit found deeper pre-Stage-9 drift:

- Stage 3.5 intentionally stopped mounting the complete legacy VideoClaw backend;
- recipe execution metadata and legacy frontend clients can still describe old routes as executable;
- some visible recipes lack a complete current UV-owned journey;
- frontend components directly coordinate multiple domain state machines and hidden prerequisites;
- D-033 reuse-first editor intent has drifted toward increasing UV-owned editor behavior while MLT is mostly projection/render;
- informed E2E tests can pass with state/test knowledge unavailable to a first-time user.

## Decision

Introduce a mandatory Product Truth Recovery Gate before Stage 9 can become the maintained product baseline.

Invariants:

1. User-visible readiness is backed by current reachable UV-owned execution.
2. No execution plan may advertise an unmounted target.
3. Setup-dependent/incomplete workflows are explicitly gated before use.
4. Product Orchestrator owns user-facing readiness, prerequisites and next actions.
5. GUI, AI, MCP and scripts converge on shared semantic product actions incrementally.
6. D-033 editor ownership/reuse is re-evaluated before generic NLE growth.
7. Permanent scenarios require cold-start UI-only evidence and installed-app human acceptance.
8. Existing Project Store, capability/security boundaries, deterministic media adapters and archived Stage 9 packaging work are preserved unless separate evidence justifies replacement.

## Consequences

- PR #38 is archived closed without merge; its branch remains engineering reference for Stage 9 packaging/native-shell work.
- Recovery begins from `main`, because the product-truth drift predates Stage 9.
- Signing/publication is lower priority than restoring product truth.
- `general_video`, `narrated_video`, `action_transfer`, `digital_human` and all other recipes must be audited against current mounted paths and executable adapters.
- stale VideoClaw-derived compatibility code is retired only after dependency/call-site evidence.
- Photo-to-video and Visualizer remain reference examples of the intended intent-to-result UX.

## Rejected alternatives

### Continue Stage 9 visual polish
Rejected because the audit found execution-contract and orchestration defects that styling cannot solve.

### Remount the complete VideoClaw backend
Rejected because it would reopen the security/authorization bypasses Stage 3.5 intentionally closed.

### Rewrite UV Studio from scratch
Rejected because substantial Project Store, capability, media, domain-state and packaging work is proven and reusable.

### Treat current E2E as sufficient product proof
Rejected because informed tests can seed or know state a first-time user cannot.
