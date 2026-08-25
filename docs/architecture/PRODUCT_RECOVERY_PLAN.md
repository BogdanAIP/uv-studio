# Product Recovery Plan — Historical Record

**Status:** HISTORICAL — recovery plan completed/superseded as forward architecture  
**Current authority:** `CURRENT_ARCHITECTURE.md` + D-064

This document originally guided Product Truth Recovery after the repository accumulated a split between legacy VideoClaw surfaces, recipe-driven project UX and current UV-owned backend boundaries.

The recovery work produced important lasting results: legacy runtime isolation, truthful fail-closed behavior, Project Store authority, cold-start evidence, domain-state validation and several usable media/domain paths.

Its former target architecture centered Product Orchestrator and recipe-by-recipe recovery. That is no longer the forward product model.

## Retained lessons

- visible actions must reach current executable UV-owned paths;
- old frontend/runtime surfaces must not be advertised when their backend is absent;
- Project Store remains canonical;
- capability/security boundaries remain explicit;
- historical domain implementations should be reused behind current Studio tools/directions when useful;
- cold-start and installed-app evidence remain valuable.

## Superseded direction

Do not continue the old sequence of expanding Product Orchestrator recipe-by-recipe or restoring Stage workspaces as product navigation. New work follows D-064 Production Directions over the shared Studio Core.

The original detailed recovery plan remains available in Git history.
