# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/direct-mcp-adapter`  
**Main baseline:** `4cbe383f3c30971b3cc006dc71ed8ea30b68e2a6`  
**Branch status:** generic direct MCP stdio discovery + explicit semantic bindings implemented; final PR-specific CI required before merge.

## Product definition

UV Studio is a universal video production/editing studio. Project state, recipes, production policy, semantic capabilities, implementation offers, selection permission and adapter execution remain separate layers. Paid AI APIs are optional capabilities rather than hidden baseline dependencies.

## Current architecture

```text
Canonical Project
  -> RecipeDefinition
      -> ProductionPolicy
      -> RecipeExecutionPlan
          -> semantic capability IDs
              -> CapabilityRegistry
                  -> CapabilityOffer metadata
                      -> SelectionPolicy
                          -> Execution Adapter

Machine Studio Config
  -> MCPProfile
      -> bounded stdio discovery
          -> MCPToolDescriptor
              -> explicit MCPToolBinding
                  -> CapabilityOffer
```

Permanent rules:

- metadata/discovery is not execution permission;
- unbound MCP tools never become UV Studio semantic offers;
- MCP profile licensing does not imply tool execution is free;
- machine commands/credential references are not portable project state.

## Merged milestones

- `af24ed11...` — reproducible VideoClaw baseline;
- `8d175c25...` — UV Studio launcher + HTTP smoke;
- `2276a854...` — canonical Project Store v1;
- `21016061...` — UV server + Projects API;
- `9570658d...` — UV-owned frontend + Projects UI;
- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan and project readiness UI;
- `7fb0ca88...` — semantic Capability Registry + explicit offer readiness/locality/cost;
- `4cbe383f3c30971b3cc006dc71ed8ea30b68e2a6` — fail-closed selection policy + safe project-scoped local FFprobe/FFmpeg execution.

## Current Stage 3 slice — generic direct MCP discovery

### Official MCP SDK v2

Added UV Studio-owned dependency:

```text
requirements-uv.txt
mcp>=2.0,<3
```

It is installed separately from vendored VideoClaw dependencies in CI and `scripts/setup-dev.ps1`.

### Machine-global MCP configuration

Added strict/versioned:

- `MCPProfile`;
- `MCPToolBinding`;
- `MCPConfiguration`;
- `MCPConfigStore`.

Configuration lives under `UV_STUDIO_CONFIG_DIR` or `data/config`, not in Project Store.

Profiles store environment-variable references, not raw secret values. There is intentionally no HTTP API for arbitrary `command + args` profile creation/editing.

### Ephemeral bounded stdio discovery

`MCPStdioDiscoveryClient` uses official SDK `Client` + `stdio_client`.

Flow:

1. resolve configured env references and optional cwd;
2. start the configured stdio server;
3. initialize MCP;
4. call `list_tools()` only;
5. normalize bounded metadata;
6. close SDK contexts and subprocess;
7. keep only discovery status/snapshot in UV Studio memory.

`ready` therefore means the last discovery succeeded; it does not mean a hidden MCP process stays resident.

Tool-list request timeout uses the SDK's own `read_timeout_seconds` cancellation path. UV Studio domain errors are raised only after SDK cleanup completes, avoiding AnyIO task-group/cancel-scope corruption. A coarse whole-session timeout remains as fail-safe.

Limits include:

- max 500 tools/profile;
- bounded names/descriptions;
- max 64 KiB per input/output schema;
- duplicate tool names reject discovery.

Child stderr is written only to machine-local MCP logs and is not returned by public APIs.

### Explicit binding -> semantic offer

`MCPBindingOfferAdapter` registers:

```text
adapter_id = mcp.<profile_id>
offer_id   = mcp.<binding_id>
```

Only explicit `MCPToolBinding` can create an offer. The binding must reference an existing UV Studio semantic capability and explicitly declares locality/cost/asynchronous/features.

Consequences:

