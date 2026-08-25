# Product Orchestrator — Historical Compatibility Record

**Status:** HISTORICAL / COMPATIBILITY — not current target architecture  
**Current authority:** `CURRENT_ARCHITECTURE.md` + D-064

Product Orchestrator was introduced during Product Truth Recovery to project readiness, prerequisites, relevant workspaces and next actions over existing recipe/domain state without creating another durable workflow database.

It was useful for recovering truthful paths while the product was still organized around recipes. That role must not be interpreted as the future UV Studio application center.

## What remains useful

- readiness and prerequisite projection patterns;
- explicit fail-closed setup state;
- semantic actions over canonical domain state;
- separation between UV-owned decisions and capability-backed execution;
- evidence that Project Store/domain stores remain canonical.

## Current classification

Existing Product Orchestrator code is migration/compatibility infrastructure. New Production Directions must not be implemented as new Orchestrator recipe graphs or `relevant_workspaces` expansions.

Current product composition is:

```text
Project -> Production Direction -> direction-specific state -> shared Studio Core
        -> Commands / Unit of Work -> Models / Jobs -> Capabilities / Adapters
```

Runtime removal is a separate dependency-proven task. The detailed original Product Orchestrator target document remains available in Git history.
