# D-017 — External execution consent is product-owned, exact and one-shot

Status: accepted  
Date: 2026-08-11

## Decision

UV Studio separates offer selection from execution authorization. A selected offer is prepared into a product-owned `ExecutionPreparation` containing the selected locality/cost facts, a cost-estimate state and a digest of the exact normalized input. External/non-free execution proceeds only after the required explicit acknowledgements are converted into a short-lived one-shot authorization grant.

Consent scopes are semantic and provider-neutral:

- `remote_execution` — required when the selected offer is not local;
- `external_cost` — required for `potentially_paid` or `paid` offers;
- `unknown_cost` — additionally required when the current cost estimate is unknown.

Cost estimate state is separate from `CostClass`:

- `known`;
- `bounded`;
- `unknown`;
- `not_applicable`.

`CostClass` continues to describe the offer's commercial behavior (`free`, `potentially_paid`, `paid`). `unknown` is not added as a cost class because lack of a current trustworthy price is an estimation fact, not a new provider charging category.

Current default estimates are deliberately conservative: free offers are `not_applicable`; non-free offers remain `unknown` until a concrete adapter can provide a trustworthy current price or bound. UV Studio must never invent a price.

Authorization grants:

- are cryptographically random opaque tokens;
- live only in process/machine runtime memory;
- are short-lived;
- are one-shot;
- bind to exact `project_id + capability_id + offer_id + selection_policy + normalized input SHA-256`;
- are invalidated by replay, expiry or any mutated execution intent;
- are never stored in `project.json`, task history, exports or project archives.

There is no global reusable "always allow paid" grant and no automatic local-failure fallback into a remote/paid offer.

## Reason

Capability discovery and selection prove availability, not user intent to contact an external service or incur cost. Provider-specific confirmation logic would fragment this boundary and make future MCP, Qwen, OpenClaw and native adapters behave differently. A single product-owned contract keeps cost/consent semantics deterministic and auditable before transport-specific code runs.

Binding authorization to the canonical input digest also prevents a consent token issued for one prompt/tool input from authorizing a changed request.

## Consequences

- Existing free/local execution stays frictionless and backward-compatible.
- Free/remote execution requires explicit remote permission but no payment acknowledgement.
- Potentially-paid/paid execution requires one-shot cost acknowledgement; unknown current price requires a separate explicit unknown-cost acknowledgement.
- External adapters consume the authorization boundary rather than implementing their own consent policy.
- Future provider price estimators plug into `ExecutionCostEstimate` without changing selection or consent semantics.
- Durable run provenance may record that authorization occurred and which scopes were required, but must never persist the token itself.
- Generic MCP `call_tool()` can now be implemented behind this boundary without weakening the existing fail-closed selection model.
