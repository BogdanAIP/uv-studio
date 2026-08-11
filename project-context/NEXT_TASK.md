# Next Task

**Primary target:** continue Stage 3 with provider-neutral **direct MCP adapter infrastructure**. Do not make Qwen-MM, OpenClaw, WSL2 or any paid provider mandatory.

## Why this comes next

UV Studio now has the full local safety chain:

```text
CapabilityDefinition
  -> CapabilityOffer
      -> SelectionPolicy
          -> Execution Adapter
```

and a proven local executor for `media.probe` / `timeline.assemble`.

The next missing seam is a generic way to connect external MCP capability packages without hard-coding one vendor into RecipeDefinition, Project Store or the execution API.

Qwen-MM-Plugins is an important intended consumer of this seam, but the MCP layer must be generic enough for other servers as well.

## First direct-MCP slice

### 1. Define MCP connection profile metadata

Add a product-owned, versioned profile model containing only safe configuration metadata, for example:

```text
profile_id
transport
command + argv        # stdio only when explicitly configured
working_directory     # optional, validated
safe environment variable names / secret references
server identity
status
```

Do not store raw secret values in public registry/API responses.

Start with one transport only if that keeps the implementation reliable. Prefer a narrow, well-tested stdio MCP path before adding multiple transports.

### 2. Separate MCP server discovery from semantic mapping

A connected MCP server exposes tools with provider/tool-specific names.

Do not make those names canonical UV Studio capabilities.

Add an explicit mapping layer:

```text
MCP tool descriptor
  -> MCP capability binding
      -> semantic capability_id
      -> CapabilityOffer
```

Bindings should be explicit/testable rather than inferred from fuzzy names at execution time.

### 3. Add lifecycle boundary

Implement a small MCP client/manager with clear lifecycle:

```text
configured
starting
ready
failed
stopped
```

Requirements:

- bounded startup timeout;
- bounded tool-call timeout;
- stderr captured safely;
- process termination on shutdown/failure;
- no orphan process after a failed start;
- no shell command interpolation;
- native Windows path/process behavior covered;
- optional server absence must not prevent UV Studio startup.

Do not build a general agent runtime. This is a capability transport adapter only.

### 4. Read-only discovery first

Before executing tools, support:

- connect/start configured MCP server;
- initialize protocol;
- list tools;
- expose safe normalized tool metadata;
- health/status;
- disconnect/stop.

Discovery must not invoke paid model tools.

### 5. Register MCP offers explicitly

Only mapped tools become `CapabilityOffer` values.

An MCP package being installed does not imply every tool is free or executable.

Each binding must preserve explicit metadata:

```text
availability
locality
cost_class
asynchronous
features
```

For Qwen-MM later:

- local/core file operations may be free/local or free/hybrid as actually verified;
- DashScope/Qwen/Wan/Omni calls remain potentially-paid/paid and configuration-dependent;
- licensing of the plugin package does not determine execution cost.

### 6. Keep paid execution disabled

This slice should support discovery and registration first.

If tool execution is added, initially permit only bindings explicitly marked safe under the current permission rules. Do not let MCP discovery bypass `SelectionPolicy` or D-014.

No automatic `local_free_first` fallback to a remote MCP service.

### 7. API

Add safe management/discovery endpoints, e.g.:

```text
GET  /api/uv/mcp/profiles
POST /api/uv/mcp/profiles/{profile_id}/connect
GET  /api/uv/mcp/profiles/{profile_id}/status
GET  /api/uv/mcp/profiles/{profile_id}/tools
POST /api/uv/mcp/profiles/{profile_id}/disconnect
```

Exact shape may change if a smaller surface is cleaner.

Do not expose raw environment secrets, process handles or unrestricted command execution.

### 8. Persistence

Connection profiles should use UV Studio-owned configuration/state, not canonical project documents unless there is a concrete project-specific reason.

Project archives must not accidentally contain machine credentials.

### 9. Tests

Use a tiny local fake MCP server/fixture to test the protocol without network/API credentials.

Cover at least:

- startup/init/list-tools success;
- malformed handshake;
- startup timeout;
- tool-list timeout;
- child process cleanup after failure;
- explicit disconnect;
- duplicate/invalid profile IDs;
- public API contains no raw secret values;
- semantic binding required before offer registration;
- `local_free_first` cannot treat remote/potentially-paid MCP offer as local/free;
- Windows-compatible stdio process launch;
- UV Studio starts normally when no MCP profiles are configured.

## Qwen-MM boundary

Do **not** vendor or require Qwen-MM-Plugins in the generic MCP slice.

After the generic client is stable, add Qwen-MM as a separate optional adapter/profile pack and verify its then-current repository contracts before binding tools.

Important:

- Qwen-MM cloud operations may require paid DashScope access;
- its Windows/WSL support may change, so re-verify at integration time;
- native Windows UV Studio must continue to work with Qwen-MM absent;
- reuse workflow ideas independently from runtime integration where useful.

## OpenClaw boundary

Do not connect OpenClaw in this slice.

OpenClaw remains a future peer runtime adapter only if its broader orchestration/provider features provide concrete value that direct MCP/local execution does not.

## What NOT to build

- generic agent orchestration;
- autonomous provider purchasing;
- mandatory cloud accounts;
- a second project database;
- arbitrary user shell execution;
- full MCP marketplace/package manager;
- Qwen-specific semantics inside RecipeDefinition;
- automatic conversion of every discovered tool into a semantic capability.

## Suggested files

```text
uv_studio/mcp/models.py
uv_studio/mcp/store.py
uv_studio/mcp/client.py
uv_studio/mcp/manager.py
uv_studio/mcp/bindings.py
uv_studio/capabilities/adapters/mcp.py
uv_studio/api/mcp.py

tests/test_mcp_models.py
tests/test_mcp_client.py
tests/test_mcp_bindings.py
tests_api/test_mcp_api.py

tests/fixtures/mcp_test_server.py

docs/architecture/MCP_ADAPTER.md
```

## Acceptance criteria

- UV Studio starts with zero MCP configuration;
- one local fake MCP server can be started, initialized, queried and stopped cross-platform;
- no shell interpolation is used;
- failed starts/calls leave no orphan child process;
- tool discovery does not invoke tools;
- semantic capability mapping is explicit;
- MCP offer cost/locality/readiness remains explicit;
- no raw secrets appear in APIs or project archives;
- Qwen/OpenClaw remain optional and absent from baseline startup;
- Linux + Windows unit/API/HTTP/frontend CI remains green.

After that, add a separate **optional Qwen-MM profile/binding pack** against a re-verified pinned Qwen-MM-Plugins revision, starting with useful free/local capabilities before any cloud/paid tools.
