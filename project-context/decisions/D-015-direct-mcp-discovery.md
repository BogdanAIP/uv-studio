# D-015 — Direct MCP discovery is generic, explicit and non-executing

**Status:** accepted  
**Date:** 2026-08-11

## Decision

UV Studio uses the official Model Context Protocol Python SDK v2 as a product-owned transport dependency for generic direct MCP integration.

The first MCP layer is discovery-only:

```text
machine MCP profile
  -> bounded stdio discovery
  -> normalized tool descriptor
  -> explicit MCPToolBinding
  -> semantic CapabilityOffer
```

A discovered tool never becomes a UV Studio semantic capability or executable operation automatically.

## Machine configuration boundary

MCP profiles are machine-global Studio configuration, not canonical project state.

They live under the UV Studio configuration root and are deliberately excluded from portable `.uvproj.zip` projects.

Profiles may contain command/argv, cwd and environment-variable references, but not raw secret values. A profile maps child environment variable names to source host environment variable names; the resolved value is passed only to the child process and never returned by public APIs.

The first slice intentionally exposes no HTTP endpoint for arbitrary profile command creation/editing. Otherwise the product API would become a generic host process-execution surface.

## Transport and lifecycle

The initial transport is stdio only.

Discovery is ephemeral:

1. start configured server through the official SDK;
2. initialize MCP;
3. invoke `list_tools()` only;
4. normalize bounded tool metadata;
5. close SDK contexts and child process;
6. retain only the in-process discovery snapshot/status.

`ready` means the latest discovery succeeded; it does not mean a hidden child process remains running.

The implementation uses the MCP SDK's own per-request timeout/cancellation support and raises UV Studio domain errors only after SDK cleanup completes. A separate coarse whole-session timeout remains as a fail-safe.

## Explicit semantic binding

Provider/server tool names are not canonical UV Studio concepts.

A configured `MCPToolBinding` explicitly maps one server tool to one already-known semantic `capability_id` and records:

- locality;
- cost class;
- async behavior;
- feature tags.

Only bound tools create `CapabilityOffer` entries.

Unbound discovered tools are visible in discovery metadata but do not become offers. Bound tools not reported by the server become unavailable offers.

## Cost and permission

MCP package licensing does not determine operation cost.

An open-source MCP server may expose both local/free operations and paid cloud operations. Each binding classifies those independently.

D-014 remains authoritative: discovery and offer availability are not execution permission. In particular, `local_free_first` cannot reinterpret a remote or potentially-paid MCP offer as local/free.

This slice does not implement MCP tool invocation at all.

## Qwen-MM boundary

Qwen-MM-Plugins is not vendored or required by the generic MCP layer.

After this layer is merged, Qwen-MM may be added as a separate optional profile/binding pack against a freshly re-verified upstream revision. Its individual tools must be classified by actual locality/cost/runtime requirements rather than by repository license.

Native Windows UV Studio must continue to work when Qwen-MM is absent or when an optional Qwen setup still requires WSL.

## OpenClaw boundary

Direct MCP does not route through OpenClaw. OpenClaw remains a future optional peer runtime only where its broader orchestration/provider features provide demonstrated value.

## Consequences

1. UV Studio gains a generic MCP seam without coupling recipes/projects to a provider package.
2. Official MCP SDK v2 is installed via UV Studio-owned `requirements-uv.txt`, separate from vendored VideoClaw dependencies.
3. No MCP process is started automatically merely because a profile exists.
4. Discovery calls `list_tools()` only and cannot spend money by invoking a discovered tool.
5. No raw secret value or child stderr is returned by public MCP APIs.
6. No arbitrary command-profile creation API exists in this slice.
7. Tool catalogs/schemas are size-bounded and duplicate names fail discovery.
8. Real stdio discovery, timeout and process cleanup are regression-tested on Linux and Windows.
9. MCP offers reuse the same Capability Registry and D-014 selection rules as local/native offers.
10. Qwen-MM/OpenClaw remain optional adapters rather than architecture prerequisites.
