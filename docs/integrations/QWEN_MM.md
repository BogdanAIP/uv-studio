# Optional Qwen-MM-Plugins integration

## Verified upstream and pin policy

UV Studio's trusted Qwen-MM profile pack remains pinned to:

```text
Repository: QwenLM/Qwen-MM-Plugins
Commit:     7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
License:    Apache-2.0
```

The pin is deliberate: UV Studio does not execute a moving `main` branch.

On **2026-08-11** upstream `main` had advanced beyond the UV Studio pin. The current checked head was:

```text
8d6ea5a1f658260743307c52c2024ec87599fa48
```

The local core `media_info` implementation was re-checked at both the UV Studio pin and current upstream. Its source blob is unchanged (`2acd32fca660359c48efd34f9e34d9c8a48bf862`) and the relevant contract remains:

```text
media_info(path: str, raw: bool = False)
```

where `path` is documented as an absolute path to an image/video/audio media file.

Changing the UV Studio pin is a separate reviewed action; current-upstream observation does not silently update executable machine configuration.

Current upstream requirements/constraints still relevant to UV Studio include:

- Python 3.12+ and `uv`;
- system FFmpeg for relevant local media operations;
- Windows support through **WSL2 only** rather than validated native Windows;
- `core` local media tools without a DashScope API key;
- `api` Qwen/DashScope-backed multimodal/ASR tools plus separately self-hosted segmentation;
- `video-edit` generation tools that may invoke remote services;
- `DASHSCOPE_API_KEY` for DashScope-backed operations.

UV Studio never infers execution price from the Apache-2.0 repository license.

## Why three packs

Qwen-MM is represented as three independent optional MCP profiles:

```text
core
api
video-edit
```

This prevents the false assumption that installing one open-source repository makes every operation local or free.

No Qwen profile is installed or launched during normal UV Studio startup.

## Core pack

Profile:

```text
profile_id: qwen-mm-core
entrypoint: qwen-mm-plugins-core
extra:      core
credential: none
```

Pinned launch requirement:

```text
qwen-mm-plugins[core] @ git+https://github.com/QwenLM/Qwen-MM-Plugins.git@7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
```

Verified core tools include:

```text
read_image
read_video
media_info
visualize
crop
draw_bbox
save_view
```

UV Studio currently binds only:

```text
media_info -> media.probe
locality   = local
cost       = free
```

The other tools remain intentionally unbound. `read_image`, `read_video` and `visualize` are model-harness content/presentation primitives rather than provider-neutral `media.understand` implementations by themselves. `crop`, `draw_bbox` and `save_view` will be reconsidered only when UV Studio has exact matching semantic edit capabilities.

### Project-file input for `media_info`

Qwen `media_info` requires an absolute host path, while UV Studio projects must remain portable. The binding therefore declares one explicit project-file argument:

```text
argument_name = path
allowed_roots = sources, assets, artifacts, exports
required      = true
```

A caller sends a portable project-relative value such as:

```json
{"path":"sources/input.mp4","raw":false}
```

Only after selection/authorization and exact READY binding resolution does UV Studio resolve that declared field through Project Store into a short-lived host path for the MCP invocation.

Raw absolute POSIX/Windows paths, UNC paths and `file://` values supplied by the caller remain rejected. Undeclared fields are never translated.

The authorization/provenance digest remains based on the portable input. The resolved machine path is not written into project provenance or `.uvproj.zip` archives.

## API pack

Profile:

```text
profile_id: qwen-mm-api
entrypoint: qwen-mm-plugins-api
extra:      api
credential reference: DASHSCOPE_API_KEY
```

Cloud-backed bindings are deliberately classified:

```text
locality = remote
cost     = potentially_paid
```

Bound tools include:

```text
vision_chat              -> media.understand
ocr                      -> media.understand
grounding                -> media.understand
transcribe_audio         -> speech.transcribe
omni_av_caption          -> media.understand
omni_asr                 -> speech.transcribe
omni_asr_timestamped     -> speech.transcribe
omni_multi_speaker_asr   -> speech.transcribe
omni_av_grounding        -> media.understand
omni_av_counting         -> media.understand
omni_music_caption       -> media.understand
```

`segmentation` remains intentionally unbound because the current tool is a self-hosted SAM3-style service whose compute/locality/cost semantics differ from the DashScope tools and do not yet map cleanly to an existing UV Studio semantic output contract.

The profile stores only the environment-variable **name** `DASHSCOPE_API_KEY`; it never persists the resolved key value.

No API-pack file argument is inferred automatically. Each future file-bearing cloud binding must be independently verified before it can receive an explicit `MCPProjectFileInput` contract.

