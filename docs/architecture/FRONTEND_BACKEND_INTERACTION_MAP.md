# Frontend / Backend Interaction Map — Historical Recovery Snapshot

**Status:** HISTORICAL SNAPSHOT  
**Current authority:** `CURRENT_ARCHITECTURE.md` + D-064

This document originally mapped the Product Truth Recovery interaction model in which Recipe Registry and Product Orchestrator projected project readiness/workspaces over UV-owned domain state.

That diagram is no longer the forward interaction architecture.

## Current interaction shape

```text
Production Direction UI / Studio tools
        -> Studio/Application Commands
        -> Project Unit of Work / domain services
        -> canonical Project Store + Timeline + production documents
        -> Model/Job services where needed
        -> Capability Registry / D-017 / adapters
        -> FFmpeg / MLT / MCP / local or optional remote tools
```

## Evidence retained from the old map

- the frontend must not become canonical workflow/timeline state;
- Project Store/domain state remains UV-owned;
- D-033 commands remain the mutation boundary;
- MLT remains derived behind the UV adapter;
- Capability Registry and D-017 remain execution/authorization boundaries;
- real targeted-edit, dubbing, music and other domain chains may be reused beneath current Studio tools/directions;
- legacy VideoClaw session/task/sandbox routes remain migration debt, not product authority.

Do not expand Product Orchestrator recipe-by-recipe as recommended by the historical version. The original detailed interaction map remains available in Git history.
