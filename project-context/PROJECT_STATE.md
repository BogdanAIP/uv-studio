# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/qwen-mm-bindings`  
**Main baseline:** `3e2b60329f7b8aa22fec38c012d703e3a8cca26d`  
**Branch status:** optional pinned Qwen-MM profile/binding pack implemented; final PR-specific CI required before merge.

## Product architecture

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

- discovery/availability is not execution permission;
- open-source repository license does not imply cloud execution is free;
- machine commands/credential references are not portable project state;
- Qwen-MM and OpenClaw remain optional peer integrations;
- native Windows baseline must not require WSL2.

## Merged milestones

- `3214cec8...` — portable project archives/backups + Qwen-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan;
- `7fb0ca88...` — semantic Capability Registry;
- `4cbe383f...` — fail-closed selection + safe local FFprobe/FFmpeg execution;
- `3e2b60329f7b8aa22fec38c012d703e3a8cca26d` — official-SDK generic direct MCP stdio discovery + explicit semantic bindings.

## Current Stage 3 slice — optional Qwen-MM pack

### Fresh upstream verification

Re-verified current `QwenLM/Qwen-MM-Plugins` on 2026-08-11.

```text
commit:  7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
license: Apache-2.0
```

At verification time that commit was also current `main`.

Current upstream requirements/constraints confirmed:

- Python 3.12+;
- `uv`;
- FFmpeg for relevant local media operations;
- current Windows support documented as WSL2-only, native Windows unsupported;
- `core` local/basic media tools;
- `api` Qwen/DashScope-backed multimodal/ASR tools plus separate self-hosted segmentation;
- `video-edit` local workflow/skill material plus remote generation tools;
- remote generation tools require `DASHSCOPE_API_KEY`.

UV Studio templates pin the exact SHA rather than `main`.

### Three independent trusted packs

Added `uv_studio/integrations/qwen_mm.py` with:

```text
core
api
video-edit
```

No Qwen package is installed/launched during normal UV Studio startup.

Profiles use fixed trusted `uvx --from <exact SHA> <entrypoint>` templates. Generic arbitrary profile command creation remains absent.

### Core classification

Verified current tools include:

```text
read_image
read_video
media_info
visualize
crop
draw_bbox
save_view
```

Initially bound only:

```text
media_info -> media.probe
locality   = local
cost       = free
```

Other core tools remain intentionally unbound rather than being misrepresented as semantic `media.understand` or a not-yet-defined edit operation.

### API classification

Added provider-neutral semantic capability:

```text
speech.transcribe
```

Current bound API tools include multimodal understanding/OCR/grounding/Omni analysis and ASR.

All Qwen/DashScope-backed API bindings are explicitly:

```text
locality = remote
cost     = potentially_paid
```

Cloud profile stores only an environment reference to `DASHSCOPE_API_KEY`, never the resolved value.

Current self-hosted `segmentation` remains intentionally unbound because its compute/locality/output semantics differ from the other cloud tools and do not yet map cleanly to an existing UV capability.

### Video-edit generation classification

Current upstream generation tools verified:

```text
qwen_image
qwen_tts
wan_s2v
wan_t2v
happyhorse
```

Bindings:

```text
qwen_image -> image.generate
qwen_tts   -> speech.synthesize
wan_t2v    -> video.generate
wan_s2v    -> video.digital_human
```

All are:

```text
locality = remote
cost     = potentially_paid
```

`happyhorse` remains unbound because its mixed generate/edit/reference contract does not cleanly map to one current provider-neutral capability.

### Digital-human gap closed semantically

Current Qwen `wan_s2v` explicitly accepts portrait image + supplied audio and generates lip-synced digital-human video. Upstream marks its detection/generation path as billed.

This matches UV Studio `video.digital_human` semantics better than pinned VideoClaw's product-promo workflow, which Stage 2 classified as partial because supplied speech/audio was not accepted.

Important: this is currently an **offer**, not execution permission. No Qwen/DashScope tool invocation is enabled.

### Trusted Qwen integration API

Added:

