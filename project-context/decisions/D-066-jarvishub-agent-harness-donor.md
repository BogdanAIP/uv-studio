# D-066 — JarvisHub as the reference donor for the UV Studio Agent Harness

**Status:** Accepted  
**Date:** 2026-08-25

## Context

UV Studio already owns product-specific authorities that a generic creative-agent harness must not replace: the file-first Project Store, typed Production Directions, shared Scene/Shot/Take semantics, canonical Timeline, Studio/Application Commands, ProjectUnitOfWork, capability/authorization boundaries and project-owned media references.

The missing layer is the autonomous Agent Harness that can observe project state, plan multi-step work, delegate bounded specialist work, execute long-running generation safely, evaluate results, repair only affected work and leave a trace that the user can inspect.

JarvisHub (`LYL1015/JarvisHub`) is a mature open-source reference for that missing layer. At pinned research commit `6c0f123119d9ffe1a6bae5140721f0b84ea3bbaa`, its implementation includes a substantial agent runtime with planning/task, context, memory, skills, policy, subagent, background-work and trace infrastructure. It also contains concrete patterns for tool effects, long-running/cost-bearing idempotency and generation constraints.

JarvisHub is Apache-2.0 licensed. UV Studio will primarily adapt architecture and contracts into UV-owned code. Any future direct/substantial code reuse must preserve the applicable Apache-2.0 attribution/license obligations.

## Decision

Treat JarvisHub as the **reference architecture/method donor for UV Studio's Agent Harness**, not as UV Studio's project model, canonical state authority or mandatory runtime dependency.

### 1. Keep UV product authority

The following remain UV-owned and authoritative:

- Project Store and portable project files;
- Production Direction identity and direction extensions;
- shared Scene / Shot / Take / accepted-Take semantics;
- project-owned media/assets and provenance;
- canonical Timeline and D-033 MLT adapter boundary;
- Studio/Application Commands as the only semantic mutation path;
- ProjectUnitOfWork and durable Undo/Redo;
- Model Registry and project-scoped Job Manager;
- Capability Registry, D-017 authorization and provider/adapter execution boundaries.

JarvisHub's Canvas, generic node graph, PostgreSQL/Hono deployment shape and canvas-as-source-of-truth model MUST NOT replace these authorities.

### 2. Adopt JarvisHub patterns for the future Agent Harness

The target UV Agent Harness should adapt these proven patterns:

- a persistent agent runtime/turn loop over project state rather than one-shot prompting;
- Planner + durable Task graph for multi-step production work;
- Skills as reusable bounded procedures/policies;
- context pipeline and context compaction so long projects do not require replaying the whole project/chat;
- memory for durable production decisions that are not already canonical project facts;
- a small functional subagent set, initially equivalent to `explore`, `plan`, `media` and `critic`, rather than many job-title agents;
- policy/effects metadata that lets the runtime know whether an action reads state, mutates project/timeline state, generates media, is destructive, long-running, reversible or cost-bearing;
- inspectable trace linking plans, tool/command calls, observations, generated artifacts, evaluations, failures and repair decisions to project entities;
- background execution coordinated through the UV Job Manager;
- evaluate -> repair loops that regenerate/recompute only affected material where dependencies permit.

The Agent MUST invoke the same Studio/Application Commands and capability/model/job services used by GUI, scripts and MCP. It gets no private write path.

### 3. Carry the idempotency pattern into the next Job Manager slice

Any operation that is long-running, cost-bearing or externally mutating MUST be safe against retries/replayed requests.

The UV-native Job Manager should therefore support an idempotency contract with at least:

- caller-supplied or application-generated idempotency key;
- stable normalized request/context digest bound to project, semantic target, named model, capability/offer and generation inputs;
- explicit queued/running/succeeded/failed/cancelled state;
- conflict when the same key is reused for a different normalized request;
- no duplicate execution while an equivalent request is already running;
- replay/reuse of the recorded succeeded result rather than launching the expensive work again;
- durable failure/provenance sufficient to distinguish retry from a new creative attempt.

Idempotency prevents duplicate generation. It does not replace D-017 authorization, Job history or ProjectUnitOfWork.

### 4. Add a provider-neutral Generation Contract

Generation requests should be able to state what a model may change and what must remain stable.

