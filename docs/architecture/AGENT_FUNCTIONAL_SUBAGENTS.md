# Functional Subagents — Stage 17

**Status:** review implementation under PR #71  
**Date:** 2026-08-27  
**Decision authority:** D-066

## Purpose

Stage 17 adds the third bounded Agent Harness layer above the merged Stage-15 Context/Catalog/Policy/Trace and Stage-16 Planner/Plan/Task/Skill contracts.

```text
bounded goal
 -> functional role
      explore | plan | media | critic
 -> bounded role context
      explicit canonical-reference inventory
      allowed existing actions / Skills
 -> untrusted structured proposal/findings only
 -> exact role-context digest consistency check
 -> existing AgentPlanner validation (plan/media)
 -> existing AgentTaskCoordinator persistence/execution
 -> existing AgentHarness
 -> existing Production / Timeline / Generation authorities
```

Functional subagents are role factoring, not new application authorities.

## Role boundaries

- `explore` receives bounded canonical Agent context and returns referenced findings only.
- `plan` receives the current bounded Agent action catalog plus explicit Stage-16 Skill descriptions. It may return structured `AgentPlanStepProposal` values, but they are not trusted: the existing Stage-16 `AgentPlanner` validates action/Skill identity, policy, inputs, dependencies and canonical prerequisites before a plan can exist.
- `media` may propose only the bounded media/generation/Take/Timeline subset already present in `AgentActionCatalog`. It cannot invoke a general Skill or create arbitrary project structure.
- `critic` receives a bounded read-only projection of one durable Plan/Task/linked-trace set and returns advisory findings only. Its referenced traces must resolve exactly to the durable Task trace IDs; missing or unrelated trace evidence fails closed. The critic cannot propose repair actions in this slice.

## No second authority

Stage 17 deliberately adds no durable subagent store, no subagent-owned task graph, no tool registry, no permission layer and no provider execution API. The injected synchronous proposer receives only a bounded `AgentSubagentContext`; its returned data is treated as untrusted and must pass strict shape/portability/role validation. Unknown output fields are rejected, so hidden reasoning/provider-private state cannot enter UV Agent state through this contract.

The proposer has no mutation callback in this API. Canonical mutations remain possible only after a planning result is explicitly persisted through the Stage-17 provenance-aware task coordinator and later executed through the existing Stage-16 `AgentTaskCoordinator` / `AgentHarness` authority chain.

## Context consistency

A role result is bound to a deterministic digest of the **entire** bounded role context: request, Stage-15 snapshot, role/action/Skill envelope, explicit available references and critic evidence when present. The coordinator rebuilds that context after the synchronous proposal call and rejects the result if project/Timeline/Jobs/models/Skills/critic evidence changed while the proposer was working.

`persist_plan()` repeats the same check. A plan/media proposal therefore cannot be persisted later against a different canonical/effects context merely because the Stage-16 Planner still considers its individual commands valid. Changed context requires a fresh delegation.

This is optimistic consistency, not a long-held project lock: Stage 17 does not hold canonical mutation locks across model/proposer latency.

## Delegation provenance

Every validated role result receives one stable content-addressed reference of the form `agent_delegate_<role>_<digest>`. The identity is derived from the validated request, bounded context digest, summary, findings and proposals; it is inspection/provenance state, not a new execution authority.

For accepted `plan` and `media` output, the delegation reference is carried into the existing durable Stage-16 Plan canonical references. The same Plan also carries a content-addressed `agent_delegate_bind_<digest>` reference derived from the Plan project/goal plus that delegation ID. Stage-17 execution classifies a typed delegation ID as functional-subagent provenance **only when the exact matching Plan binding is present**. It therefore never infers Stage-17 origin merely because an ordinary Stage-16 canonical identity happens to look like `agent_delegate_<role>_<digest>`.

The binding is not a secret, signature or authorization token. It is deterministic inspection evidence that disambiguates provenance inside the existing Plan record without adding a second state store or changing canonical application authority. Role/action/policy validation remains authoritative for what may execute.

During execution the verified delegation identity is appended to the same Stage-15 trace correlation path already used for Plan/Task/Skill provenance. No second trace or delegation store is introduced.

The same rule applies to restart recovery. If canonical work commits and the process fails before the success trace is durable, Stage-16 reconciliation reconstructs one exact enriched trace containing the delegation reference and uses that same trace object for terminal Task validation. Recovery therefore preserves delegation provenance without replaying the committed effect.

