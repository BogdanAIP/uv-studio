# Next Task

<!-- uv-next-slice: studio-v2-agent-background-execution -->

## Goal

Implement **D-066 Agent Harness layer 4: bounded background Agent execution** only after the Stage-16/17 adversarial-assurance slice is reviewed, merged and lifecycle-closed.

The target slice is `studio-v2-agent-background-execution`.

## Required direction

- reuse the existing Stage-14 Job Manager and Stage-16 Plan/Task execution authorities rather than introducing a second scheduler or task store;
- add explicit worker ownership, leases/heartbeats and restart-safe recovery for background Agent work;
- preserve exact Project Store, Production/Timeline/Generation, Capability/D-017 and Agent trace authorities;
- keep canonical effects idempotent or reconcilable so process loss cannot replay a proven committed effect;
- make ambiguous delivery/result states explicit and re-observe/reconcile before retry;
- use bounded worker/task budgets and fail closed on expired ownership or stale execution context;
- carry Stage-17 delegation provenance through background execution without turning provenance into authorization;
- expose truthful user-visible state only when a real product surface is added; background capability alone is not autonomous-product readiness.

## Required proof

At minimum prove:

- one background task completes through the existing AgentHarness/application authority and survives reopen;
- worker lease ownership prevents two workers from committing the same task concurrently;
- expired/stolen/stale worker ownership cannot authorize a canonical mutation;
- crash after canonical commit but before success trace/job bookkeeping does not replay the effect;
- crash before canonical commit leaves no false success evidence;
- restart/recovery preserves Plan/Task/delegation provenance and exact Job/Attempt history;
- cancellation and dependency failure prevent downstream background work from executing;
- bounded failure/retry facts remain inspectable and do not silently broaden permissions or provider access.

## Explicitly deferred

- automatic critic/evaluation + dependency-aware repair — D-066 layer 5;
- human takeover/edit/resume — layer 6;
- long-form autonomous production — layer 7;
- unrelated D-068 desktop updater implementation;
- provider-private background schedulers as canonical UV state.

## Entry gate

Begin only from lifecycle-closed `main` after `agent-stage17-adversarial-assurance` is accepted. Its curated guarantee suite must remain green so background concurrency is added on top of a proven Stage-16/17 authority/provenance baseline rather than weakening it implicitly.
