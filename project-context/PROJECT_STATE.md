# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/mcp-project-file-inputs`  
**Main baseline:** `bb7929dbbd8e5bd69bc509d98c58f4a56bb033c5`  
**Open PR:** #15 — explicit MCP project-file inputs  
**Branch status:** implementation/tests/docs complete; final Linux/Windows CI on the final head is required before merge.

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
          -> optional explicit project-file translation
          -> running tasks/run_<id>.json
          -> bounded short-lived call_tool()
          -> succeeded/failed provenance

Machine Studio Config
  -> MCPProfile
  -> bounded stdio discovery
  -> MCPToolDescriptor
  -> explicit MCPToolBinding
      -> optional MCPProjectFileInput declarations
  -> CapabilityOffer
```

Permanent rules:

- discovery/availability is not execution permission;
- open-source repository license does not imply cloud execution is free;
- local failure never silently widens into remote or paid execution;
- machine commands/credential references are not portable project state;
- Qwen-MM and OpenClaw remain optional peer integrations;
- native Windows remains a first-class baseline and must not require WSL2;
- authorization tokens are runtime state, never portable project state;
- generic MCP execution never infers filesystem access from field names or tool schemas.

## Merged milestones

- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan;
- `7fb0ca88...` — semantic Capability Registry;
- `4cbe383f...` — fail-closed selection + safe local FFprobe/FFmpeg execution;
- `3e2b60329f7b8aa22fec38c012d703e3a8cca26d` — official-SDK direct MCP stdio discovery + explicit semantic bindings;
- `4108db23f7de67293a53d1005a119a015539c0aa` — optional pinned Qwen-MM profile/binding pack (PR #12);
- `416677c4ca758a01b0253c8880b44d44150a8cec` — execution consent/cost boundary (PR #13);
- `bb7929dbbd8e5bd69bc509d98c58f4a56bb033c5` — authorized exact MCP `call_tool()` execution + provenance (PR #14).

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

Important classifications:

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

`wan_s2v` remains the semantically correct supplied-audio digital-human candidate. It can only become executable after trusted configuration, exact READY MCP discovery and the D-017 remote/cost/unknown-cost authorization required for its offer; it is never selected implicitly.

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

## Stable Stage 3 context — exact MCP invocation + provenance

### Official SDK `call_tool()` transport

`uv_studio/mcp/client.py` supports one exact bounded tool call through the official MCP Python SDK v2.

Transport constraints:

- request JSON limit: 1 MiB;
- normalized response JSON limit: 4 MiB;
- bounded by trusted profile startup + call/discovery timeout values;
- one short-lived stdio child per call;
- SDK cleanup is exercised on success, MCP tool error and timeout;
- stderr remains in machine-local MCP log files;
- returned SDK models are normalized to JSON-safe product data;
- timeout, protocol, tool-error, request-limit and response-limit failures are structured.

The fake MCP server exposes deterministic success, slow, explicit-error and oversized-response tools for CI. No network/provider API is involved.

### Exact binding resolution

`MCPManager.resolve_execution_target()` permits execution only when:

- selected offer resolves to exactly one configured `MCPToolBinding`;
- capability ID still matches;
- profile still exists and is enabled;
- offer adapter/locality/cost/asynchronous/features still match binding metadata;
- profile is READY;
- exact bound `tool_name` exists exactly once in the READY snapshot;
- current profile + all profile bindings hash to the same configuration digest captured at discovery.

Changing tool name, cost/locality, profile command, environment references or another binding for that profile therefore requires reconnect before invocation. No fuzzy remapping exists.

### Authorization ordering

The project capability `execute` endpoint consumes D-017 authorization before MCP target resolution/invocation.

Consequences:

- local/free MCP executes without consent token;
- remote/free requires `remote_execution`;
- potentially-paid/paid requires `external_cost` and, while estimate is unknown, `unknown_cost`;
- replayed or mutated-input tokens cannot reach MCP invocation;
- native/non-MCP adapters remain separate.

### Durable external run provenance

Canonical project records live at:

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

Because `tasks/` is canonical Project Store history, normal `.uvproj.zip` export includes provenance automatically while process-local authorization grants remain absent.

Decision: D-018.

## Current Stage 3 slice — explicit project-file MCP inputs

### Binding-owned file contract

Added versioned `MCPProjectFileInput` metadata on an exact `MCPToolBinding`.

Version 1 declares:

```text
argument_name
allowed_roots
required
```

The generic contract deliberately permits only product/media roots:

```text
sources
assets
artifacts
exports
```

It refuses internal project control/history roots:

```text
tasks
timeline
reviews
```

Old serialized bindings without `project_file_inputs` remain valid and load with an empty contract. No existing binding receives filesystem translation implicitly.

### Safe translation semantics

MCP execution now follows this order:

1. exact binding/READY target is resolved;
2. provenance starts from the portable request facts;
3. caller-supplied absolute POSIX, Windows drive, UNC and `file://` values are rejected;
4. only explicitly declared top-level file arguments are translated;
5. translation uses `ProjectStore.resolve_project_file(..., must_exist=True, allowed_roots=<binding contract>)`;
6. the resolved target must be a file;
7. only the short-lived MCP invocation dictionary contains the absolute machine path.

