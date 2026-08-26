# UV Studio — Current Architecture

**Status:** CURRENT AUTHORITY  
**Product-composition decision:** D-064  
**Shared production-semantics decision:** D-065  
**Agent Harness donor/factoring decision:** D-066  
**Product Truth verification decision:** D-067  
**Desktop update/version decision:** D-068  
**Stateful generative continuation decision:** D-069  
**Editor foundation:** D-033

This document is the primary architecture entry point for new development. Historical recovery documents, Recipe Registry flows, Product Orchestrator projections and numbered Stage workspaces are not competing target architectures.

## Product definition

UV Studio is a **local-first AI production studio with multiple Production Directions over one shared production/application core**.

A Production Direction describes how a kind of production is organized: navigation, policies, specialized domain documents and Agent context. It does not create a separate editor engine, project store, timeline authority, execution stack or duplicate common Scene/Shot/Take semantics.

Initial directions:

- `micro_drama` — micro-drama / story production;
- `commercial` — advertising / product video;
- `music_video` — music-video production;
- `narrated_video` — narrated/explainer video;
- `dub_battle` — cinematic revoicing / dub battle;
- `free_project` — free-form Studio project.

## Canonical shape

```text
Project
  -> Production Direction
       organization / navigation / policy / Agent context
  -> Shared Production Semantic Core (optional per project)
       Sequence / Scene
       Shot
       Take / Candidate / Accepted Take
       semantic references / continuity / canon
       production-to-asset and production-to-timeline bindings
  -> Direction Extensions
       micro-drama: story / characters / locations / dramaturgy
       commercial: brief / product / brand / audience / concepts
       music-video: song / Music Map / sections / visual direction
       narrated: script / narration / semantic segments
       dub-battle: source scene / dialogue / cast / mix policy
  -> Shared Studio Core
       Media / Assets
       Preview / Canvas
       Inspector / AI Tools
       canonical Timeline
       Studio/Application Commands
       Project Unit of Work / Undo-Redo
       Model Registry
       Job Manager
       Agent Harness
       Export
       Update UI / Update Service (desktop release layer)
  -> Capability / Adapter boundaries
  -> MLT / FFmpeg / MCP / local models / optional remote tools
```

Not every project must instantiate every production-semantic entity. `free_project` may remain Media/Assets/Timeline-only; a commercial may use Shots/Takes without a Story; a music video can group shared Shots under Music Map sections.

## Canonical authorities

- **Project Store** owns portable project state and project-owned references.
- **Production Direction identity** is typed Studio metadata and selects organization/policy, not execution engine.
- **Shared Production Semantic Core** owns reusable Scene/Shot/Take/accepted-material identities where needed.
- **Direction Extensions** own genuinely direction-specific data while referencing shared identities for common concepts.
- **Canonical Timeline** is UV-owned assembly state; MLT is derived behind the D-033 adapter.
- **Studio/Application Commands** are the shared semantic mutation boundary for GUI, Agent, scripts and MCP.
- **Project Unit of Work** owns atomic multi-document mutations and durable undo/redo across production semantics, project references/assets and Timeline.
- **Model Registry** owns user-visible named model identity and maps it onto lower execution capabilities/providers.
- **Job Manager** owns project-scoped long-running lifecycle, retry/idempotency and durable execution/generation provenance.
- **Agent Harness** observes and acts through the same commands/models/jobs/capabilities as manual callers; it does not own a second project graph or private mutation path.
- **Capability Registry / D-017 / adapters** own execution availability, authorization and transport, not product identity.
- **Product Truth Contracts** are verification metadata that bind user-visible surfaces to those canonical authorities; they do not become runtime product state.
- **Update Service** owns installed-application update discovery/download/verification/handoff; it does not own or rewrite Project Store data except through explicit supported migrations.

## Production semantics versus Timeline

A Shot is not a Timeline Clip.

```text
Shot
  -> intent / references / continuity
  -> generated/imported candidate Takes
  -> accepted Take
  -> project-owned asset
  -> one or more Timeline clips for assembly
```

This gives the Agent/UI a production-level model without creating a second canonical timeline.

