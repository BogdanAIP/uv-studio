# Next Task

<!-- uv-next-slice: studio-v2-agent-functional-subagents -->

## Goal

Build **D-066 Agent Harness layer 3: functional subagents** on top of the merged Stage-15 Context/Catalog/Policy/Trace foundation and merged Stage-16 Planner/Plan/Task/Skill contracts.

The slice is `studio-v2-agent-functional-subagents`:

```text
bounded production goal
 -> Agent context
 -> functional role selection/delegation
      explore
      plan
      media
      critic
 -> bounded role output
 -> Stage-16 Planner / durable Tasks / Skills
 -> Stage-15 AgentHarness
 -> existing Production / Timeline / Generation authorities
```

The purpose is to prove useful specialization and delegation without adding background workers, a second project graph, private tool permissions or long-form autonomous production.

## Required direction

- add a small UV-owned **functional subagent contract** with stable role IDs and versioned bounded input/output schemas;
- roles consume the existing bounded Agent context and canonical identities rather than copying the Project into private role state;
- roles may propose observations, structured planning input, media/model choices or critique/evaluation facts, but executable mutations must still become validated Stage-16 Plan/Task/Skill work and execute through the existing AgentHarness/application authorities;
- role selection/delegation must be inspectable and deterministic enough to validate even when a future model supplies role output;
- preserve D-017, Capability effects, locality/cost and Model Registry visibility exactly as existing authorities expose them;
- carry role identity into the existing Agent trace/task correlation where useful, without creating a competing trace store;
- keep role contexts/results bounded, portable and free of secrets, authorization tokens, absolute host paths, provider-private state and hidden model reasoning;
- keep execution foreground for this slice. **Background Agent workers remain D-066 layer 4.**

## Initial role boundaries

### `explore`

Read/inspect bounded Project, Production, Timeline, Model, Job and trace context and return structured findings/references. It does not gain canonical mutation authority.

### `plan`

Translate a bounded production goal plus findings into a structured Stage-16-compatible plan proposal. UV-owned Planner validation remains authoritative; the role cannot persist an invalid plan or bypass Planner checks.

### `media`

Reason over canonical media/reference identities plus Model/Capability metadata and return bounded media/model/capability recommendations or generation-task inputs. It does not call providers directly or hide remote/non-free execution.

### `critic`

Evaluate bounded plan/task/result evidence and return structured findings/severity/references. In this slice it must **not** autonomously repair or mutate canonical state; evaluation + dependency-aware repair is D-066 layer 5.

## Orchestration contract

At minimum define and prove:

- stable role identity and schema version;
- bounded canonical/context inputs;
- explicit allowed output type(s);
- explicit allowed downstream authority, if any;
- deterministic validation of role output before it can influence Planner/Tasks;
- role invocation/delegation identity linked to the parent goal/plan/task where applicable;
- bounded error/failure representation passed to the caller rather than hidden retries;
- no arbitrary shell, Python, filesystem, provider or permission expansion.

A role is a functional specialization inside the UV Agent Harness, not an independent application/runtime with its own project state.

## Required proof

Prove at least one foreground multi-role flow such as:

```text
existing modern Studio project
 -> explore returns bounded canonical findings
 -> plan consumes those findings and proposes 2+ dependent tasks
 -> UV Planner validates/persists the Plan and durable Tasks
 -> media contributes a bounded model/media decision to one planned generation action
 -> approved task executes through existing AgentHarness / Generation authority
 -> critic inspects the resulting bounded trace/canonical evidence
 -> role identities and canonical references remain inspectable
```

The exact proof may use fewer roles in one chain if separate focused tests cover every role contract, but no role may bypass Stage-16 Planner/Task/Skill validation or existing execution authorities.

## Negative proof

Prove at least:

- unknown role IDs fail closed;
- malformed/oversized role inputs or outputs fail closed;
- role results cannot introduce secret/path-bearing/non-portable state;
- `explore` and `critic` cannot mutate canonical state;
- `plan` cannot persist unknown actions, dependency cycles or invalid canonical prerequisites;
- `media` cannot call an arbitrary provider or bypass named Model/Capability/D-017 boundaries;
- a role cannot mint authorization or widen effects/permissions;
- failed role work produces bounded inspectable failure facts and does not silently unlock dependent executable work;
- restart/reopen preserves any durable plan/task/trace references created after role output is accepted, without making transient role scratch state canonical project truth.

## Product Truth boundary

This remains internal Agent infrastructure unless the slice deliberately adds a real user-visible Studio Agent surface. Do not claim autonomous-product readiness from internal role orchestration alone.

## Explicitly deferred

Not part of this slice:

1. background Agent workers / leases / heartbeats — D-066 layer 4;
2. automatic critic/evaluation + dependency-aware repair — layer 5;
3. human takeover/edit/resume — layer 6;
4. long-form autonomous production — layer 7;
5. unrelated D-068 desktop updater implementation;
6. a real InfinityEdit/Helios continuation provider/UI.

## Entry gate

Begin only from lifecycle-closed idle `main` after Stage 16 / PR #70 merge commit `bd258b7564f864c7f5fe636cb1336515f0dacce2` is recorded as `last_completed` and `development-context` passes on the closure head.
