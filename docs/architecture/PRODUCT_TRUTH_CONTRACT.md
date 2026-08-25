# UV Studio Product Truth Contract

**Status:** CURRENT SUPPORTING TARGET CONTRACT  
**Decision authority:** D-067

## Purpose

A green backend test is not enough to call a user-visible UV Studio feature complete. Product Truth binds the canonical application/backend behavior to the visible product surface and to end-to-end user evidence.

The target verification stack has three layers:

```text
1. Current Documentation Consistency
2. Product Surface Parity
3. User Outcome Proof
```

## 1. Current Documentation Consistency

Machine checks should validate explicit facts rather than attempt fuzzy natural-language understanding.

Required checks grow around stable markers/contracts for:

- `ACTIVE_SLICE.json` lifecycle and PR identity;
- `PROJECT_STATE.md` active/completed markers;
- `NEXT_TASK.md` one next slice;
- architecture authority/ADR references;
- existence of declared current files/contracts;
- completed/active/next state not contradicting each other;
- feature-contract references pointing at real code/tests when a feature is declared ready.

Current docs must label future/target work explicitly. A current document must not describe merged implementation as still future simply because prose was not updated.

## 2. Product Surface Parity

A future machine-readable Product Truth Contract registry will describe each user-visible feature. The exact schema is implementation work, but each contract needs enough identity to answer:

```text
What can the user do?
Where is the canonical command/query?
Where is the backend/API entry?
Where is the frontend entry?
What canonical state/results are involved?
What capabilities/models/jobs/permissions are required?
Which E2E proof demonstrates the user outcome?
```

Representative conceptual record:

```yaml
feature_id: generate-shot-take
user_visible: true
readiness: ready
command: GenerateTake
backend: POST /api/uv/...
frontend: Shot Inspector / Generate
state:
  - project Job/Attempt
  - generated project asset
  - Take candidate
dependencies:
  - named Model
  - Capability execution
  - D-017 authorization when required
e2e:
  - generate-shot-take
```

This record is verification metadata, not a second feature engine or project authority.

### Merge rule

For `user_visible=true` + `readiness=ready` on `main`:

- frontend without a real canonical backend/application path fails parity;
- advertised backend functionality without the required user surface fails parity;
- model/cost/progress/error semantics required by the contract must survive both sides;
- backend-only infrastructure is allowed only when explicitly marked non-user-visible/not-ready.

Draft work may temporarily be asymmetric while hidden or marked not-ready.

## 3. User Outcome Proof

A parity-complete feature must still prove the complete user journey:

```text
visible user action
 -> frontend client
 -> canonical command/query
 -> backend/domain service
 -> canonical/project/runtime state
 -> visible result/progress/failure
```

Where persistence is part of the promise, test reload/restart. Where installation/upgrade is part of the promise, test the packaged application.

## CI direction

The permanent CI shape may initially reuse existing jobs but should converge toward recognizable gates such as:

```text
development-context
architecture-consistency
product-surface-parity
app-baseline / user-outcome
```

The implementation should prefer deterministic reference checking over heuristic prose analysis.

## First required consumer

The next Model Registry / Job Manager / generation slice is the first new major feature that must obey D-067: a user-visible named-model generation path is not complete merely because the backend can create a Job. The Studio UI must expose model selection, job/progress/failure/result state and the E2E proof must drive the real UI through generated Take-candidate creation.
