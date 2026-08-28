# UV Studio — Current Architecture

**Status:** CURRENT AUTHORITY  
**Date:** 2026-08-28  
**Product composition:** D-064  
**Shared production semantics:** D-065  
**Agent Harness factoring:** D-066  
**Product Truth:** D-067  
**Desktop updates:** D-068  
**Stateful generation lineage:** D-069  
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
 -> ProjectUnitOfWork / durable Undo-Redo
 -> Model Registry
 -> Generation Job Manager / GenerationContract
 -> Agent Harness
      Context / Catalog / Policy / Trace              [Stage 15 merged]
      Planner / durable Tasks / Skills                [Stage 16 merged]
      functional Subagents                            [Stage 17 merged]
      bounded background Agent execution              [Stage 18 active draft, PR #75]
      evaluate / dependency-aware repair              [next layer 5]
      takeover / edit / resume                        [later layer 6]
      long-form autonomy                              [later layer 7]
 -> Capability Registry / D-017 / adapters
 -> MLT / FFmpeg / MCP / local / optional remote execution
```

Cross-cutting verification:

```text
current docs <-> Product Truth records <-> backend/API <-> frontend <-> E2E
Stage-16/17 guarantees <-> curated adversarial/mutation assurance [PR #73 merged]
Stage-18 leases/fencing/recovery <-> exact-head CI + focused review [PR #75 draft]
```

## Canonical authorities

- **Project Store** owns portable project state and project-owned references.
- **Production Direction identity** selects production organization/policy, not an execution engine.
- **Shared Production Semantic Core** owns reusable Scene/Shot/Take/accepted-material identities.
- **Direction Extensions** own genuinely direction-specific data while referencing shared identities.
- **Canonical Timeline** is UV-owned assembly state; MLT remains derived behind the D-033 adapter.
- **Studio/Application Commands** are the semantic mutation boundary for GUI, Agent, scripts and MCP.
- **ProjectUnitOfWork** owns canonical multi-document mutations and durable Undo/Redo.
- **Model Registry** owns meaningful named-model identity above provider/adapter transport.
- **Generation Job Manager** owns project-scoped generation lifecycle, idempotency, attempts and execution provenance.
- **Agent Harness** orchestrates work over the same commands/models/jobs/capabilities; it never owns a second project graph or private mutation path.
- **Capability Registry / D-017 / adapters** own execution availability, effects, authorization and transport.
- **Product Truth Contracts** are verification metadata, not runtime product state.
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
- restart never silently replays abandoned external work;
- D-017 remains separate from idempotency and is required for every fresh remote/non-free execution that needs consent;
- provider prompt text and provider-private cache/session/latent state are not canonical project truth;
- D-069 continuation uses durable project media lineage, while provider-private continuation state remains disposable.

A real InfinityEdit/Helios adapter and visible Continue/Edit surface are not currently claimed.

## Agent Harness layer 1 — Stage 15 merged

PR #69 implemented the first D-066 layer.

`AgentContextBuilder` creates a deterministic bounded observation from canonical Project / Production / Timeline / Model / Job authorities. `AgentActionCatalog` exposes only existing UV command authorities. Policy projects existing capability/D-017 facts but cannot self-authorize. `AgentTraceStore` persists bounded append-only project-scoped execution evidence under the existing `tasks/` authority.

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

## Agent Harness layer 4 — Stage 18 active draft

PR #75 (`stage-18/agent-background-execution`) is the current D-066 development slice. Stage 18 adds **bounded background execution** while preserving the merged Stage-15/16/17 authorities.

The background execution model is deliberately narrow:

```text
existing durable Agent Task
 -> short worker claim
 -> durable lease/fencing record beside that task
 -> RUNNING task + append-only execution evidence
 -> execute outside the long task lock
 -> exact commit fence at Production/Timeline/Generation authority
 -> short finalize/release
 -> existing trace / ProjectUnitOfWork / Generation Job recovery
```

### Lease authority

Background leases live under the existing project `tasks/` authority and use the same cross-runtime task-record lock and compare-and-swap boundary. They are not a scheduler and do not define another task state machine.

A lease is bound to:

- exact project / Plan / Task / task-record identity;
- worker ID and bounded generation;
- claim-time context digest;
- expected input digest;
- target Shot identity when applicable;
- frozen policy digest;
- bounded acquisition/heartbeat/expiry history.

The raw bearer lease token is **not portable project state**. Only its digest is durable. The raw token exists only in the ephemeral `AgentBackgroundClaim` and is excluded from `repr`; durable records reject any `lease_token` field.

### Frozen policy / evidence binding

The claim-time policy is persisted once through the existing Stage-16 append-only execution-evidence authority. Dispatch, heartbeat, canonical commit and finalization reload and compare that durable evidence. A caller cannot substitute a different `AgentPolicyProjection` through the claim object.

### Commit fencing

Production/Timeline mutation still commits through the existing ProjectUnitOfWork authority. Stage 18 wraps the final prepared commit with an exact live-claim guard.

Generation remains owned by the existing Generation Job Manager. Stage 18 fences `GenerationService.submit` before D-017 consumption or Job creation; it does not execute provider work in a new Agent scheduler.

At canonical commit the runtime revalidates:

- exact live lease ownership/token digest;
- exact RUNNING Agent Task record;
- durable execution-evidence / frozen-policy binding;
- exact context freshness.

An expired lease, forged claim, changed policy binding or changed canonical context fails closed before the background mutation is authorized.

### Recovery and replay boundary

A live leased RUNNING task is not treated as abandoned by ordinary Stage-16 reopen reconciliation. After lease expiry, Stage 18 reuses the existing exact trace/ProjectUnitOfWork/Generation Job recovery contracts.

- crash before canonical commit: no false success and no hidden redispatch;
- crash after canonical commit but before Agent success bookkeeping: recover from committed canonical evidence without replay;
- crash after lease persistence but before READY -> RUNNING: reclaim only after expiry, consuming a bounded lease generation;
- explicit cancellation continues to use the existing Stage-16 cancellation semantics;
- failed dependencies remain blocked according to the existing Stage-16 state machine.

`AgentBackgroundWorker.run_once` and `run_until_blocked` are bounded caller-driven facades. Stage 18 does **not** add autonomous polling or a second scheduler.

### Current proof boundary

The Stage-18 draft tests cover worker exclusivity, lease expiry/reclaim, heartbeat extension, token non-persistence, frozen-policy tamper rejection, context-stale refusal, cancellation/dependency behavior, crash recovery without replay, exact Generation Job reuse/reopen and Stage-17 delegation provenance.

The security-hardening head `eddd70086b1b15dc297a44dffc9d56b4ef7387d7` passed all five permanent CI jobs in run #3611 on Ubuntu and Windows. PR #75 remains draft until the final exact review head is green and receives focused Codex review before merge.

Stage 18 remains internal infrastructure. It does not claim a visible autonomous Agent product.

## D-066 current handoff and remaining order

Layer 4 is active in draft PR #75. After it is accepted, merged and lifecycle-closed, continue in this order:

1. **Layer 5 — critic/evaluation + dependency-aware local repair**;
2. **Layer 6 — human takeover/edit/resume**;
3. **Layer 7 — long-form autonomous production** only after all prior boundaries are proven.

Do not collapse these layers or jump directly to long-form autonomy.

## Capability/effects boundary

`CapabilityEffects` / resolved offer effects remain the single effects source for Agent policy, Skills and functional subagent routing. Relevant facts include project/Timeline mutation, media generation, destructive behavior, long-running behavior, reversibility and cost bearing.

No parallel Protocol Bridge/tool registry/permission authority is introduced.

## Product Truth — D-067

A user-visible feature is complete only when canonical domain/API/frontend/current-doc/evidence references agree.

Machine-readable Product Truth records live under `docs/architecture/product-truth/`. The existing named-generation record proves the Stage-14 visible generation path. Agent layers 15–17 are merged internal infrastructure; Stage 18 is active internal draft infrastructure; PR #73 is merged internal verification infrastructure. None claim a visible autonomous Agent product without a separate Studio surface and corresponding Product Truth/browser evidence.

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
11. Background execution must fail closed on lost lease authority, stale policy/evidence or stale canonical context.
12. Current docs must distinguish merged/as-built state from active/future state.
13. Do not claim autonomous product readiness from internal Agent infrastructure alone.

## Compatibility layer

Still present as compatibility/migration code unless separately promoted:

- schema-v1 `recipe_id`;
- Recipe Registry;
- Product Orchestrator and legacy `/execution-plan`;
- Stage 6/8 workspace UI;
- donor-era clients and runtime paths still needed by supported callers;
- targeted-edit/dubbing/music/continuity logic awaiting extraction into modern direction/tool surfaces.

Compatibility code may remain readable/editable while new architecture continues on the authorities defined above.