- discovered but unbound tool -> visible in tool discovery only, no offer;
- bound + reported tool -> available offer;
- bound but missing tool -> unavailable offer;
- disconnect -> ready snapshot cleared and bound offers marked unavailable;
- remote/potentially-paid MCP offer cannot pass `local_free_first`.

### MCP API

Added discovery/management API:

```text
GET  /api/uv/mcp/profiles
GET  /api/uv/mcp/bindings
GET  /api/uv/mcp/profiles/{profile_id}/status
POST /api/uv/mcp/profiles/{profile_id}/connect
GET  /api/uv/mcp/profiles/{profile_id}/tools
POST /api/uv/mcp/profiles/{profile_id}/disconnect
```

There is no MCP tool-call endpoint and no arbitrary profile-command creation endpoint in this slice.

### Capability Registry runtime refresh

Added `upsert_adapter()` / `upsert_offer()` so ephemeral discovery can refresh MCP availability without redefining semantic capabilities.

This refresh remains metadata only and does not bypass D-014 selection/execution permission.

### Tests

Real official-SDK stdio fixture tests cover:

- initialize/list-tools success;
- timeout/cancellation;
- subprocess cleanup after success/timeout;
- missing command/environment;
- secret-free machine config/API;
- no arbitrary profile creation API;
- explicit binding requirement;
- unbound tool never becoming an offer;
- missing bound tool unavailable;
- disconnect invalidating offers;
- remote potentially-paid MCP offer blocked by `local_free_first`;
- Windows and Linux stdio behavior.

Documentation: `docs/architecture/MCP_ADAPTER.md`. Decision: D-015.

## Verification status

Functional head: `5ab7b0f321d8b4dfc023ec171c27393c167e920e`, CI run `31469785841`.

Observed on that exact head:

- Ubuntu bootstrap/unit: success;
- Windows bootstrap/unit: success;
- Ubuntu API integration: success;
- Windows API integration: success;
- Ubuntu real HTTP smoke: success;
- Windows real HTTP smoke: success;
- Ubuntu frontend production build: success;
- Windows frontend production build: success.

This context update creates a newer docs-only head. Merge still requires PR-specific CI on the actual PR head.

## What works now

- durable project/recovery/UI foundation;
- provider-neutral recipes/policies/execution planning;
- semantic Capability Registry;
- fail-closed selection permission;
- safe local deterministic execution;
- generic direct MCP stdio discovery through official SDK;
- machine-global secret-reference configuration;
- explicit MCP semantic bindings;
- runtime MCP offer availability refresh;
- cross-platform real stdio tests;
- no paid API required by baseline startup/discovery.

## Not implemented yet

- MCP tool invocation;
- Qwen-MM optional profile/binding pack;
- OpenClaw runtime adapter;
- remote/paid-provider execution consent/cost confirmation;
- persistent MCP process pooling;
- Streamable HTTP MCP transport;
- trusted desktop UI for MCP profile editing;
- generic general-video executor;
- range edit/dubbing/music workflows.

## Current invariants

1. Recipe semantics never name provider/runtime.
2. Discovery/offer metadata never equals execution permission.
3. `local_free_first` cannot widen to remote/paid-capable offers.
4. MCP profiles are machine config, not portable projects.
5. Raw secret values are not persisted or returned by MCP APIs.
6. No arbitrary profile command creation endpoint exists.
7. Discovery invokes `list_tools()` only; no MCP tool is called.
8. Discovered tools require explicit semantic binding.
9. Qwen-MM/OpenClaw remain optional peers.
10. Native Windows works with no Qwen/OpenClaw/WSL dependency.

## Next slice

After this PR is merged, re-verify the then-current `QwenLM/Qwen-MM-Plugins` repository and add a separate **optional Qwen-MM profile/binding pack**. Classify each useful tool by actual locality/cost and platform requirements. Do not enable cloud/paid MCP tool execution yet. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
