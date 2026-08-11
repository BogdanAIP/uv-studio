# Optional Qwen-MM-Plugins integration

## Verified upstream

UV Studio's current Qwen-MM profile pack was re-verified on **2026-08-11** against:

```text
Repository: QwenLM/Qwen-MM-Plugins
Commit:     7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
License:    Apache-2.0
```

At verification time this commit was the repository `main` head. UV Studio profile templates pin the exact SHA rather than `main`.

Current upstream states:

- Python 3.12+ and `uv` are required;
- system FFmpeg is required for relevant local media operations;
- Windows is supported through **WSL2 only**; native Windows is explicitly documented as not yet supported;
- `core` contains local file/media operations and requires no API key;
- `api` contains Qwen/DashScope-backed multimodal APIs and self-hosted segmentation;
- `video-edit` combines local editing workflow/skill material with remote generation tools;
- remote generation tools require `DASHSCOPE_API_KEY`.

UV Studio does not infer price from the Apache-2.0 repository license.

## Why three packs

Qwen-MM is represented as three independent optional MCP profiles:

```text
core
api
video-edit
```

This avoids the false assumption that installing one open-source repository makes all operations local or free.

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

Verified current core tools include:

```text
read_image
read_video
media_info
visualize
crop
draw_bbox
save_view
```

UV Studio initially binds only:

```text
media_info -> media.probe
locality   = local
cost       = free
```

The other tools are intentionally left unbound in this slice. `read_image`, `read_video` and `visualize` are model-harness content/presentation primitives rather than semantic media-understanding operations by themselves; binding them to `media.understand` would overstate what they do. `crop`, `draw_bbox` and `save_view` will be reconsidered when UV Studio has provider-neutral image/editing capabilities that match them exactly.

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

Bound current tools:

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

`segmentation` is intentionally unbound because the current tool is a self-hosted SAM3-style service whose compute/locality/cost semantics differ from the DashScope tools and do not yet map cleanly to an existing UV Studio semantic output contract.

The profile stores only the environment-variable **name** `DASHSCOPE_API_KEY`; it never persists the resolved key value.

## Video-edit generation pack

Profile:

```text
profile_id: qwen-mm-video-edit
entrypoint: qwen-mm-plugins-video-edit
extra:      video-edit
credential reference: DASHSCOPE_API_KEY
```

Current upstream generation tools are explicitly described as remote DashScope operations requiring `DASHSCOPE_API_KEY`:

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

All four are:

```text
locality = remote
cost     = potentially_paid
```

### `wan_s2v` closes the semantic digital-human gap

The current upstream `wan_s2v` contract is specifically:

```text
portrait image + supplied audio -> lip-sync digital-human video
```

and its upstream documentation/tool schema explicitly marks both detection and generation paths as billed operations.

This matches UV Studio's `video.digital_human` recipe semantics much better than the pinned VideoClaw product-promo pipeline, which Stage 2 classified as only partial compatibility because it did not accept the user's supplied speech/audio.

This does **not** make `video.digital_human` automatically executable. Qwen's offer is only capability metadata until UV Studio implements explicit remote/paid execution consent and cost controls.

### Why `happyhorse` is unbound

The current `happyhorse` tool combines multiple modes including generation and video editing/reference transfer. Mapping that mixed provider contract to one current UV Studio capability would weaken semantic correctness. It therefore remains intentionally unbound until a provider-neutral transform/edit capability is defined.

## Trusted configuration API

UV Studio exposes a narrow static pack catalog/configuration API:

```text
GET  /api/uv/integrations/qwen-mm
GET  /api/uv/integrations/qwen-mm/{pack_id}
POST /api/uv/integrations/qwen-mm/{pack_id}/configure
```

`configure` can persist only one of the three pinned templates above. It does not accept user-supplied command/argv values.

The request body cannot replace the pinned `uvx` command, source SHA or entrypoint.

Generic arbitrary command profile creation remains intentionally absent.

## Windows behavior

Current upstream documents Windows support as WSL2-only.

Therefore the trusted Qwen configure action is fail-closed in a native Windows UV Studio process and returns a platform conflict instead of writing a profile that would imply native support.

This does not affect:

- native Windows UV Studio startup;
- Project Store;
- local FFmpeg/FFprobe capabilities;
- generic MCP infrastructure;
- VideoClaw compatibility paths.

A later WSL bridge may be added only after it is tested explicitly.

## Discovery vs execution

Configuring a Qwen pack creates only machine MCP profile/binding metadata.

Next flow:

```text
configure trusted pack
  -> MCP discovery
      -> exact tool names verified
          -> CapabilityOffer availability refreshed
```

Still forbidden at this stage:

```text
MCP call_tool
DashScope generation
paid provider invocation
automatic cost-bearing fallback
```

D-014 and D-015 remain authoritative: an available remote/potentially-paid Qwen offer cannot pass `local_free_first` and cannot be invoked until a separate execution-consent boundary exists.

## Drift behavior

The profile pack pins an exact Qwen commit and exact expected tool names.

If a future Qwen revision renames or removes a tool, UV Studio must update/re-verify the pack. It must not fuzzy-remap a newly discovered tool by name similarity.

With the current generic MCP layer:

- an unrecognized new tool stays unbound;
- an expected bound tool that is not reported becomes unavailable;
- canonical recipes/projects remain unchanged.

## What this integration deliberately does not do

- no Qwen runtime bundled with baseline UV Studio;
- no Qwen process at normal startup;
- no DashScope API call in CI/tests;
- no raw key persistence;
- no automatic provider/model purchase;
- no OpenClaw dependency;
- no native Windows support claim;
- no MCP tool invocation yet;
- no fuzzy tool auto-binding.