Authorization and provenance continue to hash the original portable request such as:

```json
{"path":"sources/input.mp4"}
```

They never hash or persist a machine path such as `C:\...` or `/tmp/...`.

Wrong-root references, traversal, missing files and required-but-missing arguments fail closed before MCP process invocation.

Changing a binding's file contract changes `MCPToolBinding.to_dict()` and therefore the existing MCP configuration digest. A READY snapshot cannot be reused after file-contract drift; reconnect is required.

### Real fake-MCP integration test

The local MCP fixture can opt into `read_project_file`.

API integration tests now prove:

- a real `sources/input.txt` portable reference is resolved only for invocation;
- the short-lived MCP subprocess can read the actual file;
- a process exit marker proves the subprocess lifecycle;
- provenance retains `normalized_input_digest({"path":"sources/input.txt"})`;
- provenance contains neither the resolved file path nor the temporary project root;
- `.uvproj.zip` archive contains the portable run record but no resolved host path;
- wrong-root file input returns controlled HTTP 422 and fails before MCP spawn.

### Qwen core `media_info` narrow enablement

On 2026-08-11 the pinned Qwen core implementation and current upstream were re-checked. The `media_info.py` source blob is unchanged between the pinned UV Studio SHA and the current fetched upstream revision, and its contract remains:

```text
media_info(path: str, raw: bool = False)
```

with `path` documented as an absolute image/video path.

Therefore only:

```text
qwen-mm-core.media-info -> media.probe
```

receives:

```text
argument_name = path
allowed_roots = sources, assets, artifacts, exports
required      = true
```

No Qwen cloud/API/video-edit binding receives an inferred file contract in this slice.

This makes the local/free Qwen core `media_info` binding technically executable through the existing generic path after trusted Qwen configuration + exact READY discovery. No Qwen process is started automatically, and native Windows still rejects current Qwen configuration because upstream remains WSL2-only there.

### Qwen execution catalog truth correction

After PR #14, Qwen pack catalog metadata saying `tool_execution_enabled: false` became stale: generic exact MCP execution now exists.

The catalog now truthfully reports conditional support:

```text
tool_execution_enabled = true
execution_policy.mode = generic_mcp_after_discovery_and_authorization
automatic = false
requires_ready_discovery = true
authorization_enforced = true
```

`configure` now tells callers to run discovery and states that execution is limited to exact READY bindings with UV Studio authorization still enforced when locality/cost requires it.

This is not an automatic provider opt-in and does not make DashScope a baseline dependency.

### Tests added/updated

Unit coverage includes:

- backward-compatible old binding serialization;
- file-contract round-trip;
- duplicate argument contract rejection;
- internal-root rejection;
- file-contract configuration drift requiring reconnect;
- exact field-only translation;
- undeclared relative values remain opaque;
- wrong-root/missing/traversal/required-field failures;
- raw absolute host-path rejection remains intact.

API coverage includes:

- real subprocess project-file reading;
- fail-before-spawn on invalid project file;
- portable provenance digest;
- no absolute path leakage into provenance/archive;
- truthful Qwen conditional execution metadata;
- exact Qwen core `media_info` file contract;
- Qwen cloud bindings remain without inferred file contracts;
- secrets remain references only.

No test invokes Qwen, DashScope or another paid provider.

Decision: `project-context/decisions/D-019-mcp-project-file-inputs.md`.

## Verification status

PR #14 is merged into `main` at `bb7929dbbd8e5bd69bc509d98c58f4a56bb033c5` after the full exact-head Ubuntu/Windows matrix passed.

PR #15 is open. The first code-head CI already proved the new unit suite on Ubuntu and Windows and the Ubuntu API integration/HTTP path, but documentation commits were added after that head. Final acceptance requires a fresh full matrix on the final PR head:

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
- explicit binding-owned project-file translation;
- portable authorization/provenance despite machine-only invocation paths;
- Qwen core `media_info` has a verified safe project-file contract;
- Qwen catalog truthfully reflects conditional generic MCP execution;
- raw host paths remain rejected at the generic MCP boundary;
- baseline startup/testing without DashScope, Qwen, WSL or OpenClaw.

## Not implemented yet

- executable `native_videoclaw` compatibility adapter despite one built-in Edge TTS offer being advertised as available when installed;
- exact provider/model configuration contracts for VideoClaw model-backed native offers;
- Qwen cloud/API bindings' project-file contracts (not inferred without schema verification);
- WSL bridge for optional Qwen integration on native Windows;
- OpenClaw adapter;
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
17. Only exact binding-declared project file fields may become machine paths.
18. Authorization/provenance file digests remain portable across project relocation.
19. Internal project history/control directories are not generic MCP file-input roots.

## Next slice

Implement **real native VideoClaw compatibility execution**, beginning with the already-advertised `native_videoclaw.edge_tts` offer, and generalize external provenance where necessary without opening arbitrary vendored function execution. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