## Video-edit generation pack

Profile:

```text
profile_id: qwen-mm-video-edit
entrypoint: qwen-mm-plugins-video-edit
extra:      video-edit
credential reference: DASHSCOPE_API_KEY
```

Generation tools include:

```text
qwen_image
qwen_tts
wan_s2v
wan_t2v
happyhorse
```

UV Studio binds:

```text
qwen_image -> image.generate
qwen_tts   -> speech.synthesize
wan_t2v    -> video.generate
wan_s2v    -> video.digital_human
```

All four are classified:

```text
locality = remote
cost     = potentially_paid
```

### `wan_s2v` and digital-human semantics

The verified `wan_s2v` contract is a substantially better semantic fit for:

```text
portrait image + supplied audio -> lip-synced digital-human video
```

than the pinned VideoClaw product-promo workflow that Stage 2 classified as partial compatibility.

This does **not** create automatic execution. The offer must still be explicitly configured, discovered as the exact READY binding, selected, and authorized through UV Studio's remote/cost boundary before any call can occur.

### Why `happyhorse` is unbound

The current `happyhorse` tool combines multiple generation/edit/reference modes. Mapping that mixed provider contract to one current UV Studio capability would weaken semantic correctness, so it remains intentionally unbound.

## Trusted configuration API

UV Studio exposes a narrow static pack catalog/configuration API:

```text
GET  /api/uv/integrations/qwen-mm
GET  /api/uv/integrations/qwen-mm/{pack_id}
POST /api/uv/integrations/qwen-mm/{pack_id}/configure
```

`configure` can persist only one of the known pinned templates. It does not accept user-supplied executable command/argv values.

The request body cannot replace the pinned `uvx` command, source SHA or entrypoint. Generic arbitrary command profile creation remains intentionally absent.

The pack catalog reports execution truthfully as conditional rather than automatic:

```text
tool_execution_enabled = true
execution_policy.mode = generic_mcp_after_discovery_and_authorization
execution_policy.automatic = false
execution_policy.requires_ready_discovery = true
execution_policy.authorization_enforced = true
```

This means UV Studio has a generic exact MCP execution transport. It does **not** mean a pack is currently installed, READY, credentialed or approved for a remote/paid call.

## Windows behavior

Current Qwen upstream documents Windows support as WSL2-only.

Therefore the trusted Qwen configure action is fail-closed in a native Windows UV Studio process and returns a platform conflict instead of writing a profile that would imply native support.

This does not affect:

- native Windows UV Studio startup;
- Project Store;
- local FFmpeg/FFprobe capabilities;
- generic MCP infrastructure;
- native VideoClaw compatibility paths.

A future WSL bridge may be added only after explicit testing.

## Configuration, discovery, authorization and execution

The actual flow is now:

```text
configure trusted pinned pack
  -> bounded MCP discovery
      -> exact bound tool appears in READY snapshot
          -> semantic CapabilityOffer becomes available
              -> selection policy
                  -> D-017 execution preparation
                      -> one-shot authorization when locality/cost requires it
                          -> exact MCP binding re-validation
                              -> bounded call_tool
                                  -> durable non-secret provenance
```

Important behavior:

- `local_free_first` can select only `local + free + available` offers;
- it never widens into Qwen remote/potentially-paid offers;
- local/free Qwen core `media_info` needs no consent token once the optional profile is configured/READY;
- remote/free would require `remote_execution`;
- Qwen remote/potentially-paid offers require `remote_execution`, `external_cost`, and currently `unknown_cost` because UV Studio does not invent a current provider price;
- authorization is one-shot and bound to the exact portable input digest;
- no global paid-provider permission exists;
- a changed profile/binding/file contract invalidates the READY execution snapshot and requires reconnect.

## Drift behavior

The profile pack pins an exact Qwen commit and exact expected tool names.

If upstream renames/removes a tool or changes a file-input contract, UV Studio must update and re-verify the trusted pack. It must not fuzzy-remap a newly discovered tool by name similarity.

With the generic MCP layer:

- an unrecognized new tool stays unbound;
- an expected bound tool that is not reported becomes unavailable;
- a configuration change invalidates execution until reconnect;
- canonical recipes/projects remain provider-neutral.

## What this integration deliberately does not do

- no Qwen runtime bundled with baseline UV Studio;
- no Qwen process at normal startup;
- no DashScope API call in CI/tests;
- no raw key persistence;
- no automatic provider/model purchase;
- no automatic paid fallback;
- no OpenClaw dependency;
- no native Windows Qwen support claim;
- no fuzzy tool auto-binding;
- no inferred filesystem access for unverified tool arguments.
