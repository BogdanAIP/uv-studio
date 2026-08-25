# D-062 — Product Truth Recovery Gate

**Status:** Accepted for product-truth invariants; Product Orchestrator center superseded by D-063/D-064  
**Date:** 2026-08-20

## Decision history

D-062 responded to a real product failure: package/release engineering could pass while the installed application still exposed disconnected frontend eras, stale runtime promises and hidden prerequisites. It established a mandatory Product Truth Recovery gate before further release work.

Those product-truth lessons remain active. Its temporary choice of Product Orchestrator as the user-facing recovery center does not.

## Invariants that remain accepted

1. User-visible readiness/actions must be backed by reachable UV-owned execution or canonical state.
2. Do not advertise unmounted legacy runtime targets.
3. Setup-dependent/incomplete behavior must fail closed and explain prerequisites.
4. Project Store remains canonical; old donor session/project state must not return as a competing authority.
5. GUI, Agent, MCP and scripts converge on shared semantic/application actions.
6. Do not remount the complete legacy VideoClaw backend merely to satisfy obsolete frontend callers.
7. Preserve capability/security boundaries, deterministic media adapters and useful domain work.
8. Cold-start UI evidence and installed-app acceptance remain valuable product proof.

## Superseded clause

The statement that **Product Orchestrator owns the long-term user-facing readiness/workspace/next-action product center** is superseded.

D-064 now defines the product center as Production Directions over the shared Studio Core, with Studio/Application Commands, Project Unit of Work, Model/Job services and Capability/Adapter boundaries underneath. Existing Product Orchestrator code is compatibility/migration infrastructure until dependency-proven retirement.

The original full D-062 audit context and recovery consequences remain available in Git history.
