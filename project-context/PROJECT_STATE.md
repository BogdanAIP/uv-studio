# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-application-transactions -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 11 `studio-v2-application-transactions` is active from idle `main` `44b5483a956a72b4532839b8f4222c1433bed8e4`.

The completed Studio-v2 editor spine remains PR #61, exact review head `713d55c0f8d6f8de09df12db07e74b2d39ef4f79`, merge `5be716ed44ac00f7d13cafb8b4ed038ddc24878b`. Its permanent review checks passed on Ubuntu and Windows, including browser user-outcomes.

## Why this slice exists

The Studio spine now has one canonical `timeline/main.json` and one semantic `TimelineCommandService`, but each command still performs an independent read -> build -> save sequence. `TimelineStore.save()` atomically replaces one JSON file, yet there is no application transaction spanning timeline state, project metadata/references and durable undo history.

That is safe enough for the first single-command editor proof, but it is not sufficient for professional editing or future AI actions where one user action may create assets, register references and mutate the timeline together. A crash or validation failure must not leave split project state, and Agent/MCP callers must not invent their own rollback logic.

## Slice authority

This slice must introduce a UV-owned transaction boundary with these properties:

- one project-scoped lock/transaction authority for coordinated writes;
- staged writes are validated before commit;
- commit is all-or-nothing across the files owned by one Studio action;
- every committed mutation gets durable transaction identity;
- undo and redo use the same canonical application authority, not frontend-only history;
- MLT remains derived and is never snapshotted as project truth;
- GUI, Agent, scripts and MCP keep using the same semantic command layer;
- recipes, Product Orchestrator and Stage 8 remain compatibility paths and do not grow;
- no provider/cloud/model integration belongs in this slice.

## Completion proof

A representative multi-step Studio edit must be able to:

1. commit canonical project/timeline changes atomically;
2. fail after staging without exposing partial project state;
3. survive reload with durable transaction identity;
4. undo back to the exact previous canonical state;
5. redo to the exact committed state;
6. exercise the same command boundary through HTTP/programmatic callers.

## Known design constraint

Project Store is file-first and portable. Transaction history therefore must also be project-owned, bounded and deterministic. Do not introduce a hidden database or an in-memory-only undo stack.

## Product direction after this slice

The next declared handoff is `studio-v2-model-registry`: a backend-owned, user-visible registry that maps semantic AI tools to explicit model choices without making provider configuration the product workflow. Job Manager and the first real Image AI vertical follow after that foundation.

Historical Release #395 on archived #59 remains packaging/runtime engineering evidence only and is not product acceptance.

`main` branch protection remains intentionally deferred per current development direction.
