# D-067 — Product Truth Contract and current-documentation consistency

**Status:** Accepted  
**Date:** 2026-08-25

## Context

UV Studio now has enough independent layers that ordinary unit tests can be green while the product still describes or exposes inconsistent realities. Three failure classes matter:

1. **documentation drift** — current architecture/project-context documents describe work as future although the repository already implements it, or claim implemented behavior that no longer exists;
2. **backend/frontend drift** — a user-visible backend capability exists without a reachable product surface, or the frontend presents a control whose canonical backend/application path is absent, stubbed or incompatible;
3. **layer-local success without user outcome** — backend, frontend and persistence tests pass independently while the complete visible workflow is broken.

Stage 13 exposed the first class directly: its Scene/Shot/Take path had already merged while some current architecture text still described the work as future. The existing D-062 Product Truth Recovery principle is therefore promoted into an explicit forward contract rather than being treated only as historical recovery work.

## Decision

Every user-visible UV Studio capability MUST have one **Product Truth Contract** that binds the intended user surface to the canonical application/backend behavior, persistent state where applicable, execution/permission dependencies and end-to-end proof.

Current project documentation MUST separately distinguish **as-built** state from **target/future** state and MUST be checked against machine-readable repository facts where practical.

These gates are complementary:

```text
Current Documentation Consistency
        +
Product Surface Parity
        +
User Outcome Proof
        =
Product Truth
```

### 1. Product Truth Contract

A Product Truth Contract is a small machine-readable record for one user-visible capability. The exact serialization may evolve, but the semantic fields are:

- stable `feature_id`;
- user-visible title/purpose;
- lifecycle/readiness state;
- canonical application/domain command or query boundary;
- backend/API surface when one exists;
- frontend entry point/control/surface;
- persistent canonical state affected or read, when applicable;
- capability/model/job/permission dependencies, when applicable;
- expected user-visible success/failure/progress states;
- end-to-end proof identifier(s);
- optional direction/tool scope;
- explicit exceptions when a capability is intentionally backend-only infrastructure rather than a user-visible product feature.

A contract does not create a second product registry or runtime authority. It is verification metadata pointing at existing UV-owned authorities.

Representative shape:

```text
feature_id: generate-shot-take
user_visible: true
command: GenerateTake
backend: POST /...
frontend: Shot Inspector -> Generate
state: Job + generated asset + Take candidate
dependencies: named Model + Capability + authorization when required
e2e: generate-shot-take.spec
```

### 2. Product Surface Parity

For `user_visible=true` features on `main`:

- a backend/application capability MUST NOT be advertised as product-ready unless its required frontend surface is reachable;
- a frontend control MUST NOT claim executable readiness unless its canonical command/backend path exists and is actually wired;
- user-significant parameters such as model choice, cost/remote consent and job state must not disappear between backend and frontend;
- hidden/internal infrastructure may exist without a frontend, but it must be declared non-user-visible rather than silently counted as product functionality.

A draft implementation slice may temporarily lead on one side while the feature remains hidden/non-ready. The merge/review gate must close the parity gap for any capability declared user-visible and ready.

### 3. User Outcome Proof

Product Surface Parity is necessary but not sufficient. A user-visible feature is complete only when an end-to-end test or equivalent installed-app evidence proves the intended journey through the real product surface.

The normal proof chain is:

```text
frontend interaction
 -> canonical command/query
 -> backend/domain service
 -> canonical project/runtime state
 -> visible result/error/progress
```

Where persistence matters, proof includes close/reopen or equivalent reload/re-read. Where packaging matters, release proof must run against the packaged application rather than only development servers.

### 4. Current-documentation consistency

`ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, `CURRENT_ARCHITECTURE.md` and the architecture authority index describe current repository reality and handoff. They are not aspirational prose.

CI should progressively verify machine-checkable facts such as:

- lifecycle markers and slice/PR identity agree;
- completed/active/next slice markers agree;
- referenced ADRs/files/contracts exist;
- current authority indexes contain current accepted decisions;
- current documents do not label a completed machine-recorded slice as the next implementation target;
- Product Truth Contracts point at existing commands/routes/frontend entries/tests where those references are declared;
- readiness claims have the required contract/evidence class.

Do **not** build a brittle CI system that tries to semantically understand every English sentence. Natural-language documentation remains human-readable; machine checks rely on explicit markers/registries/contracts and narrow invariants.

### 5. CI shape

The target permanent gates are conceptually:

```text
development-context
architecture-consistency / docs-freshness
product-surface-parity
user-outcome / app-baseline
```

They may initially share one validator/job and later separate as the contract registry grows.

## Consequences

- Backend and frontend may be developed independently inside a draft slice, but a user-visible feature cannot merge as ready with one side missing.
- Documentation drift becomes a detectable product defect rather than a cosmetic cleanup item.
- E2E tests become evidence attached to named capabilities instead of a loose pile of scenarios.
- Future Model Registry, Job Manager and Agent work must expose truthful UI state and product evidence rather than count backend contracts alone as completion.
- Agent/MCP-only surfaces can remain valid where explicitly scoped, but they do not masquerade as user-visible desktop features.

## Relationship to earlier decisions

- D-062 remains historical recovery rationale; D-067 is the forward verification contract that carries its Product Truth principle into current development.
- D-038 lifecycle validation remains authoritative for active development state; D-067 extends consistency beyond lifecycle metadata into current docs and product surfaces.
- D-064/D-065 continue to own product composition and production semantics.
- D-066 future Agent Harness work must use the same Product Truth Contracts when it exposes user-visible automation.