A bounded `GenerationContract` belongs above provider adapters and may be attached to a generation request/attempt associated with a Shot/Take. It should support concepts equivalent to:

- fixed constraints — character identity, costume, location, time/lighting, reference assets, dialogue/canon facts that must be preserved;
- editable variable(s) — the bounded creative dimension currently being changed, for example camera motion or framing;
- forbidden changes — semantic properties that must not drift;
- approved reference/keyframe identity where applicable.

The exact schema is UV-owned and must reference canonical project/production identities rather than provider prompt strings. Provider adapters render it into provider-specific prompts/options.

### 5. Extend capability metadata instead of creating a parallel tool system

JarvisHub's tool-effect idea should be adapted into the existing UV capability/application-command layer, not copied as a competing Protocol Bridge.

Future metadata should make relevant effects inspectable, including where applicable:

- `mutates_project`;
- `mutates_timeline`;
- `generates_media`;
- `destructive`;
- `long_running`;
- `reversible`;
- `cost_bearing`.

Existing locality, cost, availability and authorization concepts remain in the current Capability Registry / D-017 contracts.

### 6. Separate Job provenance from semantic acceptance

A generation Job/Attempt records what was requested, which named model/provider/adapter executed it, inputs/contract, status, outputs, timing/failure and provenance.

A generated result becomes project-owned media and then a Take candidate. Accepting a Take remains a separate semantic command through `ProductionSemanticService` / ProjectUnitOfWork. Undoing acceptance MUST NOT erase the historical generation Job or its provenance.

### 7. Trace and evaluation attach to canonical identities

Future Agent trace, evaluations and repair decisions should reference Project/Scene/Shot/Take/asset/Timeline identities. They are observations/history over canonical state, not a second project graph.

This enables a future flow such as:

```text
Director Agent
 -> plan Tasks
 -> Media worker creates generation Job for Shot 12.3
 -> Job executes named model with GenerationContract
 -> result becomes Take candidate
 -> Critic evaluates candidate against Shot/continuity/canon
 -> repair only affected generation if needed
 -> user/Agent accepts Take through normal command
 -> ProjectUnitOfWork projects accepted material to Timeline
```

## Immediate consequence for the next slice

`studio-v2-model-registry-job-manager-generation` remains the next implementation slice, but its contract is strengthened:

1. Model Registry remains user-visible and provider-neutral.
2. Job Manager includes retry-safe idempotency and durable attempt/provenance identity from the start.
3. The first generation path carries a bounded provider-neutral Generation Contract.
4. Capability/application-command effects remain explicit enough for later Agent policy/trace use.
5. Generated output becomes a project-owned Take candidate before acceptance.
6. No Agent runtime is required in this slice; the slice should expose the foundations that the later Agent Harness will consume.

## Later Agent Harness order

After the Model Registry/Job Manager/generation foundation is proven, implement the Agent Harness in bounded layers rather than one monolithic agent loop:

1. context builder + command/tool catalog + effects/policy + trace;
2. Planner + durable Tasks + Skills;
3. functional subagents: explore / plan / media / critic;
4. background work through Job Manager;
5. evaluation and dependency-aware local repair;
6. human takeover/edit/resume;
7. long-form autonomous production over the same canonical project state.

## Rejected alternatives

- **Vendor JarvisHub wholesale.** Rejected because its Canvas/node/server state model would duplicate or replace UV's existing project/production/timeline authorities.
- **Build an unrelated UV agent stack from scratch.** Rejected because JarvisHub already provides a concrete professional reference for the hard runtime patterns UV is missing.
- **Make the Agent the canonical project authority.** Rejected because manual UI, scripts, MCP and Agent must converge on the same commands and project state.
- **Implement the whole Agent before Jobs/generation.** Rejected because reliable idempotent long-running work, provenance and generation contracts are prerequisites for safe autonomy.

## Relationship to existing decisions

- D-064 remains Production Direction/product-composition authority.
- D-065 remains shared Scene/Shot/Take semantic authority.
- D-033 remains canonical Timeline/editor-engine authority.
- D-017 remains remote/non-free authorization authority.
- D-066 owns the donor relationship and target factoring of the future Agent Harness; it does not supersede the authorities above.
