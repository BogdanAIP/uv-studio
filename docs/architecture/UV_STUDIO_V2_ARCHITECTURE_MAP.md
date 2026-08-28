# UV Studio v2 — architecture map and migration inventory

**Status:** active architecture map under D-064 + D-065 + D-066 + D-067 + D-068 + D-069 + D-070  
**Date:** 2026-08-28

Classifications: **KEEP**, **ADAPT**, **MOVE**, **LEGACY**, **DELETE LATER**.

## 1. Current diagnosis

UV Studio now has a concrete shared production/generation spine, four merged Agent-orchestration layers, and a merged Stage-16/17 adversarial-assurance pilot. Stage 18 bounded background Agent execution merged through PR #75; D-070 now makes architecture compression and a user-visible golden vertical the product gate before further Agent autonomy:

```text
Project Store
 -> Production Directions
 -> shared Scene / Shot / Take semantics
 -> Studio/Application Commands
 -> ProjectUnitOfWork / durable Undo-Redo
 -> canonical Timeline
 -> visible Model Registry
 -> Generation Job Manager / GenerationContract
 -> Capability Registry / D-017 / adapters
 -> Agent Harness layer 1: Context / Catalog / Policy / Trace       [Stage 15 merged]
 -> Agent Harness layer 2: Planner / durable Tasks / Skills         [Stage 16 merged]
 -> Agent Harness layer 3: functional Subagents                     [Stage 17 merged]
 -> curated Stage-16/17 adversarial assurance                       [PR #73 merged]
 -> Agent Harness layer 4: bounded background execution             [Stage 18 / PR #75 merged]
 -> D-070 product-first gate: architecture compression + golden vertical
 -> later D-066 autonomy: evaluate/repair -> takeover -> autonomy
```

The old product-composition errors remain rejected:

1. recipe/workspace proliferation as separate products;
2. one generic editor shell with insufficient production semantics;
3. a parallel Agent project/tool/permission authority;
4. a second Agent scheduler or provider-execution authority hidden behind background work.

D-064 owns Production Directions. D-065 owns shared production semantics. D-066 owns the ordered Agent Harness build-out. D-067 verifies current-document/product parity. D-068 owns later desktop in-place updates. D-069 owns provider-neutral sequential-generation lineage. D-070 owns the product-first sequencing gate before further Agent autonomy.

## 2. Target architecture

```text
                              Project
                                 |
                      Production Direction
       micro_drama | commercial | music_video | narrated | dub_battle | free
                                 |
                   Shared Production Semantic Core
                       Scene | Shot | Take
                                 |
                       Direction Extensions
                                 |
                         Shared Studio Core
       Media / Preview / Inspector / canonical Timeline / Export
                                 |
                    Studio / Application Commands
                                 |
                       ProjectUnitOfWork
                                 |
                    Model Registry + Job Manager
                                 |
                         Agent Harness
       Stage 15: Context -> Catalog -> Policy -> Trace            [merged]
       Stage 16: Planner -> durable Tasks -> Skills                [merged]
       Stage 17: functional Subagents                             [merged]
       Stage 18: bounded background execution                     [merged]
       D-070: architecture compression -> micro_drama golden vertical
       later: evaluate/repair -> takeover -> autonomy
                                 |
                       Capability Registry
                                 |
                    Adapter / Transport Registry
                 MLT / FFmpeg / MCP / local / cloud
```

All Agent mutations ultimately return to the same Studio/Application Commands or existing GenerationService authority. Agent state coordinates work; it does not redefine project truth.

## 3. Production Directions — KEEP + GROW

Current direction identity is typed Studio metadata. Direction-specific documents organize the workflow while shared concepts reuse shared semantic IDs.

| direction_id | Specialized organization |
| --- | --- |
| `micro_drama` | story, characters, locations, dramaturgy + shared Scenes/Shots/Takes |
| `commercial` | brief, product, brand, audience, concepts + shared Shots/Takes |
| `music_video` | song, Music Map, sections, visual direction + shared Shots/Takes |
| `narrated_video` | script, narration, semantic segments, subtitles/visual plan |
| `dub_battle` | source scene, dialogue, cast, mix policy + shared semantics where appropriate |
| `free_project` | no mandatory production-semantic structure |

