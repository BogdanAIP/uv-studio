# Functional Subagents — Stage 17

**Status:** draft implementation under PR #71  
**Date:** 2026-08-27  
**Decision authority:** D-066

## Purpose

Stage 17 adds the third bounded Agent Harness layer above the merged Stage-15 Context/Catalog/Policy/Trace and Stage-16 Planner/Plan/Task/Skill contracts.

```text
bounded goal
 -> functional role
      explore | plan | media | critic
 -> bounded role context
 -> proposal/findings only
 -> existing AgentPlanner validation (plan/media)
 -> existing AgentTaskCoordinator persistence/execution
 -> existing AgentHarness
 -> existing Production / Timeline / Generation authorities
```

Functional subagents are role factoring, not new application authorities.

## Role boundaries

- `explore` receives bounded canonical Agent context and returns referenced findings only.
- `plan` may return structured `AgentPlanStepProposal` values, but they are not trusted: the existing Stage-16 `AgentPlanner` validates action/Skill identity, policy, inputs, dependencies and canonical prerequisites before a plan can exist.
- `media` may propose only the bounded media/generation/Take/Timeline subset already present in `AgentActionCatalog`. It cannot invoke a general Skill or create arbitrary project structure.
- `critic` receives a bounded read-only projection of one durable Plan/Task/linked-trace set and returns advisory findings only. It cannot propose repair actions in this slice.

## No second authority

Stage 17 deliberately adds no durable subagent store, no subagent-owned task graph, no tool registry, no permission layer and no provider execution API. The injected synchronous proposal provider receives only a bounded `AgentSubagentContext` and can return only the strict output contract. Unknown output fields are rejected, so hidden reasoning/provider-private state cannot be smuggled into UV state.

The provider has no `execute` callback. Canonical mutations remain possible only after a planning result is explicitly persisted through `AgentTaskCoordinator.create_plan()` and later executed through the existing `AgentTaskCoordinator.execute_task()` / `AgentHarness` authority.

## Reference and portability rules

Requests, findings and outputs reuse the Stage-15 portable-state rules: no secrets/tokens, no absolute host paths and bounded serialized payloads. Finding references must already occur in the bounded subagent context/evidence, preventing a role from inventing an inspectable canonical reference.

Plan proposals may contain new entity IDs only as inputs to existing validated creation actions; the Stage-16 Planner remains authoritative for whether those future identities and dependency chains are valid.

## Critic versus evaluate/repair

The Stage-17 critic is observation only. It can inspect durable plan/task/trace outcomes and report warnings/errors, but it cannot mutate the Plan, create repair tasks or loop automatically. Evaluation plus dependency-aware repair remains D-066 layer 5, after background execution is designed separately in layer 4.

## Foreground-only boundary

Delegation is synchronous. There are no background workers, leases, heartbeats, polling or autonomous continuation in this slice. Those remain D-066 layer 4 and later.

## Product Truth boundary

This is internal Agent infrastructure. No user-visible autonomous-Agent readiness claim is made without a separate Studio surface and D-067 Product Truth/browser proof.