Stage 13 implemented the first complete shared vertical path: Scene -> Shot -> multiple Takes -> direction context -> accepted Take -> project-owned media provenance -> canonical Timeline, including project-level Undo/Redo and cross-direction reuse of the shared contracts.

## Generation and long-running work

Generated media is not accepted production state merely because a model returned a file.

Stage 14 implements this flow:

```text
Shot / production intent
  -> choose named Model
  -> GenerationContract
  -> project-scoped Job / execution Attempt
  -> Capability / Provider / Adapter execution
  -> project-owned generated asset + provenance
  -> Take candidate
  -> explicit acceptance command
  -> canonical Timeline projection
```

The backend-owned `ModelRegistry` separates user-visible model identity from provider/adapter/capability mapping. The project-scoped `GenerationJobManager` persists queued/running/succeeded/failed/cancelled generation state under the existing project `tasks/` authority. The Job/Attempt layer records what was requested and executed; Take acceptance records production meaning. Undoing Take acceptance does not erase the historical generation Job/Attempt or its provenance.

Long-running, cost-bearing or externally mutating generation is retry-safe. The Job Manager uses a UV-native idempotency contract that binds an idempotency key to a stable normalized request/context digest: same key + same digest reuses the Job/result; same key + different digest fails closed; a fresh key explicitly permits an intentional creative reroll even when normalized creative inputs are identical.

D-017 remains separate from idempotency. A fresh external/cost-bearing execution still requires the normal exact one-shot authorization; replay of an already-created Job does not consume a fresh grant.

A provider-neutral `GenerationContract` constrains what a generation attempt may change. It expresses fixed constraints, editable variables, forbidden changes and approved project references/keyframes where applicable. Provider adapters translate this semantic contract into provider-specific prompts/options; provider prompt text is not canonical production truth.

For stateful/sequential generation, `GenerationContract` may also carry a provider-neutral `continuation_source_reference_id` pointing to prior project media. An execution offer must explicitly advertise `generation.continuation` before that field is accepted. The parent reference participates in the normalized request/idempotency digest and is recorded as parent -> child lineage in generated-media provenance.

Continuation lineage is durable project truth; model-private execution state is not. KV/attention caches, latents, provider session handles, sliding history windows and anchor-frame caches remain adapter-owned, disposable optimizations. Losing such runtime state may reduce performance but must not erase or reinterpret the durable generation chain. InfinityEdit is a technology donor/candidate adapter for this pattern, not a required runtime or product authority. See D-069.

Stage 14 intentionally does not ship a real continuation-capable offer or Continue/Edit UI. That later user-visible workflow needs its own Product Truth record and browser proof.

## Agent Harness donor boundary — D-066

JarvisHub is the reference architecture/method donor for the future UV Studio Agent Harness.

Borrow/adapt its proven patterns for:

- persistent agent runtime/turn loop;
- Planner + durable Tasks;
- Skills;
- context pipeline, memory and compaction;
- a small functional subagent set such as explore / plan / media / critic;
- action/tool effects and policy;
- inspectable trace;
- background execution;
- evaluate -> repair loops and dependency-aware local repair.

Do **not** adopt JarvisHub's Canvas-as-source-of-truth, generic node project model, PostgreSQL/Hono application authority or duplicate tool/protocol layer. UV Studio already has its own canonical project/production/timeline/transaction/capability authorities.

The future runtime shape is therefore:

```text
Human UI / Chat / scripts / MCP          Director Agent
              |                    explore / plan / media / critic
              +--------------------------+
                         |
              Studio/Application Commands
                         |
                 Project Unit of Work
             /             |              \
 Production Semantics   Project Store   Timeline
                         |
                  Model Registry
                         |
                    Job Manager
                         |
                Capability / Adapters
                         |
           local / MCP / optional remote
```

Agent trace, evaluation and repair records reference canonical Project/Scene/Shot/Take/asset/Timeline identities. They are history/observations over project truth, not a second source of truth.

## Capability/effects boundary

JarvisHub's useful action-effect pattern is adapted into existing UV-owned command/capability metadata instead of creating a competing Protocol Bridge.

`CapabilityEffects` and `CapabilityRegistry.effects_for_offer()` expose inspectable flags for:

- project mutation;
- Timeline mutation;
- media generation;
- destructive behavior;
- long-running behavior;
- reversibility;
- cost-bearing execution.

