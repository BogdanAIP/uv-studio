# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: jarvishub-agent-donor-architecture -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository is idle after merging and closing the architecture/documentation slice `jarvishub-agent-donor-architecture`.

- completed PR: #67;
- merge commit: `f43437b7716cc5454d49595a07b616b35e3f2324`;
- exact review head `7d19d7f036239bc53874b2d383a7f556a240c698` passed all five permanent CI jobs;
- the only review finding, about creative rerolls versus idempotent replay, was fixed before merge;
- next handoff: `studio-v2-model-registry-job-manager-generation` from `project-context/NEXT_TASK.md`.

There is no active feature branch or PR slice until that handoff is initialized from this idle `main`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-066** — JarvisHub is the reference architecture/method donor for the future UV Studio Agent Harness; UV keeps its own project/production/timeline/transaction authorities.
- **D-067** — Product Truth Contract and current-documentation consistency: user-visible readiness requires canonical backend/application behavior, frontend surface and user-outcome proof to agree.
- **D-068** — maintained desktop releases use one installation identity with visible in-place Update UI/Service and separate N-1 -> N upgrade evidence.
- **D-033** — canonical Timeline remains UV-owned; MLT remains derived.
- **D-017** — exact one-shot authorization remains the remote/non-free execution boundary.

## As-built Studio foundation

Stages 12 and 13 provide the current lower production spine:

1. typed Production Direction identity and bounded production storage;
2. `ProjectUnitOfWork` with prepared journal, rollback/recovery and durable project-level Undo/Redo;
3. strict shared `Scene`, `Shot`, `Take` and accepted-Take contracts in `production/semantics.json`;
4. micro-drama Story/Characters/Locations/continuity extensions in `production/micro_drama.json`;
5. one serialized `ProductionSemanticService` command boundary for shared semantic mutations;
6. HTTP semantic handlers over the same service;
7. shared Scene/Shot/Take reuse proven from the commercial direction;
8. transactional `accept_take` spanning production state, project-owned media provenance and canonical `timeline/main.json`;
9. project-level Undo/Redo of accepted-Take projection without splitting production and Timeline history;
10. rich micro-drama Production UI in the shared Studio page;
11. cross-platform browser proof using real media from visible direction selection through Scene/Shot/Take, continuity, acceptance, Timeline, Undo and Redo.

A Shot remains production meaning, not a Timeline Clip. Direction-specific extensions may reference shared production identities but must not fork common Scene/Shot/Take infrastructure.

## JarvisHub donor boundary

D-066 records JarvisHub (`LYL1015/JarvisHub`, pinned research commit `6c0f123119d9ffe1a6bae5140721f0b84ea3bbaa`) as the concrete reference for the autonomous layer UV Studio does not yet have.

Borrow/adapt later for the Agent Harness:

- persistent runtime / turn loop;
- Planner + durable Tasks;
- Skills;
- context pipeline, memory and compaction;
- functional subagents: explore / plan / media / critic;
- effects/policy metadata;
- inspectable trace;
- background execution through UV Jobs;
- evaluation and dependency-aware local repair.

Carry into the next implementation slice immediately:

- project-scoped Job/Attempt identity and durable provenance;
- retry-safe idempotency for infrastructure replay;
- a fresh idempotency key creates a deliberate new creative Attempt even when inputs match a prior attempt;
- provider-neutral `GenerationContract`;
- action/capability effects visibility for later Agent policy and trace.

JarvisHub Canvas/node/PostgreSQL/Hono application authority and a parallel Protocol Bridge/tool registry are explicitly out of scope. Project Store, production semantics, canonical Timeline, Studio/Application Commands, `ProjectUnitOfWork`, Capability Registry and D-017 remain UV-owned authorities.

## Product Truth contract

D-067 makes Product Truth a permanent forward verification rule rather than only a historical recovery concern.

For a user-visible capability, ready means:

```text
canonical command/backend behavior
 + required frontend surface
 + truthful progress/error/result state
 + end-to-end user-outcome proof
 = ready product feature
```

The target machine-readable Product Truth Contract points to the existing command/query, backend/API, frontend entry, relevant state/dependencies and E2E proof. It is verification metadata, not a second runtime feature registry.

Current project/context architecture documents are part of Product Truth and should be checked through narrow explicit markers/contracts rather than brittle semantic linting of arbitrary prose.

The next Model Registry/Job Manager/generation slice is the first required Product Truth consumer.

## Desktop update contract

D-068 defines the maintained Windows release behavior:

- one normal installed UV Studio identity rather than one stable side-by-side copy per version;
- Settings/About update UI with current version, check-for-updates, release notes, progress and controlled update/restart;
- GitHub Releases may be the first source through bounded machine-readable metadata;
- verify release artifact identity/digest/signature before installation;
- use an out-of-process replacement/updater mechanism with recovery/rollback behavior;
- keep application/runtime replacement separate from Project Store/user data;
- keep application version separate from project/domain schema versions;
- Stage-9 release proof must include both clean installation and N-1 -> N in-place upgrade with representative project/settings state.

The Update Service/UI is accepted architecture but is not implemented yet.

## Compatibility rule

Recipe/Product Orchestrator/numbered Stage routes remain compatibility code. New Studio modules must not depend on them merely to access neutral project, production, model, job or capability services.

Legacy/compatibility projects cannot execute modern direction production commands until they have valid modern Production Direction identity.

## Known intentional limits

- Replacing an already accepted Take with another candidate remains a future semantic operation; current callers Undo acceptance first.
- Model Registry, project-scoped Job Manager, `GenerationContract` and the full Agent Harness are not implemented yet.
- Product Truth Contract registry/validators beyond existing lifecycle/user-outcome checks are not implemented yet.
- Desktop Update Service/UI and packaged N-1 -> N upgrade automation are not implemented yet.
- JarvisHub is a pinned architecture/method donor, not a vendored dependency.

## Next handoff

`studio-v2-model-registry-job-manager-generation` must add the backend-owned user-visible Model Registry, project-scoped retry-safe Job Manager and first named AI generation path through the same shared Shot/Take command and transaction boundaries.

Generated output must become project-owned media with explicit model/provider/adapter/GenerationContract provenance before it becomes a Take candidate. Same idempotency key + matching digest must not duplicate expensive execution; same key + different digest must fail closed; a fresh key must allow an intentional creative reroll. Accepting a generated Take remains separate semantic history, so Undo acceptance must not erase Job/Attempt/provenance.

Under D-067 the slice must also add the first machine-readable Product Truth Contract and prove named model selection, Job/progress/failure/result state and Take-candidate materialization through the real Studio UI/browser E2E.