A direction is not a provider, recipe execution engine or separate editor.

## 4. Shared Production Semantic Core — KEEP + GROW ONLY WHEN PROVEN

Stage 13 established:

- strict Scene / Shot / Take / accepted-Take contracts;
- multiple candidate Takes per Shot;
- project-owned media/provenance bindings;
- accepted production material -> canonical Timeline projection;
- direction extensions referencing shared identities;
- `ProductionSemanticService` as one shared mutation boundary;
- `ProjectUnitOfWork` across production/project/Timeline mutations;
- durable Undo/Redo;
- cross-direction proof.

Shot remains independent from Timeline Clip. Do not grow a giant film schema without cross-direction evidence.

## 5. Generation foundation — KEEP

Stage 14 implemented:

```text
Shot
 -> named Model
 -> GenerationContract
 -> idempotent Job / Attempt
 -> Capability / Adapter execution
 -> project-owned artifact + provenance
 -> Take candidate
 -> explicit acceptance
 -> canonical Timeline
```

Keep:

- backend-owned meaningful Model Registry;
- project-scoped Job/Attempt lifecycle;
- exact idempotency;
- explicit retry/failure/cancellation history;
- D-017 separation from Job replay;
- provider-neutral GenerationContract;
- D-069 parent media lineage;
- provider-private cache/session/latent state outside Project Store.

A real InfinityEdit/Helios continuation provider/UI remains later capability/product work, not Agent Harness scope.

## 6. Agent Harness layer 1 — Stage 15 IMPLEMENTED

PR #69 supplies the first internal foundation.

### Context Builder — KEEP

Bounded deterministic observation over canonical Project / Production / Timeline / Model / Job state. Nested collections use explicit limits/omitted counts. No project clone, secrets, host paths, raw provider prompts or private caches.

### Existing-authority action catalog — KEEP + GROW CAREFULLY

Current action metadata resolves only to existing UV services:

- ProductionSemanticService;
- TimelineCommandService;
- GenerationService.

Unknown actions fail closed. The catalog does not expose generic shell, Python or project filesystem mutation.

### Policy — KEEP

Policy consumes existing `CapabilityEffects`, availability, locality, cost and D-017 preparation facts. It cannot self-authorize.

### Trace — KEEP

Append-only project-scoped inspection records under the existing `tasks/` authority bind context digest, action/policy/effects, canonical identities, result refs and sanitized failures. Trace is not canonical production state.

### Bounded execution — KEEP

`AgentHarness` dispatches only through existing UV services.

## 7. Agent Harness layer 2 — Stage 16 IMPLEMENTED

PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2` after final exact-head CI and review.

The merged implementation adds:

```text
bounded goal
 -> Stage-15 context/catalog/policy
 -> validated structured Planner proposal
 -> append-only AgentPlanRecord
 -> durable AgentTaskRecord dependency/state graph
 -> bounded Skill expansion
 -> foreground task execution through AgentHarness
 -> existing canonical transaction/Job result
 -> Stage-15 trace linked from durable task state
