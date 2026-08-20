# D-062 — Product Truth Recovery Gate

**Status:** Accepted  
**Date:** 2026-08-20

## Context

Stage 9 reached a state where packaging, native Windows hosting, installer/update/rollback, legal probes and release integrity could pass automated checks while a human Windows 10 installed-app review still found the product confusing and apparently non-functional.

A broader repository/history audit then found that the problem is not limited to Stage 9 styling:

- Stage 3.5 intentionally stopped mounting the complete legacy VideoClaw backend for security/authorization reasons;
- some recipe execution metadata and legacy frontend clients still describe old `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models` and related routes as if they were current product execution paths;
- some recipes are visible as product modes without a complete current UV-owned user journey;
- the frontend has accumulated direct knowledge of multiple domain state machines and prerequisites instead of receiving one product-level workflow/next-action projection;
- D-033 selected a reuse-first MLT/OpenCut direction, but the implementation has drifted toward increasing UV-owned editor/timeline UI while MLT is largely a projection/render adapter;
- browser regression tests can exercise informed scripted paths and seeded state without proving cold-start discoverability or truthful setup requirements.

Therefore release automation alone is insufficient evidence for product readiness.

## Decision

Introduce a mandatory **Product Truth Recovery Gate** before Stage 9 may merge.

The gate is defined in `docs/architecture/PRODUCT_RECOVERY_PLAN.md` and has these invariants:

1. User-visible readiness is derived from actually reachable UV-owned execution paths.
2. No execution plan may advertise an unmounted target.
3. Unavailable/optional/setup-dependent workflows are explicitly gated before the user starts them.
4. A Product Orchestrator becomes the user-facing projection of workflow state, prerequisites and next actions; the frontend must not remain the primary orchestrator of independent backend state machines.
5. GUI, AI, MCP and scripts converge on the same semantic action/command model incrementally.
6. D-033 reuse-first editor ownership is re-evaluated before UV Studio grows further generic NLE functionality.
7. Permanent release scenarios require cold-start UI evidence without test-only state seeding, plus human installed-app acceptance.
8. Existing Project Store, capability/security boundaries, deterministic media adapters and Stage 9 packaging/integrity work are preserved unless separate evidence justifies replacement.

## Consequences

- PR #38 remains Draft and must not merge merely because CI/release workflows are green.
- Trusted signing/publication work is lower priority than restoring product truth and user outcomes.
- The next recovery implementation slice starts with Product Truth Inventory and recipe/execution contract repair, not visual redesign.
- `general_video`, `narrated_video`, `action_transfer`, `digital_human` and every other recipe must be audited against mounted routes and actual executable adapters.
- Stale VideoClaw-derived frontend/API compatibility code is retired only after dependency evidence; it is not deleted indiscriminately.
- Photo-to-video and Visualizer are retained as examples of the desired intent-to-result product shape.
- Stage 9 resumes only after the Product Truth Gate passes, at which point preserved packaging/native-shell work is reconciled with the recovered product.

## Rejected alternatives

### Continue Stage 9 UX polish until the installed app feels better

Rejected because the audit found backend/frontend truth mismatches and missing execution paths that cannot be solved by styling or disabled-button copy.

### Roll back Stage 3.5 and remount the complete VideoClaw backend

Rejected because it would reopen the authorization, secret and provider-safety bypasses that Stage 3.5 deliberately closed.

### Rewrite UV Studio from scratch

Rejected because Project Store, capability authorization, provenance, deterministic media execution, domain state and Stage 9 packaging contain substantial proven value.

### Treat current automated E2E as sufficient product proof

Rejected because informed tests can know hidden prerequisites and seed state that a first-time user cannot.

## Verification required to supersede this decision

A future architecture may supersede D-062 only with evidence that all permanent user journeys are truthful, reachable and cold-start usable through the installed product while preserving or deliberately replacing the existing security/project/runtime invariants.
