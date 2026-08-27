# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: studio-v2-agent-planner-durable-tasks-skills -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 16 is implemented, merged in PR #70 and lifecycle-closed to idle `main`.

- merged slice: `studio-v2-agent-planner-durable-tasks-skills`;
- final reviewed PR head: `3478bb17e21fb0f02b4a456a61baf4c0ad941c22`;
- merge commit: `bd258b7564f864c7f5fe636cb1336515f0dacce2`;
- exact-head CI #3442 (`33065539562`) completed successfully across all five permanent jobs, including Ubuntu/Windows unit suites and both app-baseline browser E2E suites;
- fresh Codex review on the exact final head reported no major issues;
- every inline review thread was resolved before merge.

There is no active implementation branch or PR. The one declared handoff is `studio-v2-agent-functional-subagents`, described in `project-context/NEXT_TASK.md`.

## Merged Agent Harness foundation

D-066 now has two merged internal layers:

```text
Stage 15
  Context Builder
  Action Catalog
  Policy projection
  Agent Trace
  AgentHarness execution seam

Stage 16
  validated Planner
  append-only Plan descriptors
  durable dependency-aware Agent Tasks
  bounded versioned Skills
  foreground task coordination
  execution-time context/policy evidence
  typed trace correlation
  restart/reopen recovery without replay
```

Stage 16 preserves existing UV authorities rather than creating a second project or execution graph. Agent work continues to reference canonical Project / Scene / Shot / Take / media / Timeline / transaction / Generation Job identities and executes through existing Production, Timeline and Generation services.

## Stage-16 reliability boundary now merged

The merged implementation includes:

- canonical prerequisite validation before Plan persistence, including dependency-closure provisioning;
- rejection of duplicate planned Scene/Shot identities and deterministically invalid missing Take/track/clip/media references;
- exclusive planned `production.accept_take` per Shot and validation that dependency-created acceptance tracks are video tracks;
- cross-runtime task CAS and project-scoped locking with one lock order and Windows contention handling;
- append-only Plan create-if-absent semantics;
- exact execution-time context and policy evidence before canonical/cost-bearing dispatch;
- generation preparation binding to the exact frozen policy, model/capability/offer/adapter mapping and request digest;
- D-017 authorization remaining execution-only and outside durable Plan/Task state;
- typed plan/task/Skill trace correlation with exact input digest and execution window;
- recovery from committed `ProjectUnitOfWork` and exact Generation Job evidence without silently replaying canonical or cost-bearing work;
- reconstruction of affected Shot/track/clip identities for recovered Production/Timeline traces.

Agent Tasks remain orchestration state, not canonical Production/Timeline truth, Undo/Redo history or Generation Job provenance. Skills remain bounded procedures over approved Agent catalog actions and gain no shell, Python, arbitrary filesystem/provider or private authorization path.

## Next D-066 handoff

The next accepted layer is **functional subagents**: bounded `explore / plan / media / critic` roles that consume the merged Context / Planner / Task / Skill contracts.

This next slice must remain foreground and bounded. Background Agent work is still the following D-066 layer, followed by evaluation/repair, human takeover/edit/resume and only then long-form autonomy.

## Known limitations

UV Studio still does not claim a user-visible autonomous-Agent product surface. Functional subagents, background execution, automatic critic/repair loops, takeover/resume orchestration and long-form autonomy remain future work. The unrelated D-068 desktop updater and a real continuation-provider UI are also outside the completed Stage-16 slice.