```text
GET  /api/uv/integrations/qwen-mm
GET  /api/uv/integrations/qwen-mm/{pack_id}
POST /api/uv/integrations/qwen-mm/{pack_id}/configure
```

`configure` can persist only a predefined pinned template. A posted arbitrary command cannot replace `uvx`, the pinned source SHA or entrypoint.

On native Windows, trusted configuration fails closed with HTTP 409 because current Qwen upstream documents Windows as WSL2-only. Normal native-Windows UV Studio remains unaffected.

### MCP environment verification

Official MCP SDK v2 `stdio_client` was checked directly: it merges a small safe inherited environment allowlist (`PATH`, home/system variables, Windows executable lookup variables) with explicit `server.env`.

Therefore Qwen's `uvx` remains discoverable through `PATH` while UV Studio passes only explicitly referenced secrets such as `DASHSCOPE_API_KEY`; arbitrary process secrets are not inherited wholesale.

### Tests

Added unit/API coverage for:

- exact Qwen upstream SHA pin; no `.git@main`;
- core `media_info` local/free classification;
- cloud API/generation never classified free;
- `speech.transcribe` provider-neutral capability;
- `wan_s2v -> video.digital_human`;
- `happyhorse`/`segmentation` intentional non-binding;
- env-reference persistence without key values;
- preserving unrelated MCP profiles;
- native-Windows Qwen configuration fail-closed;
- Qwen catalog remains secret-free and tool execution disabled;
- arbitrary request body cannot replace the trusted profile command.

Docs: `docs/integrations/QWEN_MM.md`. Decision: D-016.

## Verification status

Functional code head before documentation-only commits: `93f094bd7d2ed3d43effdcc9a2663fbf9a178aa4`, CI run `31470778147`.

Observed there:

- Ubuntu bootstrap/unit: success;
- Windows bootstrap/unit: success;
- Ubuntu API integration/HTTP smoke: success;
- Qwen tests require no real Qwen install, WSL or paid API key.

Docs/decision head `04c7f0066bd096f92846cc2b1508233e9c0cc705`, CI run `31470945236` observed:

- Ubuntu bootstrap/unit: success;
- Windows bootstrap/unit: success;
- Ubuntu app-baseline/API/HTTP/frontend build: success;
- Windows API integration and HTTP smoke: success;
- Windows frontend install/build still completing when this state was written.

This state update creates a newer head. Merge requires the actual PR head to pass full Linux/Windows PR-specific CI.

## What works now

- durable portable projects;
- provider-neutral recipes/policies/plans;
- semantic capabilities + explicit cost/locality offers;
- fail-closed local execution;
- generic official-SDK MCP discovery;
- explicit semantic MCP binding;
- optional pinned Qwen-MM profile/binding templates;
- auditable local/free vs remote/potentially-paid classification;
- a semantically correct potential `digital_human` implementation via Wan S2V;
- baseline startup/testing without DashScope, Qwen, WSL or OpenClaw.

## Not implemented yet

- MCP `call_tool` execution;
- explicit remote/potentially-paid execution consent;
- provider/tool cost estimate/unknown-cost handling;
- persistent per-run execution provenance for external tools;
- Qwen cloud invocation;
- WSL bridge for Qwen on native Windows;
- OpenClaw adapter;
- generic general-video executor;
- Stage 4 range editing, dubbing and music workflows.

## Current invariants

1. Recipe semantics never name Qwen/provider/runtime.
2. Discovery/offer metadata never equals execution permission.
3. `local_free_first` never selects Qwen remote/potentially-paid offers.
4. Qwen configuration is optional machine state, not project state.
5. Raw API-key values are not persisted or returned.
6. Qwen templates pin exact upstream SHA/tool names; no fuzzy remapping.
7. Current native Windows does not claim Qwen support and does not require WSL.
8. Qwen cloud tool invocation remains disabled.
9. OpenClaw remains optional and unused in the Qwen path.
10. New external execution must pass a separate consent/cost boundary before being enabled.

## Next slice

Design and implement the **MCP/provider execution consent + cost boundary**, tested first with the local fake MCP server. Do not make real paid Qwen calls in CI. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
