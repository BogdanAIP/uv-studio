# UV Studio — Current Architecture

**Status:** CURRENT AUTHORITY  
**Date:** 2026-09-04  
**Product composition:** D-064  
**Shared production semantics:** D-065  
**Agent Harness factoring:** D-066  
**Product Truth:** D-067  
**Desktop updates:** D-068  
**Stateful generation lineage:** D-069  
**Product-first sequencing gate:** D-070  
**Editor foundation:** D-033

This document describes the current UV Studio target and the concrete implementation boundary. Historical Recipe Registry, Product Orchestrator and numbered Stage workspaces remain compatibility/migration code unless a later accepted decision explicitly promotes them.

## Product definition

UV Studio is a **local-first AI production studio with multiple Production Directions over one shared project, production, editor and execution core**.

Production Directions organize work; they do not create separate project stores, timelines, editor engines, model registries or private Scene/Shot/Take systems.

Initial directions remain:

- `micro_drama`;
- `commercial`;
- `music_video`;
- `narrated_video`;
- `dub_battle`;
- `free_project`.

## Canonical authority stack

```text
Project Store
 -> Production Direction
 -> Shared Production Semantic Core
      Scene / Shot / Take / Accepted Take
 -> Direction-specific documents
 -> Shared Studio Core
      Media / Preview / Inspector / canonical Timeline
 -> Studio / Application Commands
 -> shared cross-runtime project mutation fence
 -> ProjectUnitOfWork / durable Undo-Redo
 -> Model Registry
 -> Generation Job Manager / GenerationContract
 -> Agent Harness
      Context / Catalog / Policy / Trace              [Stage 15 merged]
      Planner / durable Tasks / Skills                [Stage 16 merged]
      functional Subagents                            [Stage 17 merged]
      bounded background Agent execution              [Stage 18 merged, PR #75]
      evaluate / dependency-aware repair              [deferred by D-070 product gate]
      takeover / edit / resume                        [deferred by D-070 product gate]
      long-form autonomy                              [deferred by D-070 product gate]
 -> Capability Registry / D-017 / adapters
 -> MLT / FFmpeg / MCP / local / optional remote execution
```

Cross-cutting verification:

```text
current docs <-> Product Truth records <-> backend/API <-> frontend <-> E2E
Stage-16/17 guarantees <-> curated adversarial/mutation assurance [PR #73 merged]
Stage-18 leases/fencing/recovery <-> exact-head CI + focused review [PR #75 merged]
D-070 product sequencing <-> accepted legacy caller/migration inventory [PR #77 merged] + micro_drama golden vertical [separate gate still open]
```

## Canonical authorities

- **Project Store** owns portable project state and project-owned references.
- **Production Direction identity** selects production organization/policy, not an execution engine.
- **Shared Production Semantic Core** owns reusable Scene/Shot/Take/accepted-material identities.
- **Direction Extensions** own genuinely direction-specific data while referencing shared identities.
- **Canonical Timeline** is UV-owned assembly state; MLT remains derived behind the D-033 adapter.
- **Studio/Application Commands** are the semantic mutation boundary for GUI, Agent, scripts and MCP.
- **Shared project mutation fence** is the existing re-entrant cross-process `ProjectTaskRecordStore.project_lock`; Production/Timeline semantic commands, ProjectUnitOfWork and bounded Generation reservation reuse it instead of creating an Agent-only lock authority.
- **ProjectUnitOfWork** owns canonical multi-document mutations and durable Undo/Redo.
- **Model Registry** owns meaningful named-model identity above provider/adapter transport.
- **Generation Job Manager** owns project-scoped generation lifecycle, idempotency, attempts and execution provenance.
- **Agent Harness** orchestrates work over the same commands/models/jobs/capabilities; it never owns a second project graph or private mutation path.
- **Capability Registry / D-017 / adapters** own execution availability, effects, authorization and transport.
- **Product Truth Contracts** are verification metadata, not runtime product state.
- **D-070 sequencing** now has an accepted architecture-compression inventory; bounded retirement follows that map, while further Agent-autonomy layers after Stage 18 remain deferred until the separate user-visible golden vertical is proven.
- **Update Service** remains the accepted future desktop release authority for in-place updates; it is not implemented by the current Agent slices.

## Production semantics versus Timeline

A Shot is not a Timeline Clip.

