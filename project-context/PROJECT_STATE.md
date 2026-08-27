# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-functional-subagents -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 17 is in review on branch `stage-17/agent-functional-subagents`, PR #71. The slice was created from lifecycle-closed `main` commit `145395fe58db811c39bc1099188e15c58736174f` after Stage 16 / PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2`.

The current code-bearing review baseline is exact head `7c8280721d96e7822d3c56e08e00ff6cb3868349`. PR CI #3495 (`33104177080`) passed all five permanent jobs on that exact head: `development-context`, Ubuntu/Windows bootstrap unit suites, and Ubuntu/Windows app-baseline including browser user-outcome E2E.

Codex review of `10643bd160c65b8d8df690266390725d5d0dd6eb` reported two final P2 findings: a complete typed `agent_delegate_<role>_<digest>` string was still a valid canonical identity and could collide with delegation provenance, and a standalone injected Planner could be bound to a foreign AgentHarness. The code-bearing baseline above addresses both: Stage 17 reserves the complete typed delegation namespace from non-critic canonical role context before proposal or durable Plan creation, and any explicitly supplied Planner must share the exact AgentHarness authority. Regression proof covers both fail-closed boundaries and same-harness Planner injection. No additional Codex review is required for this slice; the remaining gate is exact-head CI for this metadata update and resolution of the two existing review threads.

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
- a stable content-addressed `agent_delegate_<role>_<digest>` identity for every validated role result, recognized only by the complete typed role-and-digest format rather than by prefix alone;
- reservation of that complete typed delegation namespace from non-critic canonical role context, so a canonical Project/Scene/Shot/Take/Timeline identity cannot masquerade as delegation provenance;
- delegation provenance carried through the existing durable Plan and existing Stage-15 trace path rather than through a second subagent/delegation store;
- post-commit/pre-trace restart recovery that reconstructs the same delegation-linked success trace without replaying the committed effect;
- shared Stage-16 task execution/recovery preservation of durable Plan provenance;
- fail-closed task-coordinator injection unless the coordinator shares the exact Stage-17 provenance contract, AgentHarness, Project Store and Planner authority;
- fail-closed standalone Planner injection unless the Planner shares the exact AgentHarness authority.

Focused acceptance proof covers `explore -> plan -> dependent durable Tasks -> foreground execution -> media -> foreground execution -> reopen -> critic`, plus proposer failure/oversized-output rejection with no durable Plan creation, persistence-time forged-result rejection, prefix-collision proof using canonical project ID `agent_delegate_project`, exact typed-namespace collision rejection using canonical project ID `agent_delegate_media_00000000000000000000000000000000`, foreign-harness coordinator rejection, foreign standalone-Planner rejection, same-harness Planner injection, shared-executor provenance, and provenance-aware crash recovery.

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