Dependency injection cannot silently bypass this rule. A provenance-blind task coordinator is rejected, an injected Stage-17 coordinator must share the exact `AgentHarness`, Project Store and Planner authority, and a standalone injected Planner must be bound to the exact same `AgentHarness`.

## Reserved delegation namespace

A complete typed delegation identity matches `agent_delegate_(explore|plan|media|critic)_[0-9a-f]{32}`. Prefix-like ordinary IDs such as `agent_delegate_project` remain valid canonical identities and are not misclassified as delegation provenance.

The complete typed namespace is reserved at the Stage-17 boundary for non-critic execution roles. Existing Project/Scene/Shot/Take/Timeline identities that already occupy that namespace cause delegation to fail closed before proposer execution or Plan persistence.

The same reservation is applied to **future canonical outputs proposed by a role**. Stage 17 inspects the caller-selectable output identity fields of supported creation actions and bounded Skills before durable Plan creation, so a proposal cannot create a Scene, Shot, Take, track or clip whose identity masquerades as internal delegation provenance. `critic` remains able to read genuine durable delegation references as evidence.

Ordinary Stage-16 Plans remain free to carry canonical IDs that match the typed text pattern: without the exact Plan-bound `agent_delegate_bind_*` evidence they are treated only as ordinary canonical references, not as Stage-17 origin.

## Execution reference budget

`AgentPlanRecord` and terminal `AgentTaskRecord` each cap canonical references at 128. Shared Stage-16 execution adds bounded task correlation, execution context, affected canonical identities and result identities after planning.

The final Planner therefore limits durable Plan canonical references to **112**, reserving 16 slots for execution-time provenance. The shared executor repeats the same check immediately before dispatch, so an older or externally persisted Plan above the execution-safe limit is rejected while its Task is still `READY`, before execution evidence, canonical mutation or cost-bearing provider dispatch can begin.

This boundary is shared Stage-16 execution safety rather than Stage-17-only bookkeeping: Stage 17 delegation provenance and its Plan binding consume the existing Plan reference path and must remain compatible with the same bounded terminal Task/Trace contract.

## Reference and portability rules

Requests, findings and outputs reuse the Stage-15 portable-state rules: no secrets/tokens, no absolute host paths and bounded serialized payloads.

`available_references` is built from **explicit identity fields** in the bounded Stage-15 context and, for `critic`, explicit durable Plan/Task/Trace reference fields. Titles, summaries, status strings and other identifier-looking text do not become references accidentally. Finding references must be members of this explicit inventory.

Plan proposals may contain new entity IDs only as inputs to existing validated creation actions; the Stage-16 Planner remains authoritative for whether those future identities and dependency chains are valid, while Stage 17 additionally reserves its internal delegation namespace as described above.

## Critic versus evaluate/repair

The Stage-17 critic is observation only. It can inspect durable plan/task/trace outcomes and report warnings/errors, but it cannot mutate the Plan, create repair tasks or loop automatically. Evaluation plus dependency-aware repair remains D-066 layer 5, after background execution is designed separately in layer 4.

## Foreground-only boundary

Delegation is synchronous. There are no background workers, leases, heartbeats, polling or autonomous continuation in this slice. Those remain D-066 layer 4 and later.

## Verification

Stage 17 uses the repository's permanent exact-head gate before merge:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)` including browser user-outcome E2E;
- `app-baseline (windows-latest)` including browser user-outcome E2E.

The authoritative exact code-bearing SHA and CI run are recorded in `project-context/PROJECT_STATE.md` and PR #71 after the final code/docs head is green.

Focused Stage-17 tests prove bounded multi-role flow, Plan/Task/Trace delegation provenance, shared-executor execution and recovery, reopen, post-commit/pre-trace crash recovery without replay, malformed/oversized/unknown-role rejection, result-integrity and role revalidation, complete namespace collision handling for existing and proposed canonical identities, Plan-bound provenance classification that ignores unbound delegation-looking Stage-16 canonical IDs, exact-harness dependency-injection boundaries, and execution-reference budgeting including a legacy oversized Plan rejected before dispatch.

## Product Truth boundary

This is internal Agent infrastructure. No user-visible autonomous-Agent readiness claim is made without a separate Studio surface and D-067 Product Truth/browser proof.
