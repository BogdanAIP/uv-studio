# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-agent-planner-durable-tasks-skills -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 16 is active in draft on branch `stage-16/agent-planner-durable-tasks-skills`, created from lifecycle-closed idle `main` commit `fdc82fbdbd518e711a5f4b36d01cdbc6745a7e40`.

Goal: implement D-066 Agent Harness layer 2 only — bounded validated Planner output, durable project-scoped Agent Tasks with explicit dependency/state semantics, reusable bounded Skills, and foreground execution through the existing Stage-15 Agent Harness and UV application authorities.

Stage 15 / PR #69 merged as `273b5ea8f979cf759cfbf6510e1215a55e98d9c9` and was lifecycle-closed before this branch was created. The closure head passed all five permanent CI jobs on Ubuntu/Windows, including browser E2E.

## As-built authority entering Stage 16

The new layer must reuse, not replace:

- canonical Project Store and existing `tasks/` project root;
- Production Semantic Core and canonical Timeline;
- Studio/Application Commands and `ProjectUnitOfWork`;
- Stage-15 `AgentContextBuilder`, `AgentActionCatalog`, policy projection, `AgentHarness` and append-only Agent trace;
- Model Registry and project-scoped Generation Job/Attempt authority;
- Capability Registry / effects / D-017 authorization.

Agent Tasks coordinate orchestration state; they are not Generation Jobs, canonical production state or Undo/Redo history. Skills are bounded procedures over approved Agent catalog actions, not arbitrary plugin execution rights.

## Active slice

`studio-v2-agent-planner-durable-tasks-skills`

```text
bounded production goal
 -> Stage-15 context/catalog/policy
 -> validated Planner plan
 -> durable dependency-aware Agent Tasks
 -> bounded Skills expand to approved catalog work
 -> foreground execution through AgentHarness
 -> existing Production/Timeline/Generation authorities
 -> trace + task records link results to canonical identities
```

## Explicit non-goals

- no functional subagents (`explore`, `plan`, `media`, `critic`) — D-066 layer 3;
- no background Agent work through Job Manager — layer 4;
- no critic/evaluation + dependency-aware repair — layer 5;
- no human takeover/edit/resume orchestration — layer 6;
- no long-form autonomous production — layer 7;
- no Agent-only project write path, shell/Python authority or duplicate tool/permission system;
- no unrelated desktop updater or continuation-provider implementation.

`project-context/NEXT_TASK.md` is the exact Stage-16 scope contract until this slice is reviewed, merged and lifecycle-closed.