```text
Shot
 -> intent / references / continuity
 -> imported or generated candidate Takes
 -> accepted Take
 -> project-owned media
 -> Timeline projection / assembly clips
```

Stage 13 proved the shared Scene -> Shot -> Take -> accepted Take -> canonical Timeline path with ProjectUnitOfWork, Undo/Redo and reuse outside micro-drama.

## Named generation — Stage 14 merged foundation

The implemented generation path is:

```text
Shot
 -> named Model
 -> GenerationContract
 -> idempotent project Job / Attempt
 -> Capability / Provider / Adapter execution
 -> project-owned generated artifact + provenance
 -> Take candidate
 -> explicit acceptance
 -> canonical Timeline
```

Important invariants:

- same idempotency key + same normalized request digest reuses the Job;
- same key + different digest fails closed;
- a fresh key permits intentional creative reroll;
- same-key lookup, D-017 consumption and durable Job reservation are one shared cross-runtime project critical section for all `GenerationService.submit` callers;
- `GenerationJobManager.create_or_reuse` uses the same shared fence for direct reservation;
- long provider execution is outside the project mutation fence and remains owned by the Job/Attempt lifecycle;
- restart never silently replays abandoned external work;
- D-017 remains separate from idempotency and is required for every fresh remote/non-free execution that needs consent;
- provider prompt text and provider-private cache/session/latent state are not canonical project truth;
- D-069 continuation uses durable project media lineage, while provider-private continuation state remains disposable.

A real InfinityEdit/Helios adapter and visible Continue/Edit surface are not currently claimed.

## Agent Harness layer 1 — Stage 15 merged

PR #69 implemented the first D-066 layer.

`AgentContextBuilder` creates a deterministic bounded observation from canonical Project / Production / Timeline / Model / Job authorities. It is an Agent observation contract, **not an exact canonical concurrency/version token**. `AgentActionCatalog` exposes only existing UV command authorities. Policy projects existing capability/D-017 facts but cannot self-authorize. `AgentTraceStore` persists bounded append-only project-scoped execution evidence under the existing `tasks/` authority.

`AgentHarness` delegates canonical mutation to the same Production/Timeline/Generation services used by other callers. There is no generic project file write, shell, Python or arbitrary provider command.

## Agent Harness layer 2 — Stage 16 merged

PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2` after exact-head CI and review.

The merged layer adds:

```text
bounded goal
 -> Stage-15 Context + Action Catalog + Policy
 -> UV-validated structured Planner proposal
 -> append-only AgentPlanRecord
 -> durable dependency-aware AgentTaskRecord state
 -> bounded Skill expansion
 -> foreground AgentTaskCoordinator
 -> AgentHarness
 -> existing UV application authorities
 -> Stage-15 trace + canonical result references
```

Plans and task records live under the existing project `tasks/` root through `ProjectTaskRecordStore`; they are orchestration state, not Generation Jobs, production truth or Undo history.

Current task state machine:

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

Dependencies unlock only after success. A failure keeps dependants blocked and does not falsely mark them successful. Cross-runtime CAS/locking and restart reconciliation prevent stale task-state overwrites and silent replay.

Skills remain bounded procedures over approved Agent actions and inherit their effects/authority envelope. They do not gain shell, Python, arbitrary filesystem/provider or D-017 bypass rights.

Stage 16 recovery binds execution-time context/policy/correlation before canonical or cost-bearing dispatch. Production/Timeline recovery reuses correlated ProjectUnitOfWork evidence; generation recovery requires exact Job/idempotency/request/mapping evidence and never silently resubmits.

## Agent Harness layer 3 — Stage 17 merged

PR #71 merged as `c3ca3c33f89f67fad97081f889934669e34befa5` and was lifecycle-closed through PR #72.

The merged implementation provides bounded foreground functional roles:

- `explore` for advisory findings over explicit canonical context;
- `plan` for structured proposals that still require the existing Stage-16 Planner;
- `media` for the bounded media/generation/Take/Timeline action subset;
- `critic` for read-only Plan/Task/linked-trace evidence with no automatic repair authority.

Role output is bound to exact bounded context, assigned typed content-addressed `agent_delegate_<role>_<digest>` provenance, revalidated before persistence and carried through the existing Plan/Task/Trace path. Stage 17 does not add a second task graph, permission system, provider executor or mutation authority.

## Stage-16/17 adversarial assurance — merged verification baseline

PR #73 merged as `d1413e5753c24f207faf5a20828f891c14f53aa0`. It changes verification infrastructure only.

The curated mutation runner copies the full package into an isolated overlay, verifies exact source/import provenance, first proves the detector against baseline bytes, then requires selected mutants to be killed in fresh processes. The initial guarantee set protects context/provenance/namespace/shared-authority properties on Ubuntu and Windows.

This is a curated assurance baseline, not exhaustive automatic mutation testing.

## Agent Harness layer 4 — Stage 18 merged

PR #75 (`stage-18/agent-background-execution`) merged as `c5051b975a1ba8e747f453dd0a485cac1e308ba7`. Stage 18 adds **bounded background execution** while preserving the merged Stage-15/16/17 authorities.

The background execution model is deliberately narrow:

```text
existing durable Agent Task
 -> short worker claim
 -> durable lease/fencing record beside that task
 -> RUNNING task + append-only execution evidence
 -> execute outside the long Agent task lock
 -> shared project mutation fence
 -> exact canonical commit / Generation reservation
 -> short finalize/release
 -> existing trace / ProjectUnitOfWork / Generation Job recovery
