# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-functional-subagents -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 17 is in review on branch `stage-17/agent-functional-subagents`, PR #71. The slice was created from lifecycle-closed `main` commit `145395fe58db811c39bc1099188e15c58736174f` after Stage 16 / PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2`.

The current code-bearing review baseline is exact head `9af22cdcbb60501dca968fd10f12dc1d40ee6482`. PR CI #3488 (`33101350599`) passed all five permanent jobs on that exact head: `development-context`, Ubuntu/Windows bootstrap unit suites, and Ubuntu/Windows app-baseline including browser user-outcome E2E. The parallel push run #3487 had one isolated Windows named-generation browser timing failure while the same exact PR head independently passed that Windows browser suite in #3488; no code or product state changed between those runs.

The fresh Codex review of earlier head `aafddd3b37476a65558d56755edd2ae440648b74` reported four follow-up findings. The code-bearing baseline above addresses them by synchronizing authoritative architecture with the active review state, distinguishing complete typed delegation references from arbitrary canonical IDs that merely share the prefix, and rejecting injected Stage-17 task coordinators that do not share the exact harness/project-store/planner authority. This metadata update records the resulting exact-head evidence; its own exact head must still pass the declared checks before merge.

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
- delegation provenance carried through the existing durable Plan and existing Stage-15 trace path rather than through a second subagent/delegation store;
- post-commit/pre-trace restart recovery that reconstructs the same delegation-linked success trace without replaying the committed effect;
- shared Stage-16 task execution/recovery preservation of durable Plan provenance;
- fail-closed task-coordinator injection unless the coordinator shares the exact Stage-17 provenance contract, AgentHarness, Project Store and Planner authority.

Focused acceptance proof covers `explore -> plan -> dependent durable Tasks -> foreground execution -> media -> foreground execution -> reopen -> critic`, plus proposer failure/oversized-output rejection with no durable Plan creation, persistence-time forged-result rejection, prefix-collision proof using canonical project ID `agent_delegate_project`, foreign-harness coordinator rejection, shared-executor provenance, and provenance-aware crash recovery.

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
