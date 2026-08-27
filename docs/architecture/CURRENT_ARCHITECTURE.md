# UV Studio — Current Architecture

**Status:** CURRENT AUTHORITY  
**Date:** 2026-08-27  
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
      functional Subagents                            [next D-066 layer 3]
      background Agent execution                      [later layer 4]
      evaluate / repair                               [later layer 5]
      takeover / edit / resume                        [later layer 6]
      long-form autonomy                              [later layer 7]
 -> Capability Registry / D-017 / adapters
 -> MLT / FFmpeg / MCP / local / optional remote execution
```

Cross-cutting verification:

```text
current docs <-> Product Truth records <-> backend/API <-> frontend <-> E2E
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

PR #69 implemented the first D-066 layer and was lifecycle-closed before Stage 16 opened.

### Context Builder

`AgentContextBuilder` creates a deterministic bounded observation from canonical Project / Production / Timeline / Model / Job authorities. It uses bounded nested collections and omitted counts; it does not copy the project into an Agent-owned graph.

### Existing-authority action catalog

`AgentActionCatalog` exposes stable metadata only over existing UV authorities:

- ProductionSemanticService actions;
- TimelineCommandService actions;
- named generation through GenerationService.

The catalog exposes effects, authority, input contract, Job Manager routing and possible D-017 routing. There is no generic `project.write_file`, shell, Python or arbitrary provider command.

### Policy

Agent policy projects existing availability/locality/cost/`CapabilityEffects`/D-017 facts. It may report that consent is required but cannot grant consent.

### Inspectable trace

`AgentTraceStore` keeps append-only project-scoped execution history under the existing `tasks/` authority. Trace binds context digest, action/policy/effects, canonical identities, result references and sanitized failures while excluding raw prompts, authorization tokens, secrets, absolute host paths and provider-private state.

### Execution seam

`AgentHarness` delegates canonical mutation to the same Production/Timeline/Generation services used by other callers. Stage 15 proved success and failure tracing, unavailable models, D-017 separation, bounded context and restart/reopen.

## Agent Harness layer 2 — Stage 16 merged

PR #70 implemented the second D-066 layer and merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2` after exact-head CI #3442 passed all five permanent jobs and a fresh Codex review found no major issues.

The merged layer adds orchestration above Stage 15 without changing canonical authorities:

```text
bounded goal
 -> Stage-15 Context + Action Catalog + Policy
 -> AgentPlanner validates structured proposal
 -> append-only AgentPlanRecord
 -> durable dependency-aware AgentTaskRecord state
 -> bounded Skill expansion
 -> foreground AgentTaskCoordinator
 -> AgentHarness
 -> existing UV application authorities
 -> Stage-15 trace + canonical result references
```

### Planner

The Planner contract is structured and UV-validated rather than hidden free-form reasoning. It validates bounded step/task counts, stable IDs, action/Skill identities, portable inputs, dependency references, cycles, policy availability, canonical context binding and canonical prerequisites against current state/dependency closure.

A future model may propose this structured plan; UV validation remains deterministic and authoritative.

### Durable Agent Tasks

Plans and task records use the existing project `tasks/` root via `ProjectTaskRecordStore`. Agent Tasks are orchestration state, not Generation Jobs, production truth or Undo history.

Current bounded state machine:

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

Dependencies unlock only after success. A failure does not falsely unlock downstream tasks or mark the plan successful. Cross-runtime CAS/locking and restart reconciliation prevent stale task-state overwrites and silent replay.

### Skills

Skills are reusable bounded procedures over approved Agent catalog actions. The first architecture-proof Skill is `production.scene_with_shot`, which expands into `production.create_scene` followed by dependent `production.create_shot`.

Skills derive their effects/authority envelope from underlying catalog actions and do not gain shell, Python, arbitrary filesystem/provider or D-017 bypass rights.

### Foreground execution and recovery boundary

Stage 16 executes runnable tasks in the foreground through `AgentHarness`. It durably binds execution-time context/policy and typed task correlation before canonical/cost-bearing dispatch. Production/Timeline recovery reuses committed `ProjectUnitOfWork` evidence; generation recovery requires exact Job/idempotency/request/mapping evidence and never silently resubmits.

Stage 16 remains internal infrastructure. It is not a user-visible autonomous-Agent readiness claim and therefore does not invent a D-067 product claim without a real Studio surface and browser proof.

## D-066 next handoff and remaining order

The repository is lifecycle-idle after Stage 16 closure. The one declared next handoff is **functional subagents** — bounded `explore / plan / media / critic` roles consuming the merged Context / Planner / Task / Skill contracts.

After that, the accepted order remains:

1. **background Agent work** coordinated through existing Job Manager boundaries;
2. **critic/evaluation + dependency-aware repair**;
3. **human takeover/edit/resume**;
4. **long-form autonomous production** only after all prior boundaries are proven.

Do not collapse these layers or jump directly to long-form autonomy.

## Capability/effects boundary

`CapabilityEffects` / resolved offer effects remain the single effects source for Agent policy, Skills and future subagent routing. Relevant facts include project/Timeline mutation, media generation, destructive behavior, long-running behavior, reversibility and cost bearing.

No JarvisHub-style parallel Protocol Bridge/tool registry/permission authority is introduced.

## Product Truth — D-067

A user-visible feature is complete only when canonical domain/API/frontend/current-doc/evidence references agree.

Machine-readable Product Truth records live under `docs/architecture/product-truth/`. The existing named-generation record proves the Stage-14 visible generation path. Agent layers 15–16 remain explicitly internal unless a later slice adds a real Studio Agent surface and corresponding Product Truth/browser evidence.

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
6. Do not give the Agent, a Skill or a subagent a private project-write path.
7. Agent context/plan/task/trace/role state are orchestration/inspection state over canonical identities, not canonical production state.
8. Generation Job/Attempt history remains separate from Agent Task orchestration state.
9. Remote/non-free execution remains explicit and D-017-authorized where required.
10. Provider prompts, secrets, reusable authorization and provider-private continuation caches never become portable Project/Agent state.
11. Current docs must distinguish merged/as-built state from active/future state.
12. Do not claim autonomous product readiness from internal Agent infrastructure alone.

## Compatibility layer

Still present as compatibility/migration code unless separately promoted:

- schema-v1 `recipe_id`;
- Recipe Registry;
- Product Orchestrator and legacy `/execution-plan`;
- Stage 6/8 workspace UI;
- donor-era clients and runtime paths still needed by supported callers;
- targeted-edit/dubbing/music/continuity logic awaiting extraction into modern direction/tool surfaces.

Compatibility code may remain readable/editable while new architecture continues on the authorities defined above.