Resolved offer effects are exposed through the existing capability-offers API. Media-generation/long-running facts are derived from the canonical capability/offer contract, while actual locality/cost permission remains the selected offer plus D-017. No second JarvisHub-style tool registry is introduced.

## Product Truth and current-documentation consistency — D-067

A user-visible feature is not complete merely because one implementation layer exists.

The verification shape is:

```text
Current Documentation Consistency
        +
Product Surface Parity
        +
User Outcome Proof
        =
Product Truth
```

Machine-readable Product Truth records live under `docs/architecture/product-truth/*.json`. `uv_studio/product_truth.py` validates exact source references instead of interpreting Markdown semantics. For a ready user-visible feature the schema binds stable feature identity, canonical domain method, backend/API route, frontend component and declared controls, canonical state/results, dependencies, visible states and browser/API proof identifiers.

For a feature declared user-visible and ready on `main`:

- frontend UI must not advertise a non-existent/stub canonical backend/application path;
- backend functionality must not be counted as a completed user feature when its required product surface is absent;
- declared domain/API/frontend/evidence references must resolve deterministically;
- user-significant model/cost/progress/error semantics must remain truthful across layers;
- a real user-outcome proof must exercise the intended path through the product UI.

Internal infrastructure may intentionally have no UI, but must be explicitly non-user-visible/not-ready rather than silently counted as product functionality.

Current documentation is also product truth. `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, `CURRENT_ARCHITECTURE.md`, authority indexes and machine-readable feature contracts must agree on narrow machine-checkable facts. CI validates explicit markers/references/contracts rather than attempting brittle semantic interpretation of arbitrary prose.

The first implemented record is `docs/architecture/product-truth/generate-shot-take.json`. It binds the Stage-14 visible named-model generation surface to `GenerationService.submit`, its FastAPI route, Job/Attempt + artifact + Take state and the API/browser tests that prove the outcome. Normal models with unavailable or `configuration_required` offers remain visibly blocked; the successful CI proof transport is explicitly env-gated and test-only.

See `docs/architecture/PRODUCT_TRUTH_CONTRACT.md`.

## Desktop update/version boundary — D-068

The maintained desktop product uses one normal installation identity and supports in-place updates from the UI.

Target user flow:

```text
Settings / About
 -> Check for updates
 -> show newer version + release notes
 -> Download and update
 -> verify digest/signature/artifact identity
 -> controlled app shutdown
 -> out-of-process updater/installer replacement
 -> migrations when required
 -> restart
 -> healthy startup
