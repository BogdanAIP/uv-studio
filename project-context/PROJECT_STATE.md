# UV Studio — Project State

Updated: 2026-08-11

## Product

UV Studio (Universal Video Studio) is a local-first desktop video production and editing system built around product-owned projects, recipes and semantic media capabilities. Provider/runtime integrations are optional peer adapters behind the Capability Registry rather than product architecture.

## Active roadmap stage

**Stage 3 — Capability Registry & Adapters**

Active development branch: `stage-3/execution-consent-boundary`  
Base `main`: `4108db23f7de67293a53d1005a119a015539c0aa` (merged PR #12, optional pinned Qwen-MM pack).

## Current architecture

```text
Canonical Project
  -> RecipeDefinition / ProductionPolicy
  -> RecipeExecutionPlan
  -> semantic capability IDs
  -> CapabilityRegistry
  -> CapabilityOffer metadata
  -> SelectionPolicy
  -> ExecutionPreparation (locality + cost snapshot + exact input digest)
  -> one-shot ExecutionAuthorization when required
  -> execution adapter
```

Machine-global MCP configuration remains separate:

```text
MCPProfile
  -> bounded stdio discovery
  -> MCPToolDescriptor
  -> explicit MCPToolBinding
  -> CapabilityOffer
```

Discovery/availability is still not execution permission.

## What works on this branch

- Canonical file-first Project Store and project archives.
- Provider-neutral recipes, production policies and truthful execution plans.
- Semantic Capability Registry with explicit adapter offers.
- Fail-closed `manual`, `pinned_offer` and `local_free_first` selection.
- Project-scoped bounded local FFmpeg execution.
- Generic official MCP SDK v2 stdio discovery with explicit bindings; discovery does not invoke tools.
- Optional pinned Qwen-MM profile/binding pack at upstream SHA `7dfc08b7de8e621fc28bf9814e3d41a59b4595ae`.
- Product-owned execution authorization/cost boundary:
  - cost estimate states: `known`, `bounded`, `unknown`, `not_applicable`;
  - current free offers report `not_applicable`; non-free offers stay `unknown` until an adapter provides a real current estimate;
  - remote/free requires `remote_execution` acknowledgement;
  - `potentially_paid` / `paid` require `external_cost`; unknown price additionally requires `unknown_cost`;
  - authorization grants are random, process-local, short-lived and one-shot;
  - grants are bound to exact project + capability + offer + selection policy + canonical JSON input digest;
  - mutated input, replayed tokens and expired tokens fail closed;
  - tokens are not written into project state or archives.
- Capability execution API now supports a two-step safety boundary:
  - `prepare-execution` returns selected offer plus structured authorization/cost facts;
  - `authorize-execution` issues the one-shot grant only after every required acknowledgement;
  - existing `execute` remains backward-compatible for local/free offers and consumes authorization before any non-local/non-free execution path can proceed.

## What is intentionally not implemented yet

- Generic MCP `call_tool()` execution.
- Durable per-run external invocation provenance under Project Store `tasks/`.
- MCP binding-specific project file argument translation.
- Qwen/DashScope cloud invocation.
- WSL bridge for the optional Qwen pack on Windows.
- OpenClaw adapter/runtime integration.
- Stage 4 production workflows.

External offers can now pass selection and authorization, but still stop with `adapter_not_executable_yet` until their transport adapter is implemented.

## Permanent rules

- Capability metadata and discovery never grant execution permission.
- Open-source licensing never implies free provider execution.
- No local failure may silently widen into remote or paid execution.
- There is no global "always allow paid" switch.
- Unknown price is a first-class state and requires explicit acknowledgement; UV Studio does not invent provider prices.
- One-shot authorization is machine/runtime state, never portable project state.
- Machine commands and credential references remain outside portable project state.
- Qwen-MM and OpenClaw are optional peers, not mandatory architecture.
- Native Windows remains a first-class baseline and must not require WSL2.

## Verification state

The new Python module, API replacement and tests were syntax-parsed before committing. Full repository tests cannot be executed in the ChatGPT container because outbound GitHub cloning is unavailable there; GitHub Actions on the PR is the authoritative full verification for this slice.

Coverage added for:

- local/free execution unchanged;
- free/remote permission boundary;
- potentially-paid/unknown-cost consent scopes;
- missing acknowledgement rejection;
- exact normalized input binding;
- one-shot replay rejection;
- expiry;
- structured API `consent_required` / `authorization_invalid` behavior.

## Architectural risks remaining

1. MCP invocation must resolve only the exact configured binding/tool; discovery must never become fuzzy execution.
2. MCP request/response size, timeout, cancellation and stderr handling still need bounded transport behavior.
3. External invocation provenance must record durable non-secret facts for both success and failure.
4. Provider cost estimation must stay adapter-owned and current; unknown must remain unknown when reliable pricing is unavailable.
5. Project file arguments need explicit binding-owned mapping before external tools can receive filesystem paths.

## Next primary target

Implement **generic authorized MCP `call_tool()` execution plus durable external run provenance**, tested first against the local fake MCP server. Do not invoke real Qwen/DashScope paid services in CI.
