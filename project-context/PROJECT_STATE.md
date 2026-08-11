# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/native-videoclaw-edge-tts`  
**Main baseline:** `b76c25c0e97f9198bbaab848c2b3e6b99421b9d3`  
**Open PR:** #17 — native VideoClaw Edge TTS execution  
**PR status:** draft while final Linux/Windows CI and documentation are completed.

## Durable architecture snapshot

```text
Canonical Project
  -> RecipeDefinition / ProductionPolicy
  -> RecipeExecutionPlan
  -> semantic capability_id
  -> CapabilityRegistry
  -> CapabilityOffer
  -> SelectionPolicy
  -> ExecutionPreparation
  -> D-017 one-shot authorization when required
  -> exact execution adapter
      -> local_ffmpeg
      -> mcp.<profile> exact binding
      -> native_videoclaw exact-offer compatibility
  -> canonical artifacts/tasks provenance
```

Machine-only integration state remains outside portable projects:

```text
MCPProfile
  -> trusted command + environment-variable references
  -> bounded stdio discovery
  -> exact MCPToolBinding
      -> optional MCPProjectFileInput
  -> READY configuration digest
```

Permanent rules:

- discovery/availability is not execution permission;
- open-source license does not imply remote execution is free;
- local failure never silently widens into remote or paid execution;
- machine commands, resolved secrets and authorization tokens are not portable project state;
- raw host paths are never generic capability inputs;
- Qwen-MM and OpenClaw are optional peer integrations;
- native Windows remains a first-class baseline;
- native VideoClaw compatibility never means arbitrary vendored function execution.

## Merged milestones on `main`

- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan;
- `7fb0ca88...` — semantic Capability Registry;
- `4cbe383f...` — fail-closed selection + safe local FFprobe/FFmpeg execution;
- `3e2b60329f7b8aa22fec38c012d703e3a8cca26d` — official-SDK direct MCP discovery + explicit semantic bindings;
- `4108db23f7de67293a53d1005a119a015539c0aa` — optional pinned Qwen-MM profile/binding pack (PR #12);
- `416677c4ca758a01b0253c8880b44d44150a8cec` — product-owned execution consent/cost boundary (PR #13);
- `bb7929dbbd8e5bd69bc509d98c58f4a56bb033c5` — authorized exact MCP `call_tool()` + durable provenance (PR #14);
- `b76c25c0e97f9198bbaab848c2b3e6b99421b9d3` — explicit MCP project-file inputs + resolved allowed-root symlink hardening (PR #15).

## Stable Stage 3 capabilities

### Local deterministic execution

`local_ffmpeg` remains the local/free deterministic adapter.

Current executable offers include:

```text
local_ffmpeg.media_probe      -> media.probe
local_ffmpeg.timeline_assemble -> timeline.assemble
```

Project paths are resolved through `ProjectStore`; raw shell/FFmpeg flags and filesystem escape are not exposed.

### D-017 selection/authorization boundary

Consent scopes are semantic and transport-independent:

```text
remote_execution  -> remote/hybrid locality
external_cost     -> potentially_paid/paid
unknown_cost      -> provider price not known to UV Studio
```

`OneShotAuthorizationStore` grants are process-local, short-lived, one-shot and bound to the exact project + capability + offer + selection policy + canonical input digest. A mismatch consumes/fails the grant. Tokens are never archived.

Local/free execution remains token-free. Remote/free execution still requires `remote_execution`.

### Exact MCP execution and provenance

Official MCP Python SDK v2 is used for bounded stdio discovery and one exact `call_tool()` invocation.

Execution requires:

- an exact configured semantic binding;
- a READY discovery snapshot;
- unchanged profile/binding configuration digest;
- exact bound tool identity;
- D-017 authorization when locality/cost requires it.

Each external MCP invocation writes a versioned non-secret record under:

```text
tasks/run_<uuid>.json
```

Persisted facts include project/capability/offer/adapter identity, target identity, timestamps/status, authorization scopes, cost snapshot, portable input digest and safe success/failure summary. Tokens, resolved environment secrets, stderr and raw provider errors are excluded.

### Binding-owned MCP project files

`MCPProjectFileInput` is an explicit versioned contract on an exact binding. Only declared top-level arguments may translate a portable project reference into a short-lived host path.

Generic exposable roots are limited to:

```text
sources
assets
artifacts
exports
```

Internal `tasks`, `timeline` and `reviews` are not generic MCP input roots.

`ProjectStore.resolve_project_file()` now re-checks the resolved parent and target against the resolved allowed-root boundary. A symlink such as `sources/alias -> ../tasks/private` therefore fails even though the resolved target is still inside the overall project.

The verified Qwen core `media_info(path, raw=False)` binding is the first explicit project-file contract. Qwen cloud bindings do not receive inferred file access.

### Optional Qwen-MM pack

Pinned reference:

```text
QwenLM/Qwen-MM-Plugins
commit: 7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
license: Apache-2.0
```

Qwen remains optional. Core `media_info` is classified local/free; DashScope-backed understanding, ASR and generation remain remote/potentially-paid and require exact READY discovery plus D-017 consent/cost acknowledgements. Cloud configuration persists only the `DASHSCOPE_API_KEY` environment-variable reference. Current native-Windows configuration remains fail-closed because the upstream integration is WSL2-oriented.

## Current PR #17 — exact native VideoClaw Edge TTS execution

### Problem being closed

The built-in registry already advertises:

```text
native_videoclaw.edge_tts -> speech.synthesize
locality = remote
cost     = free
```

as `AVAILABLE` when `edge_tts` is installed. Before this PR, the project capability API had no native execution transport, so an advertised available offer became a dead end.

### Product-owned exact adapter

Added `NativeVideoClawAdapter` outside `vendor/`.

It executes only:

```text
offer_id      = native_videoclaw.edge_tts
capability_id = speech.synthesize
adapter_id    = native_videoclaw
```

There is no generic module/function/command dispatch and no fallback to arbitrary vendored VideoClaw functions.

Supported input is deliberately narrow:

```text
text   required, non-empty, <= 20,000 chars
voice  optional, default zh-CN-YunjianNeural, <= 128 chars
speed  optional positive finite number, default 1.0
```

The adapter preserves the pinned VideoClaw speed-to-rate conversion and uses `edge_tts.Communicate` directly through this product-owned compatibility boundary.

Callers cannot provide an output path. UV Studio creates:

```text
artifacts/art_<uuid>.mp3
```

and registers it as a canonical audio `ProjectReference` only after successful synthesis.

### Authorization remains transport-independent

Edge TTS is remote/free, therefore execution still requires D-017 `remote_execution` acknowledgement but no cost acknowledgement.

The API consumes the exact one-shot authorization before the native adapter runs. Existing `local_free_first` cannot widen to Edge TTS because the offer is remote.

Other `native_videoclaw.*` offers remain non-executable through this route even if a test registry marks one available. Model-backed built-ins remain `CONFIGURATION_REQUIRED` until exact provider/model/credential contracts exist.

### Transport-neutral external provenance

`ExternalRunProvenance` no longer depends on the MCP target class. It accepts a small transport-neutral `ExternalExecutionTarget`.

Archive schema v1 is intentionally unchanged for compatibility and retains historical serialized fields:

```text
profile_id
tool_name
```

For MCP they mean profile/tool. For Edge TTS they contain stable target identity:

```text
profile_id = native_videoclaw
tool_name  = edge_tts
```

A future rename requires an explicit schema migration; this PR does not invalidate existing MCP project history.

### Failure/cleanup guarantees

- missing/incomplete `edge_tts` fails before provenance/network execution;
- provider exceptions are wrapped as controlled `CapabilityToolFailed`;
- common capability execution exceptions now expose stable machine codes;
- partial MP3 output is removed on synthesis failure;
- raw provider exception text is not persisted;
- speech text is not stored in artifact metadata or external run provenance;
- if an artifact has already been registered successfully, a later provenance persistence failure does not delete the file and leave a dangling project reference.

### Runtime dependency

UV Studio now installs:

```text
edge-tts>=7.2.8,<8
```

The package is still lazy-imported by the adapter so incomplete installations fail explicitly. CI uses a fake communicator and makes no live Edge TTS request.

### Tests in PR #17

Unit tests cover:

- exact pinned VideoClaw request semantics and speed conversion;
- UV Studio-owned portable artifact path and project registration;
- no speech text / host path in provenance;
- default voice;
- arbitrary native offer rejection;
- caller-controlled output/unknown field rejection;
- missing dependency failure before provenance/network;
- provider failure cleanup + sanitized stable failure code.

API tests cover:

- remote consent required before Edge TTS adapter invocation;
- exact one-shot authorization permits execution;
- token replay rejected;
- mutated speech input rejected before adapter invocation;
- `local_free_first` does not widen to remote Edge TTS.

Existing MCP/project/archive/local-FFmpeg tests remain the regression guard for schema and transport compatibility.

Decision: `project-context/decisions/D-020-native-videoclaw-edge-tts.md`.

## CI status

The first PR #17 run compiled and installed successfully on Ubuntu and Windows. Unit CI exposed one test/contract mismatch: generic `CapabilityToolFailed` previously had no stable code, so provenance used `external_execution_failed`. The implementation was tightened by adding stable capability-domain codes rather than weakening the assertion.

A fresh full matrix is required on the final PR head:

- Ubuntu bootstrap/unit;
- Windows bootstrap/unit;
- Ubuntu API integration + HTTP smoke + frontend build;
- Windows API integration + HTTP smoke + frontend build.

Do not merge until all four required jobs are green on the same final head.

## What is not implemented yet

- exact provider/model/credential configuration contracts for VideoClaw model-backed native offers;
- Qwen cloud/API bindings' project-file contracts where upstream schemas have not been verified;
- optional native-Windows WSL bridge for Qwen;
- optional OpenClaw adapter/runtime;
- Stage 4 existing-video range editing;
- Stage 5 dubbing and later workflow stages.

None of these gaps may be hidden by marking a capability available before its execution contract is real.

## Current invariants

1. Recipe semantics never name provider/runtime-specific implementation IDs.
2. Discovery/offer metadata never equals execution permission.
3. `local_free_first` never widens to remote or paid-capable offers.
4. Remote/non-free execution passes D-017 before external invocation.
5. Authorization is one-shot and exact-input-bound.
6. Tokens, resolved secrets and raw remote errors never enter portable project state.
7. MCP READY execution fails after configuration drift.
8. Unbound MCP tools are non-executable.
9. Generic MCP filesystem translation is explicit binding metadata only.
10. Resolved project-file symlinks cannot cross an operation's allowed roots.
11. External provenance is portable and transport-neutral at the common boundary.
12. Native VideoClaw compatibility executes exact known offers only.
13. Edge TTS is remote/free: keyless does not mean local and does not bypass consent.
14. Native Windows does not require Qwen, WSL or OpenClaw.
15. Model-backed native offers remain configuration-required until exact contracts exist.

## Next slice after PR #17

Once PR #17 is merged with a green final matrix, begin the first Stage 4 **existing-video range-edit foundation**: introduce a provider-neutral range representation and bounded local FFmpeg extraction/reinsertion primitives without adding generative replacement yet. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
