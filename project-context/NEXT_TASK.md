# Next Task

Updated: 2026-08-11

## Primary target

Implement **generic authorized MCP `call_tool()` execution plus durable external invocation provenance**.

The execution consent/cost boundary is now a separate product-owned layer. This slice must consume that boundary rather than re-implementing consent inside MCP or Qwen-specific code.

Test the transport against the repository's local fake MCP server first. **Do not make real paid Qwen/DashScope calls in CI.**

## Required implementation

### 1. Generic MCP call transport

Extend the official-SDK stdio client with a bounded `call_tool()` path:

- invoke only an exact tool name supplied by an already-configured `MCPToolBinding`;
- use the profile's bounded process/session timeouts;
- preserve SDK cancellation and cleanup semantics;
- never keep a hidden resident MCP child process after the call;
- keep stderr private in machine-local logs;
- bound serialized request and response sizes;
- normalize successful output into JSON-safe product-owned data;
- surface structured timeout, protocol, tool-error and response-limit failures.

Do not add a generic arbitrary command/tool execution API.

### 2. Exact offer -> binding resolution

Add product-owned execution resolution for `mcp.<binding_id>` offers:

- the offer must map to exactly one configured binding;
- binding capability ID must equal the selected capability;
- binding profile must exist and be enabled;
- the bound tool must still exist in the latest ready discovery snapshot;
- renamed/missing tools fail closed;
- unbound discovered tools remain non-executable.

No fuzzy tool-name remapping.

### 3. Authorization ordering

MCP invocation may start **only after** the existing execution preparation/authorization layer succeeds.

Expected behavior:

- local/free MCP: no consent token required;
- remote/free MCP: explicit `remote_execution` one-shot grant;
- `potentially_paid` / `paid`: explicit `external_cost` grant;
- unknown current price: explicit `unknown_cost` acknowledgement too;
- no local failure -> paid fallback;
- no global reusable paid permission.

### 4. Durable invocation provenance

Persist a small versioned JSON run record beneath the canonical project's `tasks/` directory for every external invocation attempt after authorization.

Minimum non-secret fields:

- schema version;
- `run_id`;
- `project_id`;
- semantic `capability_id`;
- selected `offer_id` / `adapter_id`;
- MCP `profile_id` / exact `tool_name`;
- start/end timestamps;
- authorization fact/scope (never the token itself);
- cost-class + cost-estimate snapshot;
- normalized input digest;
- status (`running`, `succeeded`, `failed`);
- result references/summary when safe;
- structured error class/code when failed.

The record must contain no credential values, authorization tokens, resolved secret environment values or raw stderr.

Write failure provenance too. Use atomic Project Store writes.

### 5. Project-scoped external file inputs

Do not expose arbitrary host filesystem paths.

If a binding accepts project file inputs, the binding/adapter must explicitly own which argument fields are file references and resolve them through `ProjectStore.resolve_project_file(...)` with appropriate allowed roots. If no binding currently needs file translation, keep raw host paths unavailable rather than inventing a generic pass-through.

### 6. Fake MCP fixture

Extend `tests/fixtures/mcp_test_server.py` with deterministic `on_call_tool` handlers covering at least:

- successful echo call;
- delayed call for timeout cleanup;
- explicit tool failure;
- oversized response path.

Keep the existing child-process exit marker so cleanup remains observable.

## Tests / acceptance criteria

The slice is complete only when tests prove:

1. Existing local FFmpeg/local-free behavior remains unchanged.
2. `local_free_first` still never widens to remote or paid MCP offers.
3. Exact bound local/free MCP tool can execute.
4. Remote/free MCP requires the existing remote one-shot authorization.
5. Potentially-paid/unknown-cost MCP requires the existing cost + unknown-cost acknowledgement.
6. A token is consumed before invocation and cannot be replayed.
7. Mutated input cannot reuse authorization.
8. Exact bound tool is called with normalized arguments.
9. Unbound discovered tool cannot execute.
10. Renamed/missing bound tool fails closed.
11. Timeout cancels/cleans up the child and writes failed provenance.
12. MCP tool error writes failed provenance without leaking stderr/secrets.
13. Oversized response is rejected deterministically.
14. Success writes durable provenance under `tasks/`.
15. Provenance contains no secrets or authorization token.
16. Project archive contains provenance (project history) but no in-memory authorization grants.
17. Linux and Windows CI remain green.

## Expected files

Likely changes:

- `uv_studio/mcp/client.py`
- `uv_studio/mcp/manager.py`
- `uv_studio/capabilities/adapters/mcp.py`
- `uv_studio/capabilities/execution.py` or a new external execution/provenance module
- `uv_studio/projects/store.py` (only if a small public atomic JSON task-record method is needed)
- `uv_studio/api/capability_execution.py`
- `tests/fixtures/mcp_test_server.py`
- MCP client/binding tests
- capability execution API tests
- project/archive tests for provenance and token exclusion
- `project-context/PROJECT_STATE.md`
- this file
- architecture decision record if transport/provenance semantics become durable

## Explicit non-goals

- No real Qwen/DashScope call in tests or CI.
- No OpenClaw work in this slice.
- No WSL bridge.
- No provider-specific consent implementation.
- No global paid-provider permission.
- No arbitrary host-path or arbitrary command execution API.
- No Stage 4 workflow expansion until generic MCP execution is proven safe.
