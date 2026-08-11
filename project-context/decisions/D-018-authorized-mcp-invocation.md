# D-018 — MCP invocation is exact, short-lived and provenance-recorded

Status: accepted  
Date: 2026-08-11

## Decision

UV Studio may invoke an MCP tool only through an existing explicit `MCPToolBinding` whose selected offer still matches an unchanged READY discovery snapshot.

Execution order is fixed:

```text
semantic capability
  -> selected CapabilityOffer
  -> ExecutionPreparation
  -> one-shot authorization when required
  -> exact MCP binding resolution
  -> running provenance record
  -> bounded short-lived MCP call_tool session
  -> succeeded/failed provenance record
```

A READY snapshot is bound to a SHA-256 digest of the machine profile and all bindings for that profile. Any profile/binding change requires a new discovery `connect` before invocation. Tool-name remapping is exact only; no fuzzy matching is permitted.

The MCP process is still short-lived. UV Studio opens a bounded official-SDK v2 stdio session for the call and closes it after success, error or timeout. Invocation does not turn discovery into a resident agent runtime.

Current transport limits are product-owned:

- request JSON: at most 1 MiB;
- normalized response JSON: at most 4 MiB;
- startup + call duration bounded by the trusted MCP profile timeouts;
- stderr stays in machine-local MCP logs and is never copied into project provenance.

## Provenance

Every MCP invocation attempt that reaches the adapter after authorization creates a versioned `tasks/run_<id>.json` record before the tool call.

The record contains only non-secret facts:

- project/capability/offer/adapter;
- exact profile/tool binding;
- input SHA-256 digest;
- authorization-required fact and consent scopes, never the token;
- cost class and cost-estimate snapshot;
- start/end timestamps and status;
- on success: response byte count + SHA-256 summary, not raw response;
- on failure: controlled error class/code, not raw provider/tool text or stderr.

Because `tasks/` is canonical project history, these records are included in project archives. Process-local authorization grants are not.

## File argument boundary

Generic MCP execution does not automatically translate project-relative paths into host filesystem paths. Until a binding explicitly declares and owns project-file argument translation, raw absolute POSIX paths, Windows drive paths, UNC paths and `file://` URIs are rejected before MCP invocation.

This is deliberately fail-closed: a future binding-specific mapping must resolve project files through the Project Store and constrain allowed project roots instead of adding a generic host-path pass-through.

## Reason

MCP discovery alone proves neither current tool identity nor user permission to invoke it. Machine configuration can also change after discovery. Exact configuration-digest validation prevents a stale offer from silently calling a renamed or reclassified tool, while product-owned authorization keeps remote/cost consent outside provider-specific adapters.

Durable non-secret run provenance is required because external execution may have cost or side effects and must remain auditable across chats, restarts and project export.

## Consequences

- unbound discovered tools remain non-executable;
- changed profile/binding metadata requires reconnect;
- authorization is consumed before target resolution/invocation;
- remote/paid consent behavior remains the D-017 product contract;
- MCP errors/timeouts/size failures are structured and fail closed;
- no Qwen/DashScope paid call is required to test this architecture;
- the next safe extension is explicit binding-owned project-file input translation for capabilities that genuinely need project media files.