```

### Lease authority

Background leases live under the existing project `tasks/` authority and use the same cross-runtime task-record lock and compare-and-swap boundary. They are not a scheduler and do not define another task state machine.

A lease is bound to:

- exact project / Plan / Task / task-record identity;
- worker ID and bounded generation;
- claim-time bounded Agent observation digest;
- **exact canonical-state digest** over `project.json`, `production/**/*.json` and `timeline/**/*.json` bytes;
- expected input digest;
- target Shot identity when applicable;
- frozen policy digest;
- deterministic recovery correlation;
- bounded acquisition/heartbeat/expiry history.

The raw bearer lease token is **not portable project state**. Only its digest is durable. The raw token exists only in the ephemeral `AgentBackgroundClaim` and is excluded from `repr`; durable records reject any `lease_token` field.

### Frozen policy / evidence binding

The claim-time policy is persisted once through the existing Stage-16 append-only execution-evidence authority. Dispatch, heartbeat, canonical commit and finalization reload and compare that durable evidence. A caller cannot substitute a different `AgentPolicyProjection` or recovery correlation through the claim object.

### Shared cross-runtime commit fence

The first focused Codex review of exact head `e4e632322e9a28244f26b02bef3580c67feceace` found three valid P1 races: Production/Timeline cross-process TOCTOU, non-atomic Generation same-key reservation/D-017 consumption, and use of incomplete bounded Agent context as a Timeline freshness token.

The review fix reuses the already-existing `ProjectTaskRecordStore.project_lock` as the single shared project critical section:

- `ProductionSemanticService` holds it across complete semantic read -> validate/build -> ProjectUnitOfWork commit;
- `TimelineCommandService` holds it across complete Timeline read -> validate/build -> ProjectUnitOfWork commit;
- `ProjectUnitOfWork` holds the same fence for history recovery, snapshot derivation, prepared write and commit/undo/redo;
- `GenerationService.submit` holds it across prepare -> same-key lookup -> D-017 consumption -> Job reservation;
- `GenerationJobManager.create_or_reuse` uses the same fence for direct same-key reservation;
- Agent `_commit_guard` reuses the same fence while revalidating exact lease/task/evidence and canonical freshness before the canonical effect.

The lock is re-entrant across these nested authorities. It protects bounded project mutation/reservation sections only; external provider execution is deliberately outside it.

### Exact freshness versus Agent observation

`AgentContextBuilder.digest` remains a bounded observation digest and can omit Timeline details by design. Stage 18 therefore does **not** use it as the sole exact freshness token.

At claim time Stage 18 separately hashes the exact mutation-relevant canonical JSON bytes. At dispatch and canonical commit it requires that digest to match while holding the shared project fence. A clip timing/source/reference edit that is invisible to the bounded Agent observation still invalidates the exact canonical digest and fails closed.

### Recovery and replay boundary

A live leased RUNNING task is not treated as abandoned by ordinary Stage-16 reopen reconciliation. After lease expiry, Stage 18 reuses the existing exact trace/ProjectUnitOfWork/Generation Job recovery contracts.

- crash before canonical commit: no false success and no hidden redispatch;
- crash after canonical commit but before Agent success bookkeeping: recover from committed canonical evidence without replay;
- crash after lease persistence but before READY -> RUNNING: reclaim only after expiry, consuming a bounded lease generation;
- explicit cancellation continues to use the existing Stage-16 cancellation semantics;
- failed dependencies remain blocked according to the existing Stage-16 state machine.

`AgentBackgroundWorker.run_once` and `run_until_blocked` are bounded caller-driven facades. Stage 18 does **not** add autonomous polling or a second scheduler.

### Current proof boundary

The Stage-18 suites cover worker exclusivity, lease expiry/reclaim, heartbeat extension, token non-persistence, frozen-policy/correlation tamper rejection, cancellation/dependency behavior, crash recovery without replay, exact Generation Job reuse/reopen and Stage-17 delegation provenance.

Focused review regressions additionally prove:

- independent Production runtimes serialize full read/modify/commit and preserve both changes;
- independent Timeline runtimes serialize full read/modify/commit and preserve both changes;
- a real `spawn` multiprocessing test exercises the OS-level project fence between independent Python processes on the permanent Ubuntu/Windows unit jobs;
- concurrent same-key Generation submissions create/reuse one durable Job and consume authorization once;
- a Timeline timing edit deliberately leaves the bounded Agent context digest unchanged while the separate exact canonical digest rejects the stale background claim;
- foreground coordinators cannot replace installed background fences;
- direct Production/Timeline stores and every freshness-tracked JSON writer under `production/` or `timeline/` share the project fence;
- concurrent background-coordinator construction reserves harness ownership atomically.

All concrete PR #75 review findings were addressed before merge. Final PR head `4c80bc96512e5ba34b0c3ed973c76c1c7a029568` passed all five permanent CI jobs before the merge to `c5051b975a1ba8e747f453dd0a485cac1e308ba7`.

Stage 18 remains internal infrastructure. It does not claim a visible autonomous Agent product.

## D-070 product-first handoff before further D-066 autonomy

Layer 4 is merged through PR #75 and is the accepted background-execution baseline. `architecture-compression-inventory` merged through PR #77 as `c6831a36eb88289947eed1da65609654a2353524`; `donor-ui-retirement` merged through PR #82 as `c1eb609ec1e4c9db082eaa8338ac7f1e4938da11`; `actions-hardening` merged through PR #86 as `975a64855a739398139c90a094bdde9435542299`; `project-identity-v2-compat-reader` merged through PR #89 and was lifecycle-closed through PR #90; `recipe-entrypoint-retirement` merged through PR #91 as `050780d013276c3d3de9672244ad54da759f1ed3` and was lifecycle-closed through PR #92 as `af9ff888145661381caaacdec78244637058bce2`; `execution-plan-retirement` merged through PR #93 as `c8915e2aede2125136080156513ffc3bd4727038` and was lifecycle-closed through PR #94, producing clean `main` `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`. Draft PR #95 is the first bounded legacy direction/tool migration slice and targets only the duplicate Music Product Workflow mutation/action envelope.

The accepted behavior-preserving inventory establishes exact callers, canonical replacements, durable compatibility requirements and deletion gates for Recipe Registry, `uv_studio/orchestration/**`, legacy Product Orchestrator, Stage 6/8 product-composition surfaces, server compatibility routes, schema-v1 `recipe_id`, donor frontend/client/restoration paths and their runtime dependencies. The recipe-derived `/execution-plan` client/API/projection is now retired. On PR #95, Music Product Workflow remains as a temporary read-only readiness/workspace projection, while the five duplicate Music mutation actions are removed and the specialized Music client facades move their supported mutations onto already-existing direct Music Map/Direction/Assembly/Review APIs and `video.render_music_video` capability execution. Browser CI #4858 supplied positive evidence for the hidden client seam; the fix does not restore or replace Product Orchestrator mutation authority.

Further Agent autonomy resumes only after both D-070 gates are satisfied:

1. **Architecture compression gate — satisfied.** Legacy/modern overlap now has an accepted caller/migration map, superseded composition gains no new callers, and duplicate authorities have bounded retirement slices. Executing the scheduled retirement/extraction slices remains later migration work rather than a prerequisite for this gate.
2. **Golden vertical gate — open.** GUI must prove `New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`, with Agent using the same Studio/Application Commands, Generation Job authority and Capability/D-017 boundaries when invoked.

When Agent-autonomy work resumes, D-066 ordering is preserved:

1. **Layer 5 — critic/evaluation + dependency-aware local repair**;
2. **Layer 6 — human takeover/edit/resume**;
3. **Layer 7 — long-form autonomous production** only after all prior boundaries are proven.

D-070 changes sequencing, not D-066 ownership. Do not collapse the deferred layers or jump directly to long-form autonomy.

## Capability/effects boundary

`CapabilityEffects` / resolved offer effects remain the single effects source for Agent policy, Skills and functional subagent routing. Relevant facts include project/Timeline mutation, media generation, destructive behavior, long-running behavior, reversibility and cost bearing.

No parallel Protocol Bridge/tool registry/permission authority is introduced.

## Product Truth — D-067

A user-visible feature is complete only when canonical domain/API/frontend/current-doc/evidence references agree.

Machine-readable Product Truth records live under `docs/architecture/product-truth/`. The existing named-generation record proves the Stage-14 visible generation path. Agent layers 15–18 are merged internal infrastructure; PR #73 is merged internal verification infrastructure. None claim a visible autonomous Agent product without a separate Studio surface and corresponding Product Truth/browser evidence.

## Desktop updates — D-068

The accepted desktop target remains one maintained installation with visible check/update/restart flow, verified artifacts and N-1 -> N upgrade proof. This remains separate release/productization work and must not be mixed into Agent orchestration.

## Direction versus tool

A Direction answers **what production is being organized**. A tool/action answers **what operation occurs inside that project**.

Contextual operations such as targeted edit, dubbing/translation, slideshow, visualizer, talking character, lip-sync, image/video/audio generation and continuation remain tools/capabilities even when a direction gives them prominent UI.

## Rules for new work

1. Do not add RecipeDefinition as new v2 product identity.
2. Do not create a separate engine/workspace per Production Direction.
3. Do not create a second canonical Project Store or Timeline.
4. Do not duplicate shared Scene/Shot/Take semantics per direction.
5. GUI, Agent, scripts and MCP converge on the same application/domain commands.
6. Do not give the Agent, a Skill, subagent or background worker a private project-write path.
7. Agent context/plan/task/trace/role/lease state is orchestration/inspection state over canonical identities, not canonical production state.
8. Generation Job/Attempt history remains separate from Agent Task/lease orchestration state.
9. Remote/non-free execution remains explicit and D-017-authorized where required.
10. Provider prompts, secrets, raw bearer lease tokens, reusable authorization and provider-private continuation caches never become portable Project/Agent state.
11. Background execution must fail closed on lost lease authority, stale policy/evidence or stale exact canonical state.
12. Canonical Production/Timeline read-modify-commit and Generation reservation must reuse the shared cross-runtime project fence for every caller.
13. Current docs must distinguish merged/as-built state from active/future state.
14. Do not claim autonomous product readiness from internal Agent infrastructure alone.
15. Do not add new modern callers to Recipe Registry, Product Orchestrator, retired `/execution-plan`, Stage 6/8 product composition or another path classified as superseded by D-070 without an accepted decision reversing that status.

## Compatibility layer

Still present as compatibility/migration code unless separately promoted:

- schema-v1 `recipe_id`;
- Recipe Registry;
- Product Orchestrator read projection and remaining non-Music action responsibilities;
- Stage 6/8 workspace UI;
- legacy `/projects/[projectId]` domain panels and VideoClaw backend compatibility still needed by supported callers;
- targeted-edit/dubbing/continuity logic awaiting extraction into modern direction/tool surfaces;
- Music Product Workflow read state while the legacy Music page still consumes readiness/prerequisites/workspace projection.

The recipe-derived `/execution-plan` projection is retired through accepted PR #93 and closure PR #94. PR #95 is a bounded candidate that removes only the duplicate Music mutation/action envelope and moves the two specialized Music client facades onto established direct domain/capability endpoints; it deliberately preserves Music read projection, internal Recipe Registry, Stage8 and the legacy route. The D-070 `architecture-compression-inventory` is accepted and merged through PR #77, its architecture-compression gate is satisfied, and the separate `micro_drama` golden-vertical gate remains open until proven.

Compatibility code may remain readable/editable while new architecture continues on the authorities defined above, but superseded product-composition paths must not gain new modern callers while the accepted D-070 retirement map is being executed.