```

### Planner — KEEP UV-OWNED CONTRACT

Planning output is UV-validated structured data rather than a separate node graph. Validation covers bounded counts, stable IDs, portable inputs, catalog membership, dependencies/cycles, context binding, policy availability and canonical prerequisites.

### Durable Agent Tasks — KEEP AS ORCHESTRATION STATE

Task state lives under the existing project `tasks/` root. It does not replace Generation Jobs or ProjectUnitOfWork history.

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

Dependencies unlock only after success. A failed prerequisite leaves dependants blocked according to the existing state machine. Terminal tasks do not silently replay. Cross-runtime CAS and task locking protect transitions.

### Skills — BOUNDED PROCEDURES, NOT NEW PERMISSIONS

A Skill expands into approved Agent catalog actions/tasks and derives effects/authority from those actions. No Skill may introduce shell, Python, arbitrary filesystem/provider execution or D-017 bypass.

### Foreground coordinator — MERGED BOUNDARY

Stage 16 binds execution-time context/policy/correlation evidence, links durable task state to existing trace and canonical result identities, and reconciles committed work on reopen without silent replay.

## 8. Agent Harness layer 3 — Stage 17 IMPLEMENTED

PR #71 merged as `c3ca3c33f89f67fad97081f889934669e34befa5` and was lifecycle-closed by PR #72.

It implements bounded foreground roles:

- `explore` — advisory findings over explicit canonical context;
- `plan` — structured proposals still validated by the existing Planner;
- `media` — bounded media/generation/Take/Timeline proposal subset;
- `critic` — read-only evaluation over durable Plan/Task/linked-trace evidence, without repair authority.

Role output is bound to exact context, revalidated before persistence and assigned typed content-addressed delegation provenance carried through the existing Plan/Task/Trace path.

PR #73 merged as `d1413e5753c24f207faf5a20828f891c14f53aa0`. Its curated mutation runner is verification infrastructure only and protects selected Stage-16/17 context/provenance/shared-authority guarantees.

Classification: **KEEP**.

## 9. Agent Harness layer 4 — Stage 18 IMPLEMENTED

PR #75 (`stage-18/agent-background-execution`) merged as `c5051b975a1ba8e747f453dd0a485cac1e308ba7`. It implements bounded background execution over the existing Stage-16 task state machine and Stage-17 provenance without creating a second scheduler, task graph, project authority, mutation authority or provider executor.

Current flow:

```text
READY durable Agent Task
 -> bounded worker claim
 -> lease record under existing tasks/ authority
 -> RUNNING + append-only execution evidence
 -> execution outside long task lock
 -> shared cross-runtime canonical commit fence
 -> finalize/release
 -> existing trace / ProjectUnitOfWork / Generation Job recovery
