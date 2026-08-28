# Next Task

<!-- uv-next-slice: studio-v2-agent-evaluate-repair -->

## Goal

Implement **D-066 Agent Harness layer 5: bounded evaluation and dependency-aware local repair** only after `studio-v2-agent-background-execution` is reviewed, merged and lifecycle-closed.

## Required direction

- reuse the merged Agent Plan/Task/Trace, Stage-17 critic role, background worker lease/recovery and existing application authorities rather than introducing a second repair graph;
- make evaluation evidence explicit, bounded and inspectable;
- allow repair only for a failed/unsatisfied local dependency scope that can be represented by existing approved Agent actions/Skills;
- keep every repair proposal subject to the same Planner, policy/effects, D-017, context freshness and canonical command boundaries as ordinary Agent work;
- bind repair provenance to the exact failed task/evaluation evidence without treating provenance as authorization;
- prevent unbounded self-repair loops through explicit attempt and strategy budgets;
- preserve human-visible failure state when repair is unavailable, unsafe, exhausted or ambiguous;
- do not claim long-form autonomous production readiness from evaluation/repair infrastructure alone.

## Required proof

At minimum prove:

- critic/evaluation consumes exact durable Plan/Task/Trace evidence rather than reconstructed success claims;
- one bounded dependency-local failure can produce a validated repair proposal and resume only the affected downstream path;
- a repair cannot broaden permissions, model/provider authority or canonical write scope;
- repeated ineffective repair attempts stop at explicit budgets with inspectable structured reasons;
- stale evaluation/context or changed canonical state invalidates a pending repair before mutation;
- successful repair preserves original failure/evaluation/repair provenance and does not erase prior attempts;
- restart/reopen preserves repair state and cannot duplicate already committed effects;
- unrelated tasks/branches remain untouched by a local repair.

## Explicitly deferred

- human takeover/edit/resume — D-066 layer 6;
- long-form autonomous production — layer 7;
- unrelated desktop updater work;
- hidden provider-native repair loops as canonical UV state.

## Entry gate

Begin only from lifecycle-closed `main` after Stage 18 background execution is accepted with worker lease/fencing/recovery guarantees green on both Ubuntu and Windows.
