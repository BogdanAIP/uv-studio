# D-016 — Qwen-MM is an optional pinned profile/binding pack

**Status:** accepted  
**Date:** 2026-08-11

## Decision

Integrate `QwenLM/Qwen-MM-Plugins` as a set of optional trusted MCP profile/binding templates pinned to a re-verified upstream commit, not as a mandatory UV Studio runtime or a special orchestration layer.

Current verified pin:

```text
QwenLM/Qwen-MM-Plugins
7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
Apache-2.0
```

The pack is split into `core`, `api` and `video-edit` because their locality/cost/runtime requirements differ materially.

## Cost classification

Repository license never determines operation cost.

- `core.media_info` is bound to `media.probe` as `local + free`.
- DashScope-backed API tools are `remote + potentially_paid`.
- Qwen/Wan generation tools are `remote + potentially_paid`.
- no generation binding is marked free.

Cloud profiles reference `DASHSCOPE_API_KEY` by environment-variable name only; the resolved value is not persisted.

## Semantic binding policy

Only tools whose current contract maps cleanly to provider-neutral UV Studio semantics are bound.

Examples:

- `media_info -> media.probe`;
- Qwen multimodal understanding tools -> `media.understand`;
- Qwen/Omni ASR tools -> new provider-neutral `speech.transcribe`;
- `qwen_image -> image.generate`;
- `qwen_tts -> speech.synthesize`;
- `wan_t2v -> video.generate`;
- `wan_s2v -> video.digital_human`.

Tools with mixed or mismatched semantics remain explicitly unbound instead of being forced into an approximate capability. Current examples include `happyhorse` and self-hosted `segmentation`.

## Digital-human consequence

Current Qwen `wan_s2v` accepts a portrait image plus supplied audio and generates lip-synced video. This matches UV Studio's `video.digital_human` semantics better than the pinned VideoClaw product-promo pipeline, which Stage 2 classified as partial.

The Qwen implementation remains only a remote potentially-paid offer until a separate remote/paid execution consent and cost boundary is implemented.

## Trusted configuration surface

UV Studio may persist only the predefined pinned Qwen templates through a dedicated integration API. The API does not accept arbitrary command/argv fields and cannot be used as a generic host process launcher.

Normal UV Studio startup does not configure, install or launch Qwen.

## Windows consequence

At the verified upstream revision, Qwen-MM documents Windows support as WSL2-only and native Windows as unsupported.

Therefore trusted Qwen profile configuration is fail-closed in a native Windows UV Studio process. Native Windows baseline functionality remains independent of Qwen/WSL.

## Execution consequence

This decision does not enable MCP tool invocation.

D-014 and D-015 remain authoritative:

- discovery/availability is not execution permission;
- `local_free_first` cannot select Qwen cloud offers;
- remote/potentially-paid execution requires a future explicit consent/cost boundary.

## Provenance and drift

Qwen profile launch templates pin the exact upstream SHA. Expected tool names are explicit.

Future upstream changes require a new verification/pin. New discovered tools remain unbound, and missing expected tools become unavailable; no fuzzy remapping is allowed.
