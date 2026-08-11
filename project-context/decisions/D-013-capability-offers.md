# D-013 — Semantic capability is separate from adapter offer

**Status:** accepted  
**Date:** 2026-08-11

## Decision

UV Studio represents a media ability at three separate levels:

```text
CapabilityDefinition
  -> AdapterDefinition
      -> CapabilityOffer
```

`CapabilityDefinition` is semantic and provider-neutral. `AdapterDefinition` identifies an implementation family. `CapabilityOffer` describes one adapter's current proposal to satisfy one semantic capability.

An offer explicitly records:

- availability: `available | configuration_required | unavailable`;
- locality: `local | remote | hybrid`;
- cost class: `free | potentially_paid | paid`;
- synchronous/asynchronous nature;
- safe feature metadata.

The registry may order offers deterministically for display/resolution support, but **does not automatically execute or purchase an offer**.

## Reason

Research of Qwen-MM-Plugins demonstrated that an open-source plugin can expose operations whose actual model execution is paid. Conversely, useful operations such as FFmpeg assembly or keyless speech synthesis may be free while having different locality characteristics.

A single `provider` field cannot express these distinctions safely.

Separating capability from offer prevents:

- provider names leaking into RecipeDefinition;
- “open source” being confused with “free execution”;
- local deterministic work being silently routed to paid AI;
- unavailable or partially compatible implementations being presented as ready;
- OpenClaw/Qwen-MM/native VideoClaw becoming mandatory product layers.

## Consequences

1. Recipes and ProductionPolicy remain unchanged when adapters/providers change.
2. Local/free offers can coexist with remote/paid offers for the same semantic capability.
3. `configuration_required` is different from `available`; a known provider integration is not considered ready until configured.
4. Capability APIs expose no secrets or raw credentials.
5. Offer preference order is metadata only:
   - available before configuration-required before unavailable;
   - free before potentially-paid before paid;
   - local before hybrid before remote;
   - stable ID tie-breaker.
6. A later selection policy may use this order, but paid execution requires explicit policy/user choice rather than implicit fallback.
7. Qwen-MM-Plugins and OpenClaw will be implemented, if useful, as peer adapters/offers behind the same contracts.
8. Native Windows startup cannot depend on an optional WSL-only adapter.

## Initial concrete examples

- `timeline.assemble` → local FFmpeg offer: local/free when `ffmpeg` is installed.
- `media.probe` → local FFprobe offer: local/free when `ffprobe` is installed.
- `speech.synthesize` → Edge TTS compatibility offer: remote/free when package is installed.
- `video.generate` → pinned VideoClaw model layer: hybrid/potentially-paid/configuration-required until a concrete model/provider is explicitly configured.
- `video.digital_human` → no native offer yet because the pinned VideoClaw product-promo contract does not match UV Studio's portrait + supplied speech semantics.
