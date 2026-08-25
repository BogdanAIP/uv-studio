# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: jarvishub-agent-donor-architecture -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository has an active documentation/architecture slice in review from the Stage-13-closed `main` state:

- active slice `jarvishub-agent-donor-architecture`;
- branch `chore/jarvishub-agent-donor-architecture`;
- base `main` at `e9b249124c48203c71d386a5fc997cbbfe61e3e6`;
- PR #67 is the review integration PR;
- the implementation handoff remains `studio-v2-model-registry-job-manager-generation` from `project-context/NEXT_TASK.md`.

This slice changes durable architecture/development memory only; it does not add product runtime code.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-066** — JarvisHub is the reference architecture/method donor for the future UV Studio Agent Harness while UV keeps its own project/production/timeline/transaction authorities.
- **D-067** — Product Truth Contract and current-documentation consistency: user-visible readiness requires backend/application behavior, frontend surface and user-outcome proof to agree; current docs must agree on machine-checkable repository facts.
- **D-068** — maintained desktop releases use one installation identity with visible in-place Update UI/Service and separate N-1 -> N upgrade evidence.
- **D-033** — canonical Timeline remains UV-owned; MLT remains derived.

A Shot is production meaning, not a Timeline Clip. Direction-specific data may reference shared production identities but must not fork Scene/Shot/Take infrastructure. The future Agent may reason over these identities but must mutate them only through shared Studio/Application Commands.

## Stage 13 completed

Stage 13 establishes the first complete rich-direction vertical path:

1. strict shared `Scene`, `Shot`, `Take` and accepted-take contracts in `production/semantics.json`;
2. micro-drama Story, Characters, Locations and per-scene continuity/canon extensions in `production/micro_drama.json`;
3. one serialized `ProductionSemanticService` command boundary for shared semantic mutations with shared Project Store locking across read/modify/commit;
4. explicit HTTP semantic command handlers over the same service rather than a direction-private pipeline;
5. cross-direction reuse of shared Scene/Shot/Take contracts proven from the commercial direction;
6. transactional `accept_take` spanning accepted production state, project-owned media provenance and canonical `timeline/main.json` through Stage-12 `ProjectUnitOfWork`;
7. exact project-level Undo/Redo of accepted Take projection without splitting production and Timeline state;
8. support for multiple Shot/Take/Timeline provenance bindings when one project media reference is reused;
9. rich micro-drama Production UI inside the shared Studio page, while other directions keep the common Studio Core without premature direction-specific UI;
10. shared project-change synchronization between Production, Timeline and Undo/Redo controls;
11. core/API coverage for Scene -> Shot -> multiple Takes -> micro-drama context -> accepted Take -> canonical Timeline, concurrency and cross-direction reuse;
12. cross-platform Playwright proof from visible direction selection and real-media import through Scene/Shot/Take, Story/Characters/Locations/continuity, acceptance, Timeline, Undo and Redo.

Final review head `7bf776e4a58cade4706e6a5256e5fc2dcc2f91d0` passed all five permanent CI jobs. PR #66 merged as `16409d2d01ce4ca2be3eab61a02a06655650f444`, and `e9b249124c48203c71d386a5fc997cbbfe61e3e6` closed the lifecycle back to idle before this documentation slice began.

## JarvisHub donor decision

D-066 records JarvisHub (`LYL1015/JarvisHub`, pinned research commit `6c0f123119d9ffe1a6bae5140721f0b84ea3bbaa`) as the concrete reference for the autonomous layer UV Studio does not yet have.

Borrow/adapt for the future Agent Harness:

- persistent agent runtime / turn loop;
- Planner + durable Tasks;
- Skills;
- context pipeline, memory and compaction;
- functional subagents: explore / plan / media / critic;
- effects/policy metadata;
- inspectable trace;
- background execution through UV Jobs;
- evaluation and dependency-aware local repair.

Carry into the **next** implementation slice immediately:

