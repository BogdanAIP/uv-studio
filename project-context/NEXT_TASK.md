# Next Task

<!-- uv-next-slice: studio-v2-application-transactions -->

## Goal

After Production Directions are reviewed, merged and lifecycle-closed, harden the application mutation boundary so multistep production actions have one atomic transaction/undo authority before long-running AI model integration begins.

## Required direction

- introduce a file-first `ProjectUnitOfWork` or equivalent UV-owned transaction boundary for coordinated project, production-document, asset/reference and timeline mutations;
- give Studio application/domain commands durable transaction identity suitable for undo/redo without making MLT state canonical;
- prove at least one representative cross-document transaction, not only isolated timeline edits;
- keep GUI, Agent, scripts and MCP on the same semantic command handlers;
- replace growing command/API dispatch switches with explicit handler/service registries where this slice requires it;
- preserve Project Store atomicity, path/integrity rules and portable-state constraints;
- keep Production Direction identity separate from execution/provider selection;
- keep recipe/Product Orchestrator/Stage 8 paths as compatibility only and do not grow them;
- do not add cloud/provider integration in this slice;
- do not hide model selection or create a Model Registry prematurely inside transaction infrastructure.

## Completion proof

The slice is complete when a representative semantic production operation can coordinate multiple canonical project-owned documents atomically, fail/rollback without leaving split state, and be undone/redone through the same UV-owned application command authority used by programmatic callers.

A suitable proof may use a small direction-domain fixture or bounded production record plus asset/timeline mutation; it must demonstrate the transaction architecture required later for operations such as accepting a generated take into a Shot and Timeline.

## Following direction

After transaction/undo foundations are green, establish the first real direction-domain vertical (micro-drama Scenes/Shots/Characters/Locations/Takes is the preferred candidate) and then add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the shared Studio tools.

## Entry gate

Begin only from idle `main` after `studio-v2-production-directions` is merged and lifecycle-closed. Do not start from archived PR #59 or from the merged PR #61 branch.
