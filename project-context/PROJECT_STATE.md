# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-functional-subagents -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 17 is in review on branch `stage-17/agent-functional-subagents`, PR #71. The slice was created from lifecycle-closed `main` commit `145395fe58db811c39bc1099188e15c58736174f` after Stage 16 / PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2`.

The final draft implementation head `dc973c90ac20ab7bac2d4145f58c5df4d69f663c` passed PR CI #3469 (`33097030757`) across all five permanent jobs: development-context, Ubuntu/Windows bootstrap unit suites, and Ubuntu/Windows app-baseline including browser user-outcome E2E.

## Stage-17 implementation under review

D-066 layer 3 adds bounded **functional subagents** over the already merged Agent infrastructure:

```text
Stage 15
  Context Builder / Action Catalog / Policy / Trace
Stage 16
  Planner / Plan / durable Tasks / bounded Skills / foreground coordinator
Stage 17
  bounded functional roles: explore / plan / media / critic
```

The implementation provides:

- `explore` as a bounded advisory role over explicit canonical Agent context;
- `plan` as a bounded structured proposal role whose executable output must pass the existing deterministic Stage-16 `AgentPlanner` before durable Plan/Task creation;
- `media` as a bounded proposal role limited to the existing media/generation/Take/Timeline Agent action subset;
- `critic` as a read-only advisory role over one exact durable Plan/Task/linked-trace set, with no automatic repair authority;
- deterministic full-role-context consistency checks during delegation and again before Plan persistence;
- portable, bounded, explicit-reference role inputs/outputs with fail-closed rejection of malformed, oversized, hidden-field, secret/host-path and unavailable-reference data;
- a stable content-addressed `agent_delegate_<role>_*` identity for every validated role result;
- delegation provenance carried through the existing durable Plan and existing Stage-15 trace path rather than through a second subagent/delegation store;
- post-commit/pre-trace restart recovery that reconstructs the same delegation-linked success trace without replaying the committed effect;
- fail-closed rejection of provenance-blind injected Stage-16 task coordinators.

Focused acceptance proof covers `explore -> plan -> dependent durable Tasks -> foreground execution -> media -> foreground execution -> reopen -> critic`, plus proposer failure/oversized-output rejection with no durable Plan creation and provenance-aware crash recovery.

## Authority stack preserved

Stage 17 reuses rather than replaces:

- Project Store and project `tasks/` root;
- Production Semantic Core and canonical Timeline;
- Studio/Application Commands and `ProjectUnitOfWork`;
- Stage-15 Agent Context/Catalog/Policy/Trace/AgentHarness;
- Stage-16 Planner/Plan/Task/Skill/coordinator contracts;
- Model Registry and Generation Job/Attempt authority;
- Capability Registry / effects / D-017.

Functional subagents remain role factoring above those authorities. They do not gain a private project-write path, provider execution API, second tool registry, second permission authority or background runtime.

## Known limitations

Execution and role delegation remain foreground and bounded. Background Agent workers, leases/heartbeats, autonomous polling, evaluate/repair loops, human takeover/edit/resume and long-form autonomy remain later D-066 layers. This slice does not claim a user-visible autonomous-Agent product surface and does not implement the unrelated desktop updater or a real continuation-provider UI.

`project-context/NEXT_TASK.md` remains the exact Stage-17 scope contract until PR #71 is merged and lifecycle-closed.