```

### Lease/fencing model — KEEP

The lease record is durable fencing metadata only. It is bound to exact task/worker/generation/context/input/policy/target facts and uses existing task-root CAS/locking.

The raw bearer `lease_token` is intentionally **ephemeral**:

- only its digest is persisted;
- the raw token lives in `AgentBackgroundClaim` only;
- claim `repr` excludes it;
- durable record parsing rejects any raw `lease_token` field;
- bounded history stores token/policy digests, never reusable bearer authorization.

Claim-time policy is persisted once in the existing Stage-16 execution-evidence store. Background dispatch, heartbeat, commit and finalization reload and verify that evidence rather than trusting caller-supplied policy.

### Canonical commit fence — KEEP

Production and Timeline continue through ProjectUnitOfWork. The background seam rechecks live lease ownership, exact RUNNING task, durable evidence/policy binding and exact canonical freshness at the final prepared commit.

The accepted implementation reuses the existing re-entrant `ProjectTaskRecordStore.project_lock` across Production/Timeline semantic read-modify-commit, ProjectUnitOfWork, direct canonical Production/Timeline stores, every freshness-tracked JSON writer under `production/` or `timeline/`, existing-project `project.json` writes, and Generation same-key lookup/D-017 consumption/Job reservation. Long provider execution remains outside this bounded critical section and remains Generation Job Manager responsibility.

`AgentContextBuilder.digest` remains a bounded observation digest. Stage 18 separately hashes exact canonical `project.json`, `production/**/*.json` and `timeline/**/*.json` bytes so timing/source/reference changes omitted from the Agent observation still invalidate a stale background claim.

### Recovery model — KEEP

- live leased RUNNING work is not prematurely reconciled as abandoned;
- expired leases reuse existing Stage-16 exact trace/transaction/job recovery;
- no hidden redispatch of ambiguous RUNNING work;
- pre-dispatch lease loss can be reclaimed only after expiry with a bounded generation count;
- post-commit/pre-trace loss recovers from committed canonical evidence without replay;
- cancellation and dependency semantics remain those of the existing Stage-16 state machine.

### Bounded worker facade — KEEP

`AgentBackgroundWorker` exposes bounded `claim`, `execute`, `run_once` and `run_until_blocked`. There is no autonomous poll loop in Stage 18.

### Accepted proof

The Stage-18 test/review series proves:

- exclusive worker ownership;
- expiry/stale-worker commit refusal;
- safe pre-dispatch reclaim with bounded history;
- post-commit/pre-trace crash recovery without replay;
- explicit cancellation/dependency blocking;
- exact Generation Job identity/reopen;
- Stage-17 delegation provenance/reopen;
- live-lease reopen and expiry reconciliation;
- raw token non-persistence / non-disclosure in `repr`;
- forged policy/correlation rejection;
- heartbeat extension of the same authority;
- stale exact canonical-state refusal before commit;
- cross-runtime Production/Timeline/project updates serialize and preserve both edits;
- same-key Generation submission creates/reuses one durable Job and consumes authorization once;
- foreground coordinators cannot replace installed background fences;
- direct canonical stores and all freshness-tracked Production/Timeline JSON writers share the project fence;
- concurrent background coordinator construction reserves harness ownership atomically.

All concrete PR #75 review findings were resolved. Final exact head `4c80bc96512e5ba34b0c3ed973c76c1c7a029568` passed all five permanent CI jobs before merge.

Classification: **KEEP** as merged internal Agent infrastructure. It does not claim a visible autonomous Agent product.

## 10. D-070 product-first handoff before D-066 remaining order

After Stage 18 merge and protected-main lifecycle closure, the next slice is **not** Layer 5. The next slice is `architecture-compression-inventory`.

That behavior-preserving slice must map exact live callers, compatibility-only paths, canonical replacements, durable migration requirements and deletion gates for at least Recipe Registry, `uv_studio/orchestration/**`, `api/recipes.py`, `api/execution.py` / `/execution-plan`, Stage 6/8 product-composition surfaces, server compatibility routes and schema-v1 `recipe_id`.

Further Agent autonomy resumes only after both D-070 gates are satisfied:

1. **Architecture compression gate** — legacy/modern overlap has an accepted caller/migration map, superseded composition gains no new callers, and duplicate authorities have bounded retirement slices.
2. **Golden vertical gate** — GUI proves `New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`, with Agent using the same Studio/Application Commands, Generation Job authority and Capability/D-017 boundaries when invoked.

When Agent-autonomy work resumes, preserve D-066 order:

1. **Layer 5 — evaluation + dependency-aware local repair**;
2. **Layer 6 — human takeover/edit/resume**;
3. **Layer 7 — long-form autonomous production**.

Do not jump directly to long-form autonomy.

## 11. Product Truth — KEEP

D-067 keeps current docs, machine-readable feature contracts, backend/API/frontend and user-outcome evidence consistent.

The visible record remains named generation -> Take. Stages 15–18 are merged internal Agent infrastructure, and PR #73 is merged internal assurance infrastructure. None claim a visible autonomous Agent product without a separate Studio surface and browser proof.

## 12. Desktop update layer — ACCEPTED TARGET, DEFERRED HERE

D-068 target:

```text
Settings / About
 -> current version
 -> Check for updates
 -> verified manifest/artifact
 -> controlled replacement
 -> restart / supported migrations
 -> healthy N+1 application
```

Release proof must include N-1 -> N in-place upgrade, not only clean install. Keep this separate from Agent implementation slices.

## 13. Contextual tools — NOT DIRECTIONS

Targeted edit, ordinary dubbing/translation, slideshow/photo-to-video, visualizer, action transfer, talking character, lip-sync, background transforms and image/video/audio generation are tools/capabilities inside a project, not new project identities.

## 14. Foundation inventory

| Area | Classification | Current meaning |
| --- | --- | --- |
| Project Store | **KEEP** | one portable project authority |
| Project refs/media | **KEEP** | canonical project-owned asset identity/provenance |
| Production Directions | **KEEP + GROW** | product organization/policy |
| Shared Scene/Shot/Take | **KEEP + GROW CAREFULLY** | common production semantics |
| Canonical Timeline / D-033 | **KEEP** | UV-owned assembly state, MLT derived |
| Studio/Application Commands | **KEEP + GROW** | shared GUI/Agent/scripts/MCP mutation authority |
| ProjectUnitOfWork | **KEEP** | transaction + Undo/Redo authority |
| Capability Registry / D-017 | **KEEP** | execution semantics/effects/auth |
| Model Registry | **KEEP** | meaningful model identity |
| Generation Job Manager | **KEEP** | execution provenance/idempotency/retry |
| GenerationContract | **KEEP** | provider-neutral semantic generation constraints |
| Stage-15 Agent foundation | **KEEP** | Context/Catalog/Policy/Trace/AgentHarness |
| Stage-16 Planner/Tasks/Skills | **KEEP** | merged D-066 layer 2 orchestration |
| Functional subagents | **KEEP** | merged Stage-17 bounded role specialization |
| Stage-16/17 adversarial assurance | **KEEP** | merged curated verification infrastructure, not runtime authority |
| Stage-18 background execution | **KEEP** | merged bounded lease/fencing/recovery layer from PR #75 |
| Product Truth | **KEEP** | cross-layer verification metadata |
| MCP | **KEEP** | optional capability/tool transport, not product state |
| Desktop Update Service | **FUTURE ACCEPTED** | D-068 maintained installation lifecycle |

## 15. Legacy / migration inventory

- Recipe Registry — **LEGACY**; compatibility/import vocabulary only.
- Product Orchestrator / `uv_studio/orchestration/*` — **MOVE + LEGACY**; extract useful logic into modern authorities.
- `api/project_workflow.py` — **LEGACY + EXTRACT**.
- `/execution-plan` and recipe execution — **LEGACY**.
- Stage 6/8 workspaces and specialized legacy project pages — **LEGACY UI**.
- donor-era pipeline/session/task/model frontend clients — **DELETE LATER** after caller proof.
- VideoClaw backend path injection — **DELETE LATER** after dependency/package proof.
- archived Windows packaging/runtime work — **KEEP AS ENGINEERING REFERENCE**.

Do not confuse legacy `uv_studio/orchestration/*` Product-Orchestrator-era code with bounded Agent orchestration under `uv_studio/agent/`.

While D-070 is active, superseded product-composition paths must not gain new modern callers without a later accepted decision explicitly reversing their legacy status.

## 16. Migration order

Completed:

1. D-064 Production Directions.
2. D-065 shared production semantics authority.
3. Modern Studio identity + ProjectUnitOfWork + Undo/Redo.
4. Stage 13 rich shared Scene/Shot/Take vertical.
5. Stage 14 Model Registry.
6. Stage 14 Job Manager/idempotency/attempts/provenance.
7. Stage 14 GenerationContract + D-069 lineage seam.
8. Stage 14 named generation -> project artifact -> Take -> acceptance -> Timeline.
9. Stage 14 first Product Truth record/proof.
10. **Stage 15 Context Builder + Action Catalog + Policy + Trace + bounded Agent execution.**
11. **Stage 16 Planner + durable Tasks + Skills.**
12. **Stage 17 functional subagents.**
13. **Stage-16/17 curated adversarial-assurance pilot.**
14. **Stage 18 bounded background Agent execution — PR #75 merged.**

Next under D-070:

15. **`architecture-compression-inventory` — exact caller/migration/deletion map, no production behavior change.**
16. bounded retirement/extraction slices proven by that inventory;
17. `micro_drama` golden vertical to project-to-export user-outcome proof where gaps remain.

Only after both D-070 gates are satisfied, resume D-066:

18. evaluation/dependency-aware repair;
19. human takeover/edit/resume;
20. long-form autonomous production;
21. additional direction-domain growth as required;
22. D-068 maintained desktop update implementation/release proof when selected as its own slice.

## 17. Invariants

- one Project Store authority;
- one canonical Timeline;
- shared production identities where concepts truly overlap;
- no RecipeDefinition as new v2 product identity;
- no separate engine/workspace per direction;
- no Agent-only mutation path;
- no second Agent scheduler/task graph/provider authority;
- no duplicate Agent tool/protocol/permission authority;
- meaningful named model choice remains visible;
- remote/non-free execution remains explicit and authorized;
- external/cost-bearing generation is retry/idempotency safe;
- provider-private continuation state is not Project Store truth;
- Agent context/plan/tasks/skills/trace/role/lease outputs are bounded orchestration/inspection state over canonical identities;
- raw lease bearer tokens and reusable authorizations are never portable project state;
- Agent Task/lease history does not replace Generation Job/Attempt provenance;
- background commit authority fails closed on lost ownership, policy/evidence mismatch or stale canonical context;
- existing-project `project.json`, Production/Timeline and freshness-tracked JSON writers share the same cross-runtime project fence as canonical UOW/Generation reservation;
- current docs distinguish merged, active and future work;
- user-visible readiness requires D-067 parity/evidence, not implementation claims alone;
- D-066 layers 5-7 remain deferred until D-070 architecture-compression and golden-vertical gates are satisfied.