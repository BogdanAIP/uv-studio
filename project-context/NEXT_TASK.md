# Next Task

<!-- uv-next-slice: studio-v2-application-transactions -->

## Goal

After the Studio-v2 editor spine is reviewed, merged and lifecycle-closed, harden the application mutation boundary so multistep Studio actions have one atomic transaction/undo authority before long-running AI model integration begins.

## Required direction

- introduce a file-first `ProjectUnitOfWork` or equivalent UV-owned transaction boundary for coordinated project/timeline mutations;
- give Studio timeline commands durable transaction identity suitable for undo/redo without making MLT state canonical;
- keep GUI, Agent, scripts and MCP on the same semantic command handlers;
- replace growing command/API dispatch switches with explicit handler/service registries where this slice requires it;
- preserve Project Store atomicity, path/integrity rules and portable-state constraints;
- keep recipe/Product Orchestrator/Stage 8 paths as compatibility only and do not grow them;
- do not add cloud/provider integration in this slice;
- do not hide model selection or create a Model Registry prematurely inside transaction infrastructure.

## Completion proof

The slice is complete when a representative multi-command Studio edit can commit atomically, fail/rollback without leaving split project state, and be undone/redone through the same UV-owned application command authority used by programmatic callers.

## Following direction

After transaction/undo foundations are green, the next product vertical is a backend-owned **user-visible Model Registry**, followed by a project-scoped Job Manager and one real named Image AI model from Inspector to registered project asset.

## Entry gate

Begin only from idle `main` after `studio-v2-editor-spine` is merged and lifecycle-closed. Do not start from the archived PR #59 branch.
