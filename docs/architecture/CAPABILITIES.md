# UV Studio Capability Registry

## Purpose

Recipes describe the task. Execution plans describe what capabilities are needed. The Capability Registry describes **which replaceable implementations could satisfy a semantic capability**.

```text
RecipeDefinition
  -> RecipeExecutionPlan
      -> semantic capability_id
          -> CapabilityRegistry
              -> adapter offers
```

The registry is deliberately read-only metadata in the first Stage 3 slice. Listing an offer never launches work or spends money.

## Three separate concepts

### CapabilityDefinition

Provider-neutral operation such as:

```text
text.generate
image.generate
video.generate
video.action_transfer
video.digital_human
speech.synthesize
media.understand
timeline.assemble
audio.mix
subtitle.render
media.probe
```

A capability defines:

- semantic ID;
- operation kind;
- input/output media kinds;
- async/sync nature.

It contains no API key, provider account or model ID.

### AdapterDefinition

A family of implementations:

```text
local_ffmpeg
native_videoclaw
```

Future peers may include:

```text
mcp_qwen_mm
openclaw_runtime
other direct MCP/local/provider adapters
```

No adapter is globally mandatory.

### CapabilityOffer

One adapter's proposal to satisfy one semantic capability.

An offer explicitly records:

- readiness: `available | configuration_required | unavailable`;
- locality: `local | remote | hybrid`;
- cost class: `free | potentially_paid | paid`;
- async/sync;
- optional provider-neutral feature tags.

This prevents “plugin is open source” from being confused with “the model call is free”.

## First real offers

### Local FFmpeg

The pinned baseline already contains real FFmpeg-based deterministic assembly. The registry therefore declares a local/free `timeline.assemble` offer when `ffmpeg` is found in PATH.

`media.probe` similarly uses `ffprobe` availability metadata.

The first slice does not yet expose an execution endpoint; it only reports whether the local tool exists.

### Native VideoClaw model layer

The pinned VideoClaw model registry/pipelines provide compatible routes for text/image/video generation and action transfer, but concrete model/provider credentials are not selected by UV Studio yet.

These offers are therefore:

```text
availability = configuration_required
cost_class = potentially_paid
locality = hybrid
```

They are never reported as free by default.

### Edge TTS compatibility

Pinned VideoClaw contains an `edge-tts` path that does not require an API key. It is represented as:

```text
cost_class = free
locality = remote
```

Availability reflects whether the Python package is present in the current environment.

Remote-but-no-charge is intentionally distinct from local.

### No false digital-human offer

Stage 2 proved that the current pinned VideoClaw `digital_human` product-promo contract does not match UV Studio's generic portrait + supplied speech semantics.

Therefore `video.digital_human` exists as a semantic capability, but there is **no native offer** for it in this registry slice.

## Offer ordering

`CapabilityRegistry.offers_for()` gives deterministic preference ordering:

1. available before configuration-required before unavailable;
2. free before potentially-paid before paid;
3. local before hybrid before remote;
4. stable offer ID as final tie-breaker.

This ordering is metadata convenience, not automatic execution selection. A later policy may use it, but paid work still requires explicit cost/provider rules.

## Security

Capability APIs expose no secrets.

Do not include in public capability/offer metadata:

- API keys;
- bearer tokens;
- secret values;
- raw provider configuration objects.

Availability checks may later inspect configuration internally, but responses should only expose safe state/reason metadata.

## API

```text
GET /api/uv/capabilities
GET /api/uv/capabilities/{capability_id}
GET /api/uv/capabilities/{capability_id}/offers
```

Capability detail includes an offer summary:

```text
total
available
configuration_required
unavailable
```

The project execution-plan endpoint also annotates runtime capability slots with this summary. It still does not select or invoke an offer.

## Qwen-MM / OpenClaw boundary

Qwen-MM-Plugins and OpenClaw are future optional adapters.

Qwen-MM can contribute:

- direct MCP media capabilities;
- optional paid Qwen/Wan/Omni services when configured;
- professional workflow ideas already represented separately in ProductionPolicy.

OpenClaw can contribute broader runtime/provider orchestration where useful.

Neither may become a required hop between UV Studio and every tool.

## Next implementation step

After the metadata registry is stable, add execution adapters incrementally:

1. local deterministic operations first;
2. native compatibility wrappers needed by existing recipes;
3. direct MCP process/client support;
4. optional Qwen-MM adapter;
5. optional OpenClaw adapter only where its runtime adds value.

Each adapter should pass the same semantic contracts so RecipeDefinition and Project Store do not change when providers change.
