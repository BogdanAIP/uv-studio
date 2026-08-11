# UV Studio Direct MCP Adapter

## Purpose

UV Studio connects MCP packages as optional capability sources without making any one MCP server, Qwen-MM-Plugins, OpenClaw or cloud account part of canonical project state.

The first MCP slice is deliberately **discovery-only**:

```text
machine MCP profile
  -> bounded stdio discovery
  -> normalized tool descriptors
  -> explicit MCPToolBinding
  -> semantic CapabilityOffer
```

Discovering a tool does not execute it and does not authorize paid work.

## Official SDK

UV Studio uses the official Model Context Protocol Python SDK v2 (`mcp>=2,<3`) as a UV Studio-owned dependency in `requirements-uv.txt`.

The dependency is separate from `vendor/videoclaw-app/backend/requirements.txt`; the vendored VideoClaw snapshot remains an upstream compatibility boundary.

## Machine configuration, not project state

MCP profiles live under the UV Studio configuration root (`UV_STUDIO_CONFIG_DIR` or `data/config`). They are not stored in `project.json` and are not part of `.uvproj.zip`.

A profile contains:

- stable `profile_id`;
- title;
- `stdio` transport;
- command + argv;
- optional working directory;
- environment-variable **references**;
- enabled flag;
- bounded startup/discovery timeouts.

Raw secret values are not a valid profile field. Environment mapping is expressed as:

```json
{
  "env_refs": {
    "CHILD_TOKEN": "UV_STUDIO_QWEN_TOKEN"
  }
}
```

At connection time UV Studio reads the named host environment variable and passes its value only to the child process. Public profile APIs return the reference name, not the value.

## No arbitrary command configuration API

This slice intentionally has no HTTP endpoint that creates or edits an MCP profile command.

Allowing an arbitrary local HTTP caller to submit `command + args` would create a general host process-execution surface. Profiles are trusted machine configuration; future desktop settings UI must use a privileged local configuration path rather than a generic remote command endpoint.

## Bounded ephemeral stdio discovery

`MCPStdioDiscoveryClient`:

1. resolves referenced environment variables;
2. validates optional working directory;
3. starts the configured server with the official SDK stdio transport;
4. initializes the MCP client;
5. calls `list_tools()` only;
6. normalizes bounded tool metadata;
7. exits the SDK contexts and terminates the child process tree;
8. captures child stderr to a machine-local log file that is never returned by the public API.

`ready` therefore means **the latest bounded discovery succeeded**. It does not mean UV Studio keeps a hidden MCP child process resident.

Startup and tool discovery have independent timeouts. The implementation uses AnyIO cancel scopes in the same task as the SDK context because MCP SDK task groups must be exited from the task that entered them.

## Tool metadata limits

Discovery is intentionally bounded:

- maximum 500 tools per profile;
- tool names/titles/descriptions have length limits;
- input/output JSON schemas are limited to 64 KiB each;
- duplicate tool names fail discovery.

A server cannot turn an unbounded tool catalog into application/API memory growth.

## Explicit semantic binding

MCP tool names are provider/package-specific and never become UV Studio domain semantics automatically.

A configured binding declares:

```text
binding_id
profile_id
tool_name
capability_id
title
locality
cost_class
asynchronous
features
```

Only a binding can create an MCP `CapabilityOffer`.

If a server reports an unbound tool, UV Studio exposes it in the profile's discovered-tools view but does **not** create a semantic offer for it.

If a binding references a tool that the server does not report, its offer is `unavailable`.

## Cost/locality are binding facts

The license of the MCP package does not determine operation cost.

For example, one open-source server can expose both:

```text
local transcription   -> local + free
cloud video generation -> remote + potentially_paid
```

Those become different offers. Existing D-014 rules still apply: `local_free_first` cannot widen to a remote or paid-capable MCP offer.

## Capability Registry integration

Each configured profile uses an adapter ID:

```text
mcp.<profile_id>
```

Each binding uses an offer ID:

```text
mcp.<binding_id>
```

Successful discovery marks a bound/present tool's offer `available`. Disconnecting clears the ready discovery snapshot and marks bound offers unavailable.

Registry `upsert_adapter()` / `upsert_offer()` exist only to refresh runtime discovery metadata; they do not authorize tool execution.

## API

Read/discovery endpoints:

```text
GET  /api/uv/mcp/profiles
GET  /api/uv/mcp/bindings
GET  /api/uv/mcp/profiles/{profile_id}/status
POST /api/uv/mcp/profiles/{profile_id}/connect
GET  /api/uv/mcp/profiles/{profile_id}/tools
POST /api/uv/mcp/profiles/{profile_id}/disconnect
```

There is intentionally no MCP tool-call endpoint in this slice.

## Qwen-MM-Plugins boundary

Qwen-MM-Plugins is **not installed, vendored or required** by the generic MCP layer.

After this generic layer is green, Qwen-MM can be added as a separate optional profile/binding pack against a re-verified pinned upstream revision.

The binding pack must classify each relevant tool independently:

- actual local/free operations as local/free when verified;
- remote DashScope/Qwen/Wan/Omni calls as configuration-dependent and potentially-paid/paid;
- WSL-only requirements, if still present at integration time, as optional platform constraints rather than native Windows prerequisites.

## OpenClaw boundary

OpenClaw remains a separate optional runtime adapter. Direct MCP does not route through OpenClaw, and OpenClaw is not required to connect Qwen-MM or other MCP servers.

## Not implemented yet

- MCP tool execution;
- persistent MCP process pooling;
- Streamable HTTP transport;
- API/profile editor for arbitrary local commands;
- Qwen-MM profile/bindings;
- DashScope calls;
- paid-provider consent/cost confirmation;
- automatic semantic inference from discovered tool names.

## Security invariants

1. No MCP server is launched at UV Studio startup just because a profile exists.
2. Discovery invokes `list_tools()` only; it never calls discovered tools.
3. Profiles store env references, not secret values.
4. Public APIs never return resolved secret values or child stderr.
5. No arbitrary profile-command creation endpoint exists.
6. MCP subprocesses use official SDK stdio argv handling, not shell interpolation.
7. Discovery subprocesses are ephemeral and cleaned up after success, timeout or failure.
8. Unbound tools never become semantic capabilities/offers.
9. Offer locality/cost remain explicit binding metadata.
10. D-014 execution-permission rules remain unchanged.
