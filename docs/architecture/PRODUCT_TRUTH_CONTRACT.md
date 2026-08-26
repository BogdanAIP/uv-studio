# UV Studio Product Truth Contract

**Status:** CURRENT SUPPORTING CONTRACT  
**Decision authority:** D-067

## Purpose

A green backend test is not enough to call a user-visible UV Studio feature complete. Product Truth binds canonical application/backend behavior to the visible product surface and to end-to-end user evidence.

The verification stack has three layers:

```text
1. Current Documentation Consistency
2. Product Surface Parity
3. User Outcome Proof
```

## 1. Current Documentation Consistency

Machine checks validate explicit facts rather than attempt fuzzy natural-language understanding.

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

Machine-readable Product Truth records live under:

```text
docs/architecture/product-truth/*.json
```

Schema-v1 reference validation is implemented by `uv_studio/product_truth.py` and exercised by the permanent unit-test suite. This is deterministic reference checking, not Markdown/NLP interpretation.

Each user-visible ready record identifies:

- stable `feature_id`, title, visibility and readiness;
- canonical domain class/method;
- backend source/function plus exact HTTP method and route;
- frontend source/symbol, exact Next route mount-chain and declared visible controls;
- canonical state/results involved;
- capability/model/job/authorization/transaction dependencies;
- visible progress/failure/result states;
- browser E2E and API integration proof identifiers;
- conditional availability facts when execution depends on a configured offer.

Representative shape:

```json
{
  "schema_version": 1,
  "feature_id": "generate-shot-take",
  "title": "Named generation",
  "user_visible": true,
  "readiness": "ready",
  "canonical": {
    "domain": {"path": "uv_studio/generation/service.py", "class": "GenerationService", "method": "submit"},
    "backend": {"path": "uv_studio/api/generation.py", "function": "submit_generation", "http_method": "POST", "route": "/api/uv/..."},
    "frontend": {
      "path": "frontend/components/editor/GenerationWorkspacePanel.tsx",
      "symbol": "GenerationWorkspacePanel",
      "route": "/projects/{project_id}/studio",
      "mount_chain": [
        {"path": "frontend/app/projects/[projectId]/studio/page.tsx", "symbol": "StudioProjectPage"},
        {"path": "frontend/components/editor/StudioProjectWorkspace.tsx", "symbol": "StudioProjectWorkspace"},
        {"path": "frontend/components/editor/ProductionWorkspacePanel.tsx", "symbol": "ProductionWorkspacePanel"},
        {"path": "frontend/components/editor/GenerationWorkspacePanel.tsx", "symbol": "GenerationWorkspacePanel"}
      ],
      "controls": ["Модель генерации"]
    },
    "state": ["project Job/Attempt", "generated project artifact", "Take candidate"]
  },
  "dependencies": [
    {"name": "model_registry", "path": "uv_studio/generation/models.py", "symbol": "ModelRegistry"}
  ],
  "visible_states": ["model_choice", "queued", "running", "succeeded", "failed", "cancelled", "take_candidate"],
  "availability": {
    "requires_available_offer": true,
    "default_behavior": "configuration-dependent",
    "proof_transport": "bounded test transport"
  },
  "evidence": {
    "browser_e2e": {"path": "e2e/test_feature_outcome.py", "class": "FeatureBrowserOutcome", "test": "test_visible_feature_outcome"},
    "api_integration": {"path": "tests_api/test_feature_api.py", "class": "FeatureApiTests", "test": "test_feature_api_outcome"}
  }
}
```

The record is verification metadata, not a second feature engine or project authority.

For the frontend, validation does more than check that the final component file exists. The first `mount_chain` entry must be the declared Next `frontend/app/**/page.*` route, its dynamic segments must match the declared product route, every chain element must declare a real component/function symbol, each parent must reference the next symbol, and the chain must terminate at the declared product surface. Deleting or disconnecting the page therefore fails Product Truth even if the leaf component file survives.

### Merge rule

For `user_visible=true` + `readiness=ready` on `main`:

- frontend without a real canonical backend/application path fails parity;
- advertised backend functionality without the required user surface fails parity;
- declared source symbols/routes/mount-chain/controls/evidence that no longer resolve fail validation;
- model/cost/progress/error semantics required by the contract must survive both sides;
- backend-only infrastructure is allowed only when explicitly marked non-user-visible/not-ready.

Draft work may temporarily be asymmetric while hidden or marked not-ready.

Conditional model availability does not by itself make the product contract false. A named model whose selected offer is `configuration_required` or unavailable must stay visibly blocked with its reason; successful execution requires an available offer and normal D-017 authorization. Test-only proof transports must be explicitly gated and absent from the normal product catalog.

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

## CI shape

The permanent CI currently reuses the five established jobs. Product Truth registry validation runs in the normal Python unit-test suite, while the declared browser outcome is exercised by both `app-baseline` jobs after frontend build.

The long-term gate names may become more explicit, but the verification principle stays the same: deterministic contract/reference checks plus real user-outcome tests rather than heuristic prose analysis.

## First implemented consumer

Stage 14 named-model generation is the first implemented D-067 consumer. Its contract is:

```text
docs/architecture/product-truth/generate-shot-take.json
```

The record binds the visible Studio model/Shot/prompt controls to `GenerationService.submit`, the generation Job API, the real Next Studio mount-chain, durable Job/Attempt + generated-artifact + Take-candidate state, the shared acceptance/Timeline authorities and the browser/API evidence that proves the path.

D-069 continuation lineage is intentionally not marked as a separate ready user-visible feature in Stage 14: no real continuation-capable offer or Continue/Edit UI is shipped yet.
