# Next Task

**Primary target:** begin Stage 3 with a product-owned semantic Capability Registry. Do not connect Qwen-MM/OpenClaw or spend money in the first slice.

## Why this comes next

Stage 2 now separates:

```text
RecipeDefinition
  -> ProductionPolicy
  -> RecipeExecutionPlan
```

Execution planning also proved that existing upstream pipelines only partially cover UV Studio semantics:

- `narrated_video` matches native `standard`;
- `action_transfer` matches the native transfer pipeline;
- `digital_human` is only partial because the upstream product-promo workflow does not accept supplied speech;
- `general_video` has no honest native implementation and must stay unavailable.

The missing abstraction is therefore not another hard-coded pipeline wrapper. It is the Stage 3 semantic Capability Registry that can resolve `video.generate`, `speech.synthesize`, `media.understand`, `video.digital_human`, etc. through replaceable local/MCP/native adapters.

## First Stage 3 slice

1. Add `uv_studio/capabilities/` as product-owned code.
2. Define strict/versioned `CapabilityDefinition`, including at least:
   - `capability_id`;
   - title/description;
   - operation kind;
   - input/output media kinds;
   - locality class: local / remote / hybrid;
   - cost class: free / potentially_paid / paid;
   - asynchronous flag;
   - optional quality/features metadata.
3. Define adapter metadata separately from semantic capability definitions:
   - stable `adapter_id`;
   - adapter kind: local / native / mcp / runtime;
   - availability state and reason;
   - capabilities provided;
   - no secrets in registry responses.
4. Implement deterministic `CapabilityRegistry`:
   - register definitions;
   - register adapter offers;
   - list/get;
   - resolve available offers for a semantic capability;
   - reject duplicate/conflicting IDs;
   - preserve deterministic ordering.
5. Add baseline local/native offers without paid calls:
   - deterministic FFmpeg-related media operations as local/free capabilities where already supported;
   - existing VideoClaw compatibility offers as native metadata only;
   - do not call external models.
6. Add API:

```text
GET /api/uv/capabilities
GET /api/uv/capabilities/{capability_id}
GET /api/uv/capabilities/{capability_id}/offers
```

7. Update project execution-plan API so runtime config slots can optionally report whether any capability offer currently exists, without choosing a provider automatically.
8. Add unit/API tests and documentation.

## Mandatory architecture rules

- `RecipeDefinition` remains provider-neutral and unchanged.
- Capability definitions are semantic; provider/runtime data lives in adapter offers.
- local/free deterministic work must not be routed to paid AI by default.
- no API key is required for registry startup/listing.
- no secrets may appear in capability metadata/API.
- OpenClaw is an optional adapter, not a mandatory layer.
- Qwen-MM-Plugins is an optional direct-MCP adapter and workflow donor, not a baseline paid dependency.
- native Windows startup must work with optional WSL integrations absent.
- do not modify `vendor/videoclaw-app` in this slice.

## What NOT to implement yet

- actual Qwen-MM installation;
- DashScope calls;
- OpenClaw launch/Gateway;
- generic MCP process management;
- automatic paid-provider selection;
- cost estimation from live prices;
- full general-video generation;
- dubbing/range-edit/music recipes.

The first Capability Registry slice is metadata + deterministic resolution only. This keeps Stage 3 testable without credentials and creates the exact seam where later adapters can plug in.

## Suggested files

```text
uv_studio/capabilities/__init__.py
uv_studio/capabilities/models.py
uv_studio/capabilities/registry.py
uv_studio/capabilities/builtin.py
uv_studio/api/capabilities.py

tests/test_capability_registry.py
tests_api/test_capabilities_api.py

docs/architecture/CAPABILITIES.md
```

## Acceptance criteria

- capability IDs and adapter IDs are strict/versioned/provider-separated;
- registry starts and lists capabilities with zero API credentials;
- `free` vs `potentially_paid/paid` is explicit metadata;
- semantic capability listing contains no secret/config values;
- available offers can be queried without executing them;
- execution plans can show whether required semantic capabilities have any current offers;
- tests + frontend production build stay green on Windows/Linux;
- no hidden paid dependency is added.

After that, implement adapters incrementally: local deterministic tools first, then direct MCP/Qwen-MM optional support, then OpenClaw only where its broader runtime is useful.
