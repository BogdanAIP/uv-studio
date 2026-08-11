# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/capability-registry`  
**Main baseline:** `dff8fc14a522bdb46498921ea5ebded204682747`  
**Branch status:** semantic capability metadata/offer registry implemented; final branch/PR CI must be green before merge.

## Product definition

UV Studio is a universal video production/editing studio. Task recipes, professional production policy and semantic capabilities are separate layers. Music, narration, story, continuity, lip-sync and review remain optional. Paid AI APIs are never hidden baseline dependencies.

## Current architecture

```text
Canonical Project
  -> RecipeDefinition
      -> ProductionPolicy
      -> RecipeExecutionPlan
          -> semantic capability IDs
              -> CapabilityRegistry
                  -> CapabilityDefinition
                  -> AdapterDefinition
                  -> CapabilityOffer
```

Adapters are peers. Local tools, direct MCP, native VideoClaw, optional Qwen-MM-Plugins, optional OpenClaw and future providers may coexist without becoming canonical project state or mandatory product layers.

## Merged milestones

- `af24ed11...` — reproducible VideoClaw baseline;
- `8d175c25...` — UV Studio launcher + HTTP smoke;
- `2276a854...` — canonical Project Store v1;
- `21016061...` — UV server + Projects API;
- `9570658d...` — UV-owned frontend + Projects UI;
- `3214cec8...` — portable project archives/backups + Qwen-MM-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14a522bdb46498921ea5ebded204682747` — truthful RecipeExecutionPlan and project readiness UI.

## Stage 3 implemented on current branch

### Capability contracts

Added `uv_studio/capabilities/` with schema v1.

`CapabilityDefinition` describes a provider-neutral operation.

Current semantic capabilities include:

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

Definitions record operation/input/output/async semantics only.

### Adapter / offer separation

`AdapterDefinition` describes implementation family.

`CapabilityOffer` records one adapter's proposal for one semantic capability with explicit:

```text
availability: available | configuration_required | unavailable
locality:     local | remote | hybrid
cost_class:   free | potentially_paid | paid
```

This prevents open-source plugin licensing from being confused with free model execution.

Decision record: `project-context/decisions/D-013-capability-offers.md`.

### Deterministic registry

`CapabilityRegistry` supports:

- strict registration and references;
- deterministic list/get;
- offers per capability;
- availability summary;
- duplicate/conflict errors;
- display preference order: available → configured-needed → unavailable; free → potentially-paid → paid; local → hybrid → remote.

This ordering is metadata only. It does not automatically execute or purchase an offer.

### Initial real offers

The first slice uses only capabilities verified in the pinned baseline.

#### `local_ffmpeg`

- `timeline.assemble` → local/free if `ffmpeg` is found;
- `media.probe` → local/free if `ffprobe` is found.

#### `native_videoclaw`

- `text.generate` → configuration-required / potentially-paid;
- `image.generate` → configuration-required / potentially-paid;
- `video.generate` → configuration-required / potentially-paid;
- `video.action_transfer` → configuration-required / potentially-paid;
- `speech.synthesize` → Edge TTS compatibility, remote/free when `edge-tts` package is installed.

No native `video.digital_human` offer is registered because Stage 2 proved the current upstream product-promo contract does not match UV Studio's portrait + supplied-speech semantics.

`media.understand`, `audio.mix` and `subtitle.render` remain definition-only until a concrete tested adapter is added.

### Read-only Capability API

Added:

```text
GET /api/uv/capabilities
GET /api/uv/capabilities/{capability_id}
GET /api/uv/capabilities/{capability_id}/offers
```

Responses contain safe metadata only; no secrets/config objects.

### Execution-plan integration

Project execution-plan runtime slots now include safe capability readiness summaries:

```text
total
available
configuration_required
unavailable
```

The endpoint still does not choose a model/provider or launch work.

### Tests / security

Added unit/API tests for:

- zero-credential registry startup;
- strict IDs/references/duplicates;
- free/local FFmpeg metadata;
- potentially-paid/configuration-required native generation metadata;
- absence of false digital-human offer;
- deterministic offer preference;
- no secret values in public metadata;
- capability API summaries;
- execution-plan capability readiness.

A security test initially caught the harmless feature label `speech.no_api_key` because public metadata forbids the literal secret-field name. The metadata was renamed to `speech.keyless`; the test was kept strict.

Documentation: `docs/architecture/CAPABILITIES.md`.

## Verification status

Functional head `4ecc3eb76a8213bad53165d7d15aa8531628a8ae`, CI run `31465538901`:

- Ubuntu bootstrap/unit: success;
- Ubuntu API integration + real HTTP smoke + frontend production build: success;
- Windows bootstrap/unit: success;
- Windows API integration + real HTTP smoke: success;
- Windows frontend install/build was still completing when this state update was written.

This state commit creates a newer CI head. Merge requires the final actual head to pass the full Linux/Windows matrix.

## What works now

- durable project/recovery/UI foundation;
- provider-neutral recipes and production policies;
- truthful execution planning;
- semantic Capability Registry;
- explicit free/paid-potential/locality/readiness metadata;
- local FFmpeg/FFprobe discovery;
- native VideoClaw compatibility offers without pretending they are already configured/free;
- zero paid API calls required to start/list the registry.

## Not implemented yet

- capability execution through UV-owned adapters;
- explicit selection policy implementation;
- direct MCP process/client;
- Qwen-MM runtime adapter;
- OpenClaw runtime adapter;
- live provider/model/cost selection;
- general-video executor;
- range edit/dubbing/music workflows.

## Current invariants

1. Capability semantics and adapter offers remain separate.
2. RecipeDefinition never names a provider/runtime.
3. Metadata may prefer free/local for display, but never silently executes a paid fallback.
4. Public capability metadata contains no credentials/secrets.
5. No paid provider is a hidden baseline dependency.
6. Native Windows cannot depend on WSL-only optional adapters.
7. No false offer is registered merely because a related upstream pipeline exists.
8. Vendor source remains an immutable compatibility boundary.

## Next slice

Implement UV Studio-owned **local deterministic capability execution + explicit selection policy** before connecting Qwen-MM/OpenClaw. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