- retry-safe idempotency for long-running/cost-bearing/external generation;
- durable Job/Attempt identity and provenance;
- provider-neutral `GenerationContract` for fixed constraints, editable variables, forbidden changes and approved references/keyframes;
- action/capability effects visibility for later Agent policy and trace.

Do not import JarvisHub Canvas/node/PostgreSQL/Hono application authority or create a parallel tool/protocol layer. Project Store, shared production semantics, canonical Timeline, Studio/Application Commands, ProjectUnitOfWork, Capability Registry and D-017 remain UV-owned authorities.

## Product Truth decision

D-067 turns the earlier Product Truth recovery lesson into a permanent forward contract.

A future user-visible feature is complete only when:

```text
canonical command/backend behavior
 + required frontend surface
 + user-visible state/progress/errors
 + E2E user-outcome proof
 = ready product feature
```

The target machine-readable Product Truth Contract binds stable feature identity to command/query, backend/API, frontend entry, relevant canonical state/dependencies and E2E proof. Internal infrastructure can intentionally lack UI, but it must be explicitly non-user-visible/not-ready rather than counted as completed product functionality.

Current documentation is part of Product Truth. CI should progressively validate narrow explicit facts across `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, current architecture/decision indexes and Product Truth Contract references. The design explicitly avoids brittle natural-language semantic linting.

The next Model Registry/Job Manager/generation slice is the first required consumer: named-model generation must land with truthful Studio UI states and browser E2E, not backend contracts alone.

## Desktop update decision

D-068 defines the future maintained Windows update behavior:

- one normal installed UV Studio identity rather than one stable side-by-side copy per version;
- Settings/About update UI with current version, check-for-updates, release notes, progress and controlled update/restart;
- GitHub Releases acceptable as the first source through bounded machine-readable metadata;
- verified artifact identity/digest/signature before installation;
- out-of-process replacement with recovery/rollback behavior;
- application/runtime replacement kept separate from Project Store/user data;
- application version kept separate from project/domain schema versions;
- Stage-9 release proof must include both clean installation and N-1 -> N in-place upgrade with representative project/settings state.

This is accepted target architecture only; the Update Service/UI is not implemented in this documentation slice.

## Compatibility rule

Recipe/Product Orchestrator/Stage routes remain compatibility code. New Studio modules must not depend on them merely to access neutral project or production services.

Legacy/compatibility projects cannot execute modern direction production commands until they have valid modern Production Direction identity.

Stage 13 and D-066/D-067/D-068 add no RecipeDefinition, Product-Orchestrator graph, numbered Stage workspace, direction-private editor engine, second timeline, provider-specific production identity, JarvisHub Canvas-as-source-of-truth or parallel application update authority.

## Known intentional limits

- Replacing an already accepted Take with another candidate remains a future semantic operation. Current callers Undo the acceptance before choosing another Take rather than silently rewriting acceptance history.
- The Model Registry, project-scoped Job Manager, GenerationContract and full Agent Harness are not implemented yet.
- Product Truth Contract registry/validators beyond the existing lifecycle/user-outcome checks are not implemented yet.
- Desktop Update Service/UI and packaged N-1 -> N upgrade automation are not implemented yet.
- JarvisHub is currently a pinned architecture/method donor, not a vendored dependency.

## Next handoff

`studio-v2-model-registry-job-manager-generation` should add the backend-owned user-visible Model Registry, project-scoped retry-safe Job Manager and first named AI generation path through the same shared Shot/Take application-command and transaction boundaries.

Generated output must become project-owned media with explicit model/provider/adapter/GenerationContract provenance before it can become a Take candidate. Equivalent replay must not duplicate expensive execution. Accepting a generated Take remains separate semantic history, so Undo of acceptance must not corrupt or erase the underlying Job/Attempt/provenance record.

Under D-067 that slice must also add the first machine-readable Product Truth Contract and prove named model selection, Job/progress/failure/result state and Take-candidate materialization through the real Studio UI/browser E2E.

D-068 remains a later Stage-9 desktop-productization obligation and must be applied when packaging/release work resumes.