```

Application/runtime files are replaceable; Project Store projects, user media, intended persistent settings and other user-owned data remain separately protected.

GitHub Releases may be the initial distribution source, but the application consumes bounded machine-readable update metadata rather than scraping arbitrary release pages. The updater fails closed on integrity/signature mismatch.

Release evidence must include both clean install and **N-1 -> N in-place upgrade** using representative project/settings state. A successful clean installation does not prove upgrade safety.

Application version, Project Store schema version and production-domain schema versions remain separate identities.

See `docs/architecture/DESKTOP_UPDATES.md`.

## Direction versus tool

A direction answers **what kind of production is being organized**. A tool answers **what operation should be performed inside a project**.

Directions: micro-drama, commercial, music video, narrated video, dub battle, free project.

Contextual tools: targeted edit, ordinary dubbing/translation, photo-to-video/slideshow, visualizer, action transfer, talking character, lip-sync, background replacement, image/video/audio generation.

A tool may be especially useful in one direction without becoming a separate project identity.

## Rules for new work

1. Do not add a `RecipeDefinition` to ship a new product direction or feature.
2. Do not grow Product Orchestrator recipe-by-recipe as the target application architecture.
3. Do not add a numbered Stage workspace as normal product navigation.
4. Do not create a second canonical project/timeline state.
5. Do not create a direction-specific editor engine.
6. Do not create parallel direction-specific Scene/Shot/Take schemas when the semantic concept is shared.
7. Do not hide user-significant model choice behind capability selection.
8. GUI, Agent, scripts and MCP must converge on the same application/domain commands.
9. Reuse mature media/editor/model/agent components behind UV-owned boundaries rather than copying their application model.
10. Keep compatibility paths until call-site/dependency proof permits deletion.
11. Modern Studio identity must be validated independently from compatibility `recipe_id` and generic extensions mutation.
12. Do not give the Agent a private write path or let Agent memory/trace become canonical project state.
13. Do not execute a replayed long-running/cost-bearing generation twice when the normalized idempotency identity is the same.
14. Do not make provider prompt text the canonical representation of production constraints.
15. Do not declare a user-visible feature ready on `main` when its Product Truth Contract has an unresolved backend/frontend/evidence gap.
16. Current architecture/project-context documents must distinguish as-built from target state and keep machine-checkable current facts synchronized.
17. Stable desktop releases must update the maintained installation in place by default; clean-install success never substitutes for N-1 -> N upgrade proof.
18. Do not persist provider-private continuation cache/latent/session state as canonical project data; sequential generation must be reconstructible from durable project media lineage and request provenance.

## Current implementation boundary after Stage 14

Stages 12 through 14 now provide the concrete lower foundation for generation and later autonomy:

- modern Studio/project-media APIs use recipe-free common project contracts;
- modern Production Direction identity has a typed load/update/import gate with explicit compatibility and recovery projections;
- bounded `production/` storage owns strict shared semantics and direction documents;
- `ProjectUnitOfWork` coordinates strict canonical JSON with prepared journals, exact rollback/recovery and durable project-level undo/redo;
- timeline commands plus source/export reference registration use the shared transaction authority;
- shared `Scene`, `Shot`, `Take` and accepted-Take contracts are implemented in `production/semantics.json`;
- micro-drama Story/Characters/Locations/continuity extensions are implemented in `production/micro_drama.json`;
- `ProductionSemanticService` is the shared semantic mutation boundary;
- Take acceptance can atomically span production state, project-owned media provenance and canonical Timeline;
- Undo/Redo preserves a single project history across production and Timeline;
- the shared Scene/Shot/Take contracts are proven outside micro-drama through the commercial direction;
- the backend-owned Model Registry separates named model choice from provider transport;
- project-scoped generation Jobs/Attempts persist retry-safe execution history and idempotency provenance;
- `GenerationContract` preserves provider-neutral semantic constraints, including D-069 continuation parent lineage;
- generated media is registered as project-owned material before it becomes a shared Take candidate;
- Studio UI exposes named model/Shot/prompt/contract controls and truthful queued/running/succeeded/failed/cancelled/result states;
- offer-resolved effects metadata is available from the existing Capability Registry/API for future policy/trace consumers;
- `docs/architecture/product-truth/generate-shot-take.json` plus `uv_studio/product_truth.py` provide the first machine-readable D-067 parity contract;
- API and cross-platform browser tests prove named generation -> Take -> acceptance -> canonical Timeline -> Undo without deleting Job provenance.

D-069's durable continuation-lineage seam is implemented as backend/contract groundwork only. A real InfinityEdit/Helios adapter, real `generation.continuation` offer and user-visible Continue/Edit workflow remain future Product Truth work.

The full Planner/Memory/Skills/Subagents Agent Harness remains later work. The next post-Stage-14 implementation slice is selected only after this PR is merged and lifecycle-closed so the handoff is based on current `main`, not speculative parallel architecture.

Desktop Update Service/UI and packaged N-1 -> N upgrade verification remain Stage-9 desktop release/productization work; clean-install success must never be treated as upgrade proof.

## Compatibility layer

The repository still contains old recipe, Product Orchestrator, Stage 8 and donor-era paths because supported historical projects/domain implementations may depend on them.

They are **compatibility/migration code** unless a later accepted decision explicitly promotes something back into current architecture:

- schema-v1 `recipe_id` is compatibility metadata;
- Recipe Registry is not the v2 product taxonomy;
- Product Orchestrator is not the long-term product center;
- legacy `/execution-plan` is not current application truth;
- Stage 6/8 workspaces are not the template for new direction UI;
- useful targeted-edit, dubbing, music, continuity and media adapters should be extracted/reused rather than discarded;
- legacy projects may remain readable/editable in an explicit compatibility mode without being assigned a fake Production Direction.

See `docs/architecture/README.md`, D-064, D-065, D-066, D-067, D-068 and D-069.
