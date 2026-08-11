# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/mcp-call-tool`  
**Main baseline:** `416677c4ca758a01b0253c8880b44d44150a8cec`  
**Open PR:** #14 — authorized MCP `call_tool()` execution and provenance  
**Branch status:** implementation and tests complete; final Linux/Windows CI for the documentation-updated head is required before merge.

## Product architecture

```text
Canonical Project
  -> RecipeDefinition / ProductionPolicy
  -> RecipeExecutionPlan
  -> semantic capability IDs
  -> CapabilityRegistry
  -> CapabilityOffer
  -> SelectionPolicy
  -> ExecutionPreparation
  -> one-shot authorization when required
  -> exact execution adapter
      -> local bounded FFmpeg
      -> exact MCP binding
          -> running tasks/run_<id>.json
          -> bounded short-lived call_tool()
          -> succeeded/failed provenance

Machine Studio Config
  -> MCPProfile
  -> bounded stdio discovery
  -> MCPToolDescriptor
  -> explicit MCPToolBinding
  -> CapabilityOffer
```

Permanent rules:

- discovery/availability is not execution permission;
- open-source repository license does not imply cloud execution is free;
- local failure never silently widens into remote or paid execution;
- machine commands/credential references are not portable project state;
- Qwen-MM and OpenClaw remain optional peer integrations;
- native Windows remains a first-class baseline and must not require WSL2;
- authorization tokens are runtime state, never portable project state.

## Merged milestones

- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan;
- `7fb0ca88...` — semantic Capability Registry;
- `4cbe383f...` — fail-closed selection + safe local FFprobe/FFmpeg execution;
- `3e2b60329f7b8aa22fec38c012d703e3a8cca26d` — official-SDK direct MCP stdio discovery + explicit semantic bindings;
- `4108db23f7de67293a53d1005a119a015539c0aa` — optional pinned Qwen-MM profile/binding pack (PR #12);
- `416677c4ca758a01b0253c8880b44d44150a8cec` — execution consent/cost boundary (PR #13).

## Stable Stage 3 context — optional Qwen-MM pack

Verified upstream reference used by UV Studio:

```text
QwenLM/Qwen-MM-Plugins
commit: 7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
license: Apache-2.0
```

Trusted optional packs remain independent:

```text
core
api
video-edit
```

Profiles use fixed trusted `uvx --from <exact SHA> <entrypoint>` templates. UV Studio does not install or launch Qwen during ordinary startup, and generic arbitrary profile-command creation is absent.

Important current classifications:

```text
core.media_info -> media.probe
  locality = local
  cost     = free

Qwen/DashScope understanding + ASR
  locality = remote
  cost     = potentially_paid

qwen_image -> image.generate
qwen_tts   -> speech.synthesize
wan_t2v    -> video.generate
wan_s2v    -> video.digital_human
  locality = remote
  cost     = potentially_paid
```

`happyhorse` and current self-hosted `segmentation` remain intentionally unbound because their contracts do not cleanly map to one current provider-neutral capability.

`wan_s2v` remains the semantically correct supplied-audio digital-human candidate, but Qwen cloud execution is never selected implicitly.

Current Qwen upstream documents Windows support through WSL2 rather than native Windows. UV Studio therefore fails closed when configuring that optional integration on native Windows; the native-Windows product baseline remains independent of Qwen/WSL.

Cloud profile persistence stores only an environment-variable reference to `DASHSCOPE_API_KEY`, never its resolved value. Full rationale: D-016 and `docs/integrations/QWEN_MM.md`.

## Stable Stage 3 context — execution consent/cost boundary

D-017 separates offer selection from permission to execute.

Cost estimate states are independent from `CostClass`:

```text
known
bounded
unknown
not_applicable
```

Current conservative defaults:

```text
free offer                    -> not_applicable
potentially_paid / paid offer -> unknown
```

Consent scopes:

```text
remote_execution  -> locality is remote/hybrid
external_cost     -> potentially_paid/paid
unknown_cost      -> current price estimate is unknown
```

`OneShotAuthorizationStore` grants are:

- random opaque tokens;
- process-local;
- short-lived;
- one-shot;
- bound to exact project + capability + offer + selection policy + canonical JSON input SHA-256;
- consumed on replay/mismatch attempts;
- never persisted to project files or archives.

API boundary:

```text
POST .../prepare-execution
POST .../authorize-execution
POST .../execute
```

Existing local/free execution stays token-free. There is no global reusable paid permission.

## Current Stage 3 slice — exact MCP invocation + provenance

### Official SDK `call_tool()` transport

`uv_studio/mcp/client.py` now supports one exact bounded tool call through the official MCP Python SDK v2.

Transport constraints:

- request JSON limit: 1 MiB;
- normalized response JSON limit: 4 MiB;
- bounded by trusted profile startup + call/discovery timeout values;
- one short-lived stdio child per call;
- SDK cleanup is exercised on success, MCP tool error and timeout;
- stderr remains in machine-local MCP log files;
- returned SDK models are normalized to JSON-safe product data;
- timeout, protocol, tool-error, request-limit and response-limit failures are structured.

The fake MCP server now exposes deterministic success, slow, explicit-error and oversized-response tools for CI. No network/provider API is involved.

### Exact binding resolution

`MCPManager.resolve_execution_target()` permits execution only when:

- selected offer resolves to exactly one configured `MCPToolBinding`;
- capability ID still matches;
- profile still exists and is enabled;
- offer adapter/locality/cost/asynchronous/features still match binding metadata;
- profile is READY;
- exact bound `tool_name` exists exactly once in the READY snapshot;
- current profile + all profile bindings hash to the same configuration digest captured at discovery.

Changing tool name, cost/locality, profile command, environment references or another binding for that profile therefore requires reconnect before any invocation. No fuzzy remapping exists.

### Authorization ordering

The existing `execute` endpoint consumes D-017 authorization before MCP target resolution/invocation.

Consequences:

- local/free MCP executes without consent token;
- remote/free still requires `remote_execution`;
- potentially-paid/paid still requires `external_cost` and, while estimate is unknown, `unknown_cost`;
- replayed or mutated-input tokens cannot reach MCP invocation;
- native/non-MCP adapters remain separate.

### Durable external run provenance

Added atomic canonical project records:

```text
tasks/run_<uuid>.json
```

A record is written as `running` before MCP invocation and finalized to `succeeded` or `failed`.

Persisted non-secret facts include:

- schema version + run ID;
- project/capability/offer/adapter IDs;
- exact MCP profile/tool;
- start/end timestamps;
- authorization-required fact + consent scopes, never token;
- cost class + cost-estimate snapshot;
- portable normalized input digest;
- success summary: response JSON byte count + SHA-256 only;
- failure summary: controlled exception class/code only.

Not persisted:

- authorization token;
- resolved environment-secret values;
- raw stderr;
- raw external error content;
- raw provider response in provenance.

Because `tasks/` is already canonical Project Store history, normal `.uvproj.zip` export includes provenance automatically while process-local authorization grants remain absent.

### Host-path boundary

Generic MCP argument pass-through does not translate project-relative files into absolute host paths.

Until a binding explicitly declares project-file argument semantics, the MCP adapter rejects raw:

- POSIX absolute paths;
- Windows drive paths;
- UNC paths;
- `file://` URIs.

Relative references such as `sources/clip.mp4` remain opaque JSON data and are not automatically resolved for the MCP child. This prevents the generic executor from becoming an arbitrary host-path bridge. The next slice owns explicit safe translation.

### Tests added

Unit tests cover:

- real stdio `call_tool` success + child cleanup;
- timeout + cleanup;
- explicit MCP tool error;
- oversized request rejection before spawn;
- oversized response rejection;
- exact READY binding resolution;
- config drift requiring reconnect;
- missing READY snapshot rejection;
- absolute POSIX/Windows/UNC/file-URI rejection.

API integration tests cover:

- exact local/free MCP execution;
- remote/potentially-paid authorization;
- one-shot replay rejection;
- durable success provenance;
- durable failed provenance on tool error;
- durable failed provenance on timeout;
- project archive includes provenance but not authorization token.

No test invokes Qwen, DashScope or another paid provider.

Decision: `project-context/decisions/D-018-authorized-mcp-invocation.md`.

## Verification status

PR #13 is merged into `main` at `416677c4ca758a01b0253c8880b44d44150a8cec` after full Ubuntu/Windows green CI.

PR #14 is open. A current-head PR matrix is required before merge because documentation/safety commits were added after the initial implementation run.

The latest observed current-slice Ubuntu bootstrap/unit job passed, including compilation and unit tests. Final acceptance still requires all four PR jobs on the final head:

- Ubuntu bootstrap/unit;
- Windows bootstrap/unit;
- Ubuntu API integration + HTTP smoke + frontend build;
- Windows API integration + HTTP smoke + frontend build.

## What works now on this branch

- durable portable projects and archives;
- provider-neutral recipes/policies/plans;
- semantic capabilities + explicit cost/locality offers;
- fail-closed local FFmpeg execution;
- generic official-SDK MCP discovery;
- explicit semantic MCP binding;
- optional pinned Qwen-MM profile/binding templates;
- explicit execution preparation/cost/consent;
- exact short-lived one-shot authorization;
- generic exact MCP `call_tool()` execution;
- stale/config-mutated MCP bindings fail closed;
- durable non-secret success/failure MCP provenance;
- project archive preservation of external run history;
- raw host paths rejected at the generic MCP boundary;
- baseline startup/testing without DashScope, Qwen, WSL or OpenClaw.

## Not implemented yet

- binding-owned project-file argument translation;
- Qwen core project-file execution through MCP;
- Qwen/DashScope cloud invocation from UV Studio production workflows;
- WSL bridge for optional Qwen integration on native Windows;
- OpenClaw adapter;
- generic general-video executor beyond current semantic offers;
- Stage 4 range editing, dubbing and music workflows.

## Current invariants

1. Recipe semantics never name Qwen/provider/runtime.
2. Discovery/offer metadata never equals execution permission.
3. `local_free_first` never widens to remote or paid-capable offers.
4. Qwen configuration is optional machine state, not project state.
5. Raw API-key values are not persisted or returned.
6. Qwen templates pin exact upstream SHA/tool names; no fuzzy remapping.
7. Native Windows does not require Qwen or WSL.
8. OpenClaw remains optional and unused in the MCP/Qwen direct path.
9. Remote/non-free execution must pass the product-owned consent/cost boundary first.
10. There is no global reusable paid-execution permission.
11. Unknown provider price stays unknown and requires explicit acknowledgement.
12. One-shot authorization tokens never enter portable project state.
13. An MCP READY snapshot is invalid for execution after profile/binding configuration drift.
14. Unbound discovered MCP tools are non-executable.
15. Generic MCP execution never auto-translates arbitrary host paths.
16. External invocation provenance contains non-secret audit facts, not credentials/tokens/stderr.

## Next slice

Implement **explicit binding-owned project-file argument translation**, tested first against the fake MCP server and only then applied narrowly to a freshly re-verified Qwen core binding if its pinned schema still matches. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
